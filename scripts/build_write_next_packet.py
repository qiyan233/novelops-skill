#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from build_next_chapter_context import build_context_report
from novelops_common import (
    CHAPTER_HEADING_RE,
    chapter_sections,
    extract_bullets,
    extract_markdown_section,
    infer_next_chapter_from_project,
    iso_now,
    read_text,
    require_project_markers,
    write_json,
    posix_path,
)


def infer_next_chapter(project, explicit_chapter=None):
    return infer_next_chapter_from_project(project, explicit_chapter)


def find_outline_target(outline_text, chapter):
    patterns = [
        r'^\s*-\s*ch%s:\s*(.+)$' % chapter,
        r'^\s*-\s*chapter\s+%s:\s*(.+)$' % chapter,
        r'^\s*-\s*第\s*%s\s*章[:：]\s*(.+)$' % chapter,
    ]
    for line in outline_text.splitlines():
        stripped = line.strip()
        for pattern in patterns:
            match = re.match(pattern, stripped, flags=re.I)
            if match:
                return match.group(1).strip()
    return ''


def latest_pov(chapter_summaries):
    sections = chapter_sections(chapter_summaries, CHAPTER_HEADING_RE)
    if not sections:
        return ''
    latest = sections[-1][1]
    match = re.search(r'^-\s*POV:\s*(.+)$', latest, flags=re.M)
    return match.group(1).strip() if match else ''


def active_hooks(pending_hooks_text, limit=5):
    items = []
    for bullet in extract_bullets(pending_hooks_text):
        match = re.match(r'\[(OPEN|ADVANCED)\]\s*(.+?)\s*\((.+)\)$', bullet)
        if not match:
            continue
        items.append({
            'status': match.group(1).lower(),
            'hook': match.group(2).strip(),
            'meta': match.group(3).strip(),
        })
        if len(items) >= limit:
            break
    return items


def book_constraints(book_rules_text, limit=6):
    bullets = extract_bullets(book_rules_text)
    keep = []
    for bullet in bullets:
        if re.search(r'不允许|不得|不要|禁止|must not|do not|constraint|prohibition|lock', bullet, flags=re.I):
            keep.append(bullet)
        if len(keep) >= limit:
            break
    return keep


def immediate_pressure(current_state_text):
    return extract_bullets(extract_markdown_section(current_state_text, 'Immediate next pressure'))


def open_conflicts(current_state_text):
    return extract_bullets(extract_markdown_section(current_state_text, 'Open conflicts'))


def recent_state_targets(chapter_summaries, limit=4):
    sections = chapter_sections(chapter_summaries, CHAPTER_HEADING_RE)
    if not sections:
        return []
    latest = sections[-1][1]
    lines = []
    in_state = False
    for line in latest.splitlines():
        stripped = line.rstrip()
        if re.match(r'^-\s*State changes:', stripped):
            in_state = True
            continue
        if in_state and re.match(r'^-\s+\S', stripped):
            break
        if in_state:
            match = re.match(r'^\s*-\s+(.+)$', stripped)
            if match:
                lines.append(match.group(1).strip())
        if len(lines) >= limit:
            break
    return lines


def build_scene_beats(outline_target, pressure_items, hook_items, conflict_items):
    beats = []
    if outline_target:
        beats.append('开场先服务本章目标：%s' % outline_target)
    if pressure_items:
        beats.append('尽快落地当前压力：%s' % pressure_items[0])
    if hook_items:
        beats.append('明确推进至少一个 active hook：%s' % hook_items[0]['hook'])
    if len(hook_items) >= 2:
        beats.append('保留次级悬念，不要把这条线一次性说透：%s' % hook_items[1]['hook'])
    if conflict_items:
        beats.append('把核心冲突具象化成可见动作或对话，而不是解释：%s' % conflict_items[0])
    return beats[:5]


def chapter_path_hint(project, chapter):
    return str(Path(project) / 'chapters' / ('ch%02d.md' % chapter))


def plan_template(chapter, suggested_pov, primary_goal, beats):
    lines = [
        '# Chapter %s Plan' % chapter,
        '',
        '- POV: %s' % (suggested_pov or '待定'),
        '- Primary goal: %s' % primary_goal,
        '- Planned payoff or partial payoff: ',
        '- State change to land: ',
        '',
        '## Scene Beats',
    ]
    if beats:
        lines.extend(['- %s' % item for item in beats])
    else:
        lines.append('- 待补充')
    return '\n'.join(lines).strip() + '\n'


def single_chapter_contract(chapter):
    return [
        '只输出第 %s 章正文。' % chapter,
        '不要额外输出第 %s 章或更后面的章节。' % (chapter + 1),
        '不要在同一份草稿里写多个章节标题。',
        '当前章节结束后立即停止，不要续写下一章。',
    ]


def build_packet(project, chapter=None, recent_chapters=3, max_chars_per_file=1800):
    project = require_project_markers(project)
    chapter = infer_next_chapter(project, chapter)
    context_report = build_context_report(project, recent_chapters, max_chars_per_file, chapter)

    outline_text = read_text(Path(project) / 'outline.md')
    current_state_text = read_text(Path(project) / 'current_state.md')
    pending_hooks_text = read_text(Path(project) / 'pending_hooks.md')
    chapter_summaries = read_text(Path(project) / 'chapter_summaries.md')
    book_rules_text = read_text(Path(project) / 'book_rules.md')

    outline_target = find_outline_target(outline_text, chapter)
    pressure_items = immediate_pressure(current_state_text)
    hook_items = active_hooks(pending_hooks_text)
    conflict_items = open_conflicts(current_state_text)
    constraints = book_constraints(book_rules_text)
    state_targets = recent_state_targets(chapter_summaries)
    suggested_pov = latest_pov(chapter_summaries)
    beats = build_scene_beats(outline_target, pressure_items, hook_items, conflict_items)

    primary_goal = outline_target or (pressure_items[0] if pressure_items else '推进当前主线并制造可记录的 state change')
    planned_payoff = hook_items[0]['hook'] if hook_items else primary_goal

    return {
        'schema_version': 'novelops.write-next.v1',
        'tool': 'build_write_next_packet',
        'generated_at': iso_now(),
        'project': posix_path(project),
        'chapter': chapter,
        'chapter_file_hint': posix_path(chapter_path_hint(project, chapter)),
        'files_loaded': context_report['files_loaded'],
        'chapter_function': {
            'primary_goal': primary_goal,
            'pressure': pressure_items[:3],
            'planned_payoff_or_partial_payoff': planned_payoff,
        },
        'required_inputs': {
            'suggested_pov': suggested_pov,
            'active_hooks': hook_items,
            'open_conflicts': conflict_items[:4],
            'constraints': constraints,
            'state_targets': state_targets,
        },
        'single_chapter_contract': single_chapter_contract(chapter),
        'suggested_scene_beats': beats,
        'plan_template': plan_template(chapter, suggested_pov, primary_goal, beats),
        'context_packet': context_report,
        'next_actions': [
            '先用 chapter_function 和 suggested_scene_beats 写 1-3 条 chapter plan。',
            '正文必须只写当前目标章节，不要继续写后续章节。',
            '正文完成后按顺序跑 knowledge-check、audit、extract-state、state-update。',
        ],
    }


def print_markdown(packet):
    print('# Write-Next Packet')
    print()
    print('- chapter: %s' % packet['chapter'])
    print('- suggested_pov: %s' % (packet['required_inputs']['suggested_pov'] or 'unspecified'))
    print('- primary_goal: %s' % packet['chapter_function']['primary_goal'])
    print()
    print('## Active Hooks')
    if not packet['required_inputs']['active_hooks']:
        print('- none')
    else:
        for item in packet['required_inputs']['active_hooks']:
            print('- [%s] %s' % (item['status'], item['hook']))
    print()
    print('## Constraints')
    if not packet['required_inputs']['constraints']:
        print('- none')
    else:
        for item in packet['required_inputs']['constraints']:
            print('- %s' % item)
    print()
    print('## Suggested Scene Beats')
    if not packet['suggested_scene_beats']:
        print('- none')
    else:
        for item in packet['suggested_scene_beats']:
            print('- %s' % item)
    print()
    print('## Single Chapter Contract')
    for item in packet['single_chapter_contract']:
        print('- %s' % item)
    print()
    print(packet['context_packet']['context'])


def main():
    parser = argparse.ArgumentParser(description='Build a structured write-next packet for the next chapter.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--chapter', type=int)
    parser.add_argument('--recent-chapters', type=int, default=3)
    parser.add_argument('--max-chars-per-file', type=int, default=1800)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    args = parser.parse_args()

    if args.recent_chapters < 0:
        raise SystemExit('--recent-chapters must be >= 0')
    if args.max_chars_per_file < 0:
        raise SystemExit('--max-chars-per-file must be >= 0')

    packet = build_packet(args.project, args.chapter, args.recent_chapters, args.max_chars_per_file)
    if args.write_report:
        out = Path(args.project) / 'reviews' / ('ch%02d.write-next.json' % packet['chapter'])
        packet['report_path'] = posix_path(out)
        write_json(out, packet)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print_markdown(packet)


if __name__ == '__main__':
    main()
