#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from audit_chapter import build_report as build_audit_report
from build_revision_plan import build_plan
from hook_report import build_report as build_hook_report
from novelops_common import iso_now, write_json
from novelops_common import posix_path
from knowledge_check import build_report as build_knowledge_report
from suggest_spot_fixes import build_suggestions

SEVERITY_LEVELS = ('critical', 'major', 'minor', 'note')
FAIL_ON_LEVELS = ('none', 'critical', 'major', 'minor')
EXIT_FAILED = 2


def overall_status(knowledge_report, audit_report):
    knowledge_counts = knowledge_report['summary']['counts']
    audit_counts = audit_report['summary']['counts']
    if knowledge_counts['critical'] or knowledge_counts['major']:
        return 'block'
    if audit_counts['critical']:
        return 'block'
    if audit_counts['major']:
        return 'revise'
    return 'pass'


def severity_counts(knowledge_report, audit_report):
    """knowledge-check 与 audit 的严重度计数合并（不改动两份原始报告）。"""
    counts = dict(audit_report['summary']['counts'])
    if knowledge_report:
        for level, value in knowledge_report['summary']['counts'].items():
            counts[level] = counts.get(level, 0) + value
    return counts


def counts_by_rule(knowledge_report, audit_report):
    """按规则统计命中数：给 CI / 趋势看「哪条规则最吵」，不用读整份报告。"""
    counts = {}
    for finding in audit_report.get('findings', []):
        rule_id = finding.get('rule_id')
        counts[rule_id] = counts.get(rule_id, 0) + 1
    if knowledge_report:
        for violation in knowledge_report.get('violations', []):
            key = 'KNOW-%s' % (violation.get('type') or 'unknown')
            counts[key] = counts.get(key, 0) + 1
    return counts


def worst_severity(counts):
    for level in SEVERITY_LEVELS:
        if counts.get(level):
            return level
    return None


def fail_on_exit_code(counts, fail_on):
    """CI 用的门禁：severity 达到 --fail-on 门槛就退出码 2。

    默认 none，行为与 1.1.0 一致（永远 0），不影响既有脚本。
    """
    if fail_on not in FAIL_ON_LEVELS or fail_on == 'none':
        return 0
    worst = worst_severity(counts)
    if worst is None:
        return 0
    return EXIT_FAILED if SEVERITY_LEVELS.index(worst) <= SEVERITY_LEVELS.index(fail_on) else 0


def summarize(data):
    """去掉三份完整报告的紧凑版：给 CLI 直接看、给 CI 存档。"""
    return {
        'schema_version': 'novelops.revision-cycle-summary.v1',
        'tool': data['tool'],
        'generated_at': data['generated_at'],
        'project': data['project'],
        'chapter': data['chapter'],
        'chapter_file': data['chapter_file'],
        'status': data['status'],
        'summary': dict(data['summary'],
                        severity_counts=data['severity_counts'],
                        counts_by_rule=data['counts_by_rule']),
        'coverage': data['coverage'],
        'recommended_sequence': data['recommended_sequence'],
        'reports': {'full_report': data.get('report_path')},
    }


def build_cycle(project, chapter_file, run_knowledge_check=True):
    knowledge_report = build_knowledge_report(project, chapter_file) if run_knowledge_check else None
    audit_report = build_audit_report(project, chapter_file)
    revision_plan = build_plan(project, chapter_file, None)
    spot_fixes = build_suggestions(project, chapter_file, None)
    hook_report = build_hook_report(project, stale_after=5)

    status = overall_status(
        knowledge_report or {'summary': {'counts': {'critical': 0, 'major': 0}}},
        audit_report,
    )
    blocking_items = 0
    if knowledge_report:
        blocking_items += knowledge_report['summary']['counts']['critical'] + knowledge_report['summary']['counts']['major']
    blocking_items += audit_report['summary']['counts']['critical'] + audit_report['summary']['counts']['major']

    combined_counts = severity_counts(knowledge_report, audit_report)
    return {
        'schema_version': 'novelops.revision-cycle.v1',
        'tool': 'run_revision_cycle',
        'generated_at': iso_now(),
        'project': posix_path(project),
        'chapter': posix_path(chapter_file),
        'chapter_file': posix_path(chapter_file),
        'status': status,
        'summary': {
            'knowledge_check_run': run_knowledge_check,
            'blocking_item_count': blocking_items,
            'audit_overall': audit_report['overall'],
            'spot_fix_count': spot_fixes['summary']['suggestion_count'],
            'human_review_needed': revision_plan['summary']['human_review_needed'],
            'stale_hook_count': hook_report['summary']['stale_hook_count'],
            'worst_severity': worst_severity(combined_counts),
        },
        'severity_counts': combined_counts,
        'counts_by_rule': counts_by_rule(knowledge_report, audit_report),
        # 能力边界：overall=pass 不等于这些维度也过了，它们本来就没有脚本检查。
        'coverage': audit_report.get('coverage'),
        'recommended_sequence': [
            '先修 knowledge-boundary 和 audit 里的 critical / major 问题。',
            '再按 revision_plan 处理 scene-level 或 local-level 修订。',
            '最后应用 spot-fixes，并在接受后更新 truth files。',
        ],
        'hook_pressure': hook_report,
        'knowledge_check': knowledge_report,
        'audit': audit_report,
        'revision_plan': revision_plan,
        'spot_fixes': spot_fixes,
    }


def print_markdown(data):
    print('# Revision Cycle')
    print()
    print('- status: %s' % data['status'])
    print('- audit_overall: %s' % data['summary']['audit_overall'])
    print('- blocking_item_count: %s' % data['summary']['blocking_item_count'])
    print('- human_review_needed: %s' % data['summary']['human_review_needed'])
    print('- stale_hook_count: %s' % data['summary']['stale_hook_count'])
    print('- worst_severity: %s' % (data['summary'].get('worst_severity') or 'none'))
    print()

    if data['knowledge_check']:
        print('## Knowledge Check')
        print('- ok: %s' % ('yes' if data['knowledge_check']['ok'] else 'no'))
        print('- violations: %s' % data['knowledge_check']['summary']['violation_count'])
        print()

    print('## Minimal Fix Plan')
    for item in data['revision_plan']['minimal_fix_plan']:
        print('- %s' % item)
    print()

    print('## Spot Fixes')
    if not data['spot_fixes']['suggestions']:
        print('- none')
    else:
        for item in data['spot_fixes']['suggestions']:
            print('- [%s/%s] %s' % (item['suggestion_id'], item['rule_id'], item['suggested_action']))
    print()

    print('## Hook Pressure')
    if not data['hook_pressure']['stale_hooks']:
        print('- no stale hooks')
    else:
        for item in data['hook_pressure']['stale_hooks']:
            print('- [%s] %s' % (item['status'] if 'status' in item else 'stale', item['hook']))
    print()

    print('## Coverage（自动检查之外）')
    coverage = data.get('coverage') or {}
    for item in coverage.get('human_only_dimensions', []):
        print('- [human] %s：%s' % (item.get('label', item.get('dimension')), item.get('why', '')))
    if not coverage.get('human_only_dimensions'):
        print('- none')


def main():
    parser = argparse.ArgumentParser(description='Run a full revision cycle for a chapter draft.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--chapter-file', required=True)
    parser.add_argument('--skip-knowledge-check', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    parser.add_argument('--summary', action='store_true',
                        help='Emit the compact JSON summary instead of inlining all five reports (only with --json).')
    parser.add_argument('--fail-on', choices=FAIL_ON_LEVELS, default='none',
                        help='Exit with code 2 when the worst finding reaches this severity (CI gate).')
    args = parser.parse_args()

    data = build_cycle(args.project, args.chapter_file, run_knowledge_check=not args.skip_knowledge_check)

    if args.write_report:
        chapter_stem = Path(args.chapter_file).stem
        out = Path(args.project) / 'reviews' / ('%s.revision-cycle.json' % chapter_stem)
        data['report_path'] = posix_path(out)
        write_json(out, data)

    if args.json:
        payload = summarize(data) if args.summary else data
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_markdown(data)

    exit_code = fail_on_exit_code(data['severity_counts'], args.fail_on)
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
