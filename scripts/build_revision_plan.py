#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from audit_chapter import build_report
from novelops_common import iso_now, write_json
from novelops_common import posix_path

SCOPE_BY_DIMENSION = {
    'information-boundary': 'scene',
    'protagonist-lock': 'scene',
    'outline-drift': 'chapter',
    'state-cohesion': 'chapter',
    'timeline-continuity': 'scene',
    'hook-overload': 'planning',
    'hook-advancement': 'planning',
    'state-update-pressure': 'state-files',
    'repetition-fatigue': 'local',
    'report-speak': 'local',
    'crowd-cliche': 'local',
    'paragraph-monotony': 'local',
    'dialogue-balance': 'scene',
    'telling-vs-dramatizing': 'local',
}

STRATEGY_BY_DIMENSION = {
    'information-boundary': 'Patch the leaking line first; verify POV knowledge boundaries before touching prose style.',
    'protagonist-lock': 'Restore the protagonist lock before any style cleanup.',
    'outline-drift': 'Re-state the chapter function and decide whether the scene should be reframed or moved.',
    'state-cohesion': 'Re-anchor the chapter in current pressures, facts, and active conflicts.',
    'timeline-continuity': 'Clarify scene transitions and trim unearned time jumps.',
    'hook-overload': 'Choose one or two hooks to advance explicitly and defer the rest on purpose.',
    'hook-advancement': 'Decide whether the chapter is intentionally transitional; if not, advance at least one active hook.',
    'state-update-pressure': 'Prepare truth-file updates immediately after acceptance to avoid drift.',
    'repetition-fatigue': 'Trim repeated transition words and keep only the strongest beats.',
    'report-speak': 'Replace abstract explanation with concrete action, sensory detail, or dialogue.',
    'crowd-cliche': 'Swap generic crowd reactions for 1-2 specific character beats.',
    'paragraph-monotony': 'Vary paragraph rhythm by splitting heavy blocks or combining thin ones.',
    'dialogue-balance': 'Verify whether silence is intentional; add dialogue only if the scene needs interactive pressure.',
    'telling-vs-dramatizing': 'Convert labeled emotions into observable action, bodily response, or subtext.',
}


def load_audit(project, chapter_file, audit_report):
    if audit_report:
        return json.loads(Path(audit_report).read_text(encoding='utf-8'))
    if not project or not chapter_file:
        raise SystemExit('Either provide --audit-report or both --project and --chapter-file.')
    return build_report(project, chapter_file)


def overall_strategy(report):
    counts = report['summary']['counts']
    if counts['critical']:
        return {
            'mode': 'block-and-patch',
            'reason': 'Critical continuity or knowledge-boundary issues must be repaired before stylistic work.',
        }
    if counts['major'] >= 2:
        return {
            'mode': 'targeted-scene-rewrite',
            'reason': 'Multiple major findings suggest the chapter needs scene-level restructuring, not only line edits.',
        }
    if counts['major'] == 1:
        return {
            'mode': 'targeted-rewrite',
            'reason': 'One major issue exists; repair the structural problem first, then do local cleanup.',
        }
    if counts['minor'] >= 3:
        return {
            'mode': 'spot-fix-pass',
            'reason': 'No major blockers; prioritize a focused local revision pass.',
        }
    return {
        'mode': 'light-pass-or-accept',
        'reason': 'Only low-severity or note-level issues remain.',
    }


def build_actions(report):
    actions = []
    for idx, finding in enumerate(report['findings'], 1):
        dimension = finding['dimension']
        scope = SCOPE_BY_DIMENSION.get(dimension, 'local')
        needs_human = finding['severity'] in ('critical', 'major') or scope in ('scene', 'chapter', 'planning')
        actions.append({
            'action_id': 'REV-%03d' % idx,
            'priority': finding['severity'],
            'rule_id': finding.get('rule_id'),
            'dimension': dimension,
            'target_scope': scope,
            'needs_human_review': needs_human,
            'goal': finding['message'],
            'recommended_strategy': STRATEGY_BY_DIMENSION.get(dimension, 'Apply the smallest safe patch that resolves the finding.'),
            'repair_targets': finding.get('repair_targets', []),
            'evidence': finding.get('evidence', []),
        })
    return actions


def build_plan(project, chapter_file, audit_report):
    report = load_audit(project, chapter_file, audit_report)
    actions = build_actions(report)
    strategy = overall_strategy(report)
    return {
        'schema_version': 'novelops.revision-plan.v1',
        'tool': 'build_revision_plan',
        'generated_at': iso_now(),
        'project': report.get('project'),
        'chapter': report.get('chapter'),
        'chapter_file': report.get('chapter_file') or report.get('chapter'),
        'based_on': {
            'schema_version': report.get('schema_version'),
            'overall': report.get('overall'),
        },
        'overall_strategy': strategy,
        'summary': {
            'action_count': len(actions),
            'human_review_needed': sum(1 for action in actions if action['needs_human_review']),
            'counts': report['summary']['counts'],
        },
        'source_files': report.get('source_files', []),
        'minimal_fix_plan': report.get('minimal_fix_plan', []),
        'actions': actions,
    }


def print_markdown(plan):
    print('# Revision Plan')
    print()
    print('## Overall strategy')
    print('- mode: %s' % plan['overall_strategy']['mode'])
    print('- reason: %s' % plan['overall_strategy']['reason'])
    print()
    print('## Minimal fix plan')
    for item in plan['minimal_fix_plan']:
        print('- %s' % item)
    print()
    print('## Actions')
    if not plan['actions']:
        print('- none')
        return
    for action in plan['actions']:
        print('- [%s/%s] %s' % (action['action_id'], action['rule_id'], action['goal']))
        print('  - scope: %s' % action['target_scope'])
        print('  - strategy: %s' % action['recommended_strategy'])
        print('  - needs_human_review: %s' % ('yes' if action['needs_human_review'] else 'no'))
        if action['repair_targets']:
            print('  - repair_targets: %s' % '; '.join(action['repair_targets']))


def main():
    parser = argparse.ArgumentParser(description='Build a structured revision plan from an audit report.')
    parser.add_argument('--project')
    parser.add_argument('--chapter-file')
    parser.add_argument('--audit-report', help='Existing audit JSON report. If omitted, audit is run on the fly.')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    args = parser.parse_args()

    plan = build_plan(args.project, args.chapter_file, args.audit_report)

    if args.write_report:
        project_dir = plan.get('project')
        chapter_ref = plan.get('chapter_file') or plan.get('chapter')
        if not project_dir or not chapter_ref:
            raise SystemExit(
                '--write-report requires "project" and "chapter"/"chapter_file" in the audit report; '
                'the provided --audit-report JSON is missing them. '
                'Pass --project/--chapter-file instead, or omit --write-report.')
        chapter_stem = Path(chapter_ref).stem
        out = Path(project_dir) / 'reviews' / ('%s.revision-plan.json' % chapter_stem)
        plan['report_path'] = posix_path(out)
        write_json(out, plan)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print_markdown(plan)


if __name__ == '__main__':
    main()
