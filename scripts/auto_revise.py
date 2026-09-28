#!/usr/bin/env python3
"""LLM 段落级最小化自动修订。

流程：跑修订闭环（run_revision_cycle）→ 取 local-dimension 且有 evidence 的 findings →
按 evidence 定位包含段落（同段多 finding 合并为一个 target）→ 每个 target 交 LLM 最小化重写。

三种模式：
- --dry-run：不联网不写盘，只输出每个 target 的请求 payload；
- 缺省（diff）：执行重写（mock 或 live），输出整章 unified diff，但不写盘；
- --apply：先自动 snapshot + 章节原文备份，再把重写结果写回。
"""
import argparse
import difflib
import json
import re
from pathlib import Path

from audit_chapter import SEVERITY_ORDER
from build_write_next_packet import book_constraints
from draft_chapter import find_chapter_headings
from llm_client import (
    build_chat_payload,
    chat,
    load_mock_responses,
    resolve_api_key,
    resolve_llm_config,
    resolve_mock_source,
)
from novelops_common import (
    atomic_write_text,
    clean_model_output,
    detect_newline,
    iso_now,
    parse_chapter_number,
    read_text,
    state_root,
    write_json,
)
from novelops_config import load_project_config
from run_revision_cycle import build_cycle
from snapshot_story_state import snapshot
from suggest_spot_fixes import LOCAL_DIMENSIONS, TEMPLATES

PARA_SPLIT_RE = re.compile(r'\n\s*\n')
DIFF_LINE_CAP = 400
LENGTH_RATIO_MIN = 0.4
LENGTH_RATIO_MAX = 2.5
# 单条 finding 最多牵引几个段落：evidence 是「突然」这类通用词时会命中很多段，
# 不设限的话一个 finding 就能吃满 --max-paragraphs 预算，让「最小化修订」名不副实。
MAX_PARAGRAPHS_PER_FINDING = 2

REWRITE_SYSTEM_PROMPT = (
    '你是长篇小说的最小化修订执行器。规则：\n'
    '- 只修订问题清单里列出的问题，能不动的句子保持原样。\n'
    '- 保持人称、时态、POV 与信息边界，不得让任何角色知道原文中不知道的事。\n'
    '- 不新增人物、事件、设定或伏笔，不删除关键信息。\n'
    '- 重写后段落长度与原段接近（±30%）。\n'
    '- 只输出重写后的段落纯文本，不要标题、解释或代码块。'
)


def split_paragraphs(text):
    """按空行切段并记录 (start, end) 偏移，供精确重建全文。"""
    paragraphs = []
    pos = 0
    for match in PARA_SPLIT_RE.finditer(text):
        segment = text[pos:match.start()]
        if segment.strip():
            paragraphs.append({'index': len(paragraphs), 'start': pos, 'end': match.start(), 'text': segment})
        pos = match.end()
    tail = text[pos:]
    if tail.strip():
        paragraphs.append({'index': len(paragraphs), 'start': pos, 'end': len(text), 'text': tail})
    return paragraphs


def is_heading_paragraph(text):
    return text.lstrip().startswith('#')


def collect_targets(chapter_text, findings, max_paragraphs):
    """把 local-dimension findings 映射到包含段落，合并同段，返回 (targets, skipped_findings)。"""
    paragraphs = split_paragraphs(chapter_text)
    skipped_findings = []
    para_findings = {}
    for finding in findings:
        if finding['dimension'] not in LOCAL_DIMENSIONS:
            continue
        evidence = [token for token in (finding.get('evidence') or []) if token]
        if not evidence:
            skipped_findings.append({
                'rule_id': finding.get('rule_id'),
                'dimension': finding['dimension'],
                'reason': 'no-evidence-anchor',
            })
            continue
        hit_indexes = set()
        for token in evidence:
            for para in paragraphs:
                if is_heading_paragraph(para['text']):
                    continue
                if token in para['text']:
                    hit_indexes.add(para['index'])
        if not hit_indexes:
            skipped_findings.append({
                'rule_id': finding.get('rule_id'),
                'dimension': finding['dimension'],
                'reason': 'evidence-not-found',
            })
            continue
        if len(hit_indexes) > MAX_PARAGRAPHS_PER_FINDING:
            kept = sorted(hit_indexes)[:MAX_PARAGRAPHS_PER_FINDING]
            skipped_findings.append({
                'rule_id': finding.get('rule_id'),
                'dimension': finding['dimension'],
                'reason': 'evidence-too-broad',
            })
            hit_indexes = set(kept)
        for index in hit_indexes:
            para_findings.setdefault(index, []).append(finding)

    def target_sort_key(index):
        best = min(SEVERITY_ORDER[f['severity']] for f in para_findings[index])
        return (best, index)

    ordered = sorted(para_findings, key=target_sort_key)
    targets = []
    for index in ordered[:max_paragraphs]:
        para = paragraphs[index]
        targets.append({
            'paragraph': para,
            'findings': para_findings[index],
        })
    for index in ordered[max_paragraphs:]:
        for finding in para_findings[index]:
            skipped_findings.append({
                'rule_id': finding.get('rule_id'),
                'dimension': finding['dimension'],
                'reason': 'over-paragraph-budget',
            })
    targets.sort(key=lambda t: t['paragraph']['index'])
    return targets, skipped_findings, paragraphs


def build_rewrite_messages(target, paragraphs, constraints):
    para = target['paragraph']
    prev_text = paragraphs[para['index'] - 1]['text'].strip() if para['index'] > 0 else '（本段已是开头）'
    next_text = (paragraphs[para['index'] + 1]['text'].strip()
                 if para['index'] + 1 < len(paragraphs) else '（本段已是结尾）')
    issue_lines = []
    for finding in target['findings']:
        template = TEMPLATES.get(finding['dimension'], 'Apply the smallest local patch that resolves the issue.')
        issue_lines.append('- [%s/%s] %s；建议动作：%s'
                           % (finding.get('rule_id'), finding['dimension'], finding['message'], template))
    constraint_lines = '\n'.join('- %s' % line for line in constraints) if constraints else '- （无显式禁令）'
    user = (
        '【书籍约束】\n%s\n\n'
        '【上文段落（仅供衔接，勿输出）】\n%s\n\n'
        '【待修订段落】\n%s\n\n'
        '【下文段落（仅供衔接，勿输出）】\n%s\n\n'
        '【问题清单】\n%s\n\n'
        '现在输出重写后的段落。'
        % (constraint_lines, prev_text, para['text'].strip(), next_text, '\n'.join(issue_lines))
    )
    return [
        {'role': 'system', 'content': REWRITE_SYSTEM_PROMPT},
        {'role': 'user', 'content': user},
    ]


def validate_rewrite(original, revised):
    """校验并净化重写结果；返回 (status, reason, cleaned)。

    净化必须在校验之前：模型返回 ``` 包裹或「好的，以下是修订后的段落：」开场白时，
    不剥掉就会把围栏和客套话当成合法正文写回小说。status: rewritten/unchanged/skipped。
    """
    cleaned = clean_model_output(revised)
    if not cleaned:
        return 'skipped', 'empty-rewrite', cleaned
    if find_chapter_headings(cleaned):
        return 'skipped', 'rewrite-contains-heading', cleaned
    ratio = len(cleaned) / float(len(original.strip()) or 1)
    if ratio < LENGTH_RATIO_MIN or ratio > LENGTH_RATIO_MAX:
        return 'skipped', 'rewrite-out-of-bounds', cleaned
    if cleaned == original.strip():
        return 'unchanged', None, cleaned
    return 'rewritten', None, cleaned


def rebuild_text(chapter_text, replacements):
    """replacements: [(start, end, new_text)]，按位置从后往前替换。"""
    result = chapter_text
    for start, end, new_text in sorted(replacements, key=lambda item: item[0], reverse=True):
        result = result[:start] + new_text + result[end:]
    return result


def build_auto_revise(project, chapter_file, dry_run=False, apply_changes=False, mock_path=None,
                      llm_overrides=None, max_paragraphs=5, skip_knowledge_check=False, force=False):
    chapter_file = Path(chapter_file)
    cycle = build_cycle(project, chapter_file, run_knowledge_check=not skip_knowledge_check)
    chapter_text = read_text(chapter_file)
    findings = cycle['audit']['findings']
    targets, skipped_findings, paragraphs = collect_targets(chapter_text, findings, max_paragraphs)

    project_config = load_project_config(project)
    llm_config = resolve_llm_config(project_config, llm_overrides)
    api_key, api_key_source = resolve_api_key(llm_config)
    constraints = book_constraints(read_text(Path(project) / 'book_rules.md'))

    mode = 'dry-run' if dry_run else ('apply' if apply_changes else 'diff')
    report = {
        'schema_version': 'novelops.auto-revise.v1',
        'tool': 'auto_revise',
        'generated_at': iso_now(),
        'project': cycle['project'],
        'chapter_file': str(chapter_file),
        'chapter': parse_chapter_number(chapter_file.stem),
        'mode': mode,
        'llm': {
            'provider': llm_config['provider'],
            'base_url': llm_config['base_url'],
            'model': llm_config['model'],
            'temperature': llm_config['temperature'],
            'top_p': llm_config['top_p'],
            'max_tokens': llm_config['max_tokens'],
            'api_key': None,
            'api_key_present': api_key is not None,
            'api_key_source': api_key_source,
        },
        'based_on': {
            'revision_cycle_status': cycle['status'],
            'audit_overall': cycle['audit']['overall'],
        },
        'summary': {
            'local_finding_count': sum(1 for f in findings if f['dimension'] in LOCAL_DIMENSIONS),
            'paragraphs_targeted': len(targets),
            'paragraphs_rewritten': 0,
            'paragraphs_skipped': 0,
            'applied': False,
        },
        'targets': [],
        'skipped_findings': skipped_findings,
        'diff': [],
        'diff_truncated': False,
        'snapshot': None,
    }

    # audit 判定 block 说明存在 critical 问题（如信息边界泄露）。局部段落重写修不了
    # 结构性问题，还可能把它盖住；在调用 LLM 之前就拒绝，附带 --force 逃生通道。
    if apply_changes and not force and report['based_on']['audit_overall'] == 'block':
        raise SystemExit(
            'Audit overall is "block"（存在 critical 问题）；段落级重写修不了结构性问题。'
            '请先处理 critical 项，确认仍要继续时加 --force。')

    def target_entry(target):
        return {
            'paragraph_index': target['paragraph']['index'],
            'findings': [
                {
                    'rule_id': f.get('rule_id'),
                    'dimension': f['dimension'],
                    'severity': f['severity'],
                    'evidence': f.get('evidence') or [],
                }
                for f in target['findings']
            ],
            'original': target['paragraph']['text'].strip(),
            'revised': None,
            'status': 'skipped',
            'skip_reason': None,
        }

    if dry_run:
        for target in targets:
            entry = target_entry(target)
            entry['payload'] = build_chat_payload(build_rewrite_messages(target, paragraphs, constraints), llm_config)
            report['targets'].append(entry)
        report['summary']['paragraphs_skipped'] = len(targets)
        return report

    mock_source = resolve_mock_source(mock_path)
    mock_responses = load_mock_responses(mock_source) if mock_source else None
    if mock_responses is not None and len(mock_responses) not in (1,) and len(mock_responses) < len(targets):
        raise SystemExit('mock responses exhausted: need %d, got %d' % (len(targets), len(mock_responses)))

    replacements = []
    transport = None
    for position, target in enumerate(targets):
        entry = target_entry(target)
        if mock_responses is not None:
            mock_content = mock_responses[0] if len(mock_responses) == 1 else mock_responses[position]
        else:
            mock_content = None
        result = chat(build_rewrite_messages(target, paragraphs, constraints), llm_config, mock_content=mock_content)
        transport = result['transport']
        status, reason, cleaned = validate_rewrite(target['paragraph']['text'], result['content'])
        entry['status'] = status
        entry['skip_reason'] = reason
        if status == 'rewritten':
            entry['revised'] = cleaned
            paragraph = target['paragraph']
            original_segment = chapter_text[paragraph['start']:paragraph['end']]
            # 保留原段落的首尾空白：段落切片本身可能带尾随换行（文件末尾尤其如此），
            # 直接用 strip 过的正文替换会把换行吃掉，重建后文件末尾就没有换行了。
            leading = original_segment[:len(original_segment) - len(original_segment.lstrip())]
            trailing = original_segment[len(original_segment.rstrip()):]
            body = cleaned.replace('\r\n', '\n').replace('\r', '\n')
            replacements.append((paragraph['start'], paragraph['end'], leading + body + trailing))
            report['summary']['paragraphs_rewritten'] += 1
        elif status == 'skipped':
            report['summary']['paragraphs_skipped'] += 1
        report['targets'].append(entry)
    report['llm']['transport'] = transport

    revised_text = rebuild_text(chapter_text, replacements)
    if revised_text != chapter_text:
        diff_lines = list(difflib.unified_diff(
            chapter_text.splitlines(),
            revised_text.splitlines(),
            fromfile='before/%s' % chapter_file.name,
            tofile='after/%s' % chapter_file.name,
            lineterm='',
        ))
        if len(diff_lines) > DIFF_LINE_CAP:
            report['diff'] = diff_lines[:DIFF_LINE_CAP]
            report['diff_truncated'] = True
        else:
            report['diff'] = diff_lines

    if apply_changes and revised_text != chapter_text:
        stem = chapter_file.stem
        manifest = snapshot(project, label='auto-revise-%s' % stem,
                            chapter=parse_chapter_number(stem), notes='pre auto-revise backup')
        backup_dir = state_root(project) / 'backups' / manifest['snapshot_id']
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / chapter_file.name
        # 原文件可能是 CRLF；read_text 已把它归一成 \n，写回时按原风格还原，
        # 否则只改一段却会把整文件行尾翻转，git diff 全红。
        newline = detect_newline(chapter_file, '\n')
        atomic_write_text(backup_path, chapter_text.replace('\n', newline))
        atomic_write_text(chapter_file, revised_text.replace('\n', newline))
        report['summary']['applied'] = True
        report['snapshot'] = {
            'snapshot_id': manifest['snapshot_id'],
            'snapshot_dir': manifest['snapshot_dir'],
            'chapter_backup': str(backup_path),
        }
    return report


def print_markdown(report):
    print('# Auto Revise')
    print()
    print('- mode: %s' % report['mode'])
    print('- chapter_file: %s' % report['chapter_file'])
    print('- targets: %s' % report['summary']['paragraphs_targeted'])
    print('- rewritten: %s' % report['summary']['paragraphs_rewritten'])
    print('- applied: %s' % ('yes' if report['summary']['applied'] else 'no'))
    if report['snapshot']:
        print('- snapshot: %s' % report['snapshot']['snapshot_id'])
        print('- chapter_backup: %s' % report['snapshot']['chapter_backup'])
    print()
    print('## Diff')
    if not report['diff']:
        print('- none')
    else:
        for line in report['diff']:
            print(line)


def main():
    parser = argparse.ArgumentParser(description='LLM paragraph-level minimal auto revision for a chapter.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--chapter-file', required=True)
    parser.add_argument('--dry-run', action='store_true', help='Only print per-target chat payloads.')
    parser.add_argument('--apply', action='store_true', help='Write revisions back (snapshot + backup first).')
    parser.add_argument('--force', action='store_true',
                        help='Apply even when the audit overall is "block" (critical findings present).')
    parser.add_argument('--mock-response', help='File whose content is used as the LLM response (offline).')
    parser.add_argument('--max-paragraphs', type=int, default=5)
    parser.add_argument('--skip-knowledge-check', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    parser.add_argument('--model')
    parser.add_argument('--base-url')
    parser.add_argument('--temperature', type=float)
    parser.add_argument('--top-p', dest='top_p', type=float)
    parser.add_argument('--max-tokens', dest='max_tokens', type=int)
    parser.add_argument('--timeout', dest='timeout_seconds', type=int)
    args = parser.parse_args()

    llm_overrides = {
        'model': args.model,
        'base_url': args.base_url,
        'temperature': args.temperature,
        'top_p': args.top_p,
        'max_tokens': args.max_tokens,
        'timeout_seconds': args.timeout_seconds,
    }

    report = build_auto_revise(
        args.project,
        args.chapter_file,
        dry_run=args.dry_run,
        apply_changes=args.apply,
        mock_path=args.mock_response,
        llm_overrides=llm_overrides,
        max_paragraphs=args.max_paragraphs,
        skip_knowledge_check=args.skip_knowledge_check,
        force=args.force,
    )

    if args.write_report:
        out = Path(args.project) / 'reviews' / ('%s.auto-revise.json' % Path(args.chapter_file).stem)
        report['report_path'] = str(out)
        write_json(out, report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)


if __name__ == '__main__':
    main()
