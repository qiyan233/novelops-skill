#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from audit_chapter import build_report
from novelops_common import iso_now, read_text, write_json
from novelops_common import posix_path

LOCAL_DIMENSIONS = set([
    'repetition-fatigue',
    'report-speak',
    'crowd-cliche',
    'paragraph-monotony',
    'telling-vs-dramatizing',
    'dialogue-balance',
    'timeline-continuity',
])

TEMPLATES = {
    'repetition-fatigue': 'Keep only the strongest transition beat and cut the repeated connector in nearby sentences.',
    'report-speak': 'Replace abstract explanation with one concrete action, one sensory cue, or one line of dialogue.',
    'crowd-cliche': 'Replace generic crowd response with 1-2 named or specific observers reacting differently.',
    'paragraph-monotony': 'Split or merge nearby paragraphs to create clearer rhythm contrast.',
    'telling-vs-dramatizing': 'Turn the labeled emotion into visible behavior or physical sensation.',
    'dialogue-balance': 'If the scene needs pressure, insert one short exchange instead of more exposition.',
    'timeline-continuity': 'Clarify the transition or trim one time jump marker so the scene timeline reads cleanly.',
}


def load_audit(project, chapter_file, audit_report):
    if audit_report:
        return json.loads(Path(audit_report).read_text(encoding='utf-8'))
    return build_report(project, chapter_file)


def snippet_around(text, token, radius=70):
    if not token:
        return ''
    idx = text.find(token)
    if idx < 0:
        return ''
    start = max(0, idx - radius)
    end = min(len(text), idx + len(token) + radius)
    return text[start:end].replace('\n', ' ').strip()


def build_suggestions(project, chapter_file, audit_report):
    report = load_audit(project, chapter_file, audit_report)
    chapter_ref = report.get('chapter_file') or report.get('chapter')
    chapter_text = read_text(chapter_ref) if chapter_ref else ''
    suggestions = []
    for idx, finding in enumerate(report['findings'], 1):
        if finding['dimension'] not in LOCAL_DIMENSIONS:
            continue
        evidence = finding.get('evidence') or []
        snippet = ''
        for token in evidence:
            snippet = snippet_around(chapter_text, token)
            if snippet:
                break
        suggestions.append({
            'suggestion_id': 'FIX-%03d' % idx,
            'rule_id': finding.get('rule_id'),
            'severity': finding['severity'],
            'dimension': finding['dimension'],
            'snippet': snippet,
            'suggested_action': TEMPLATES.get(finding['dimension'], 'Apply the smallest local patch that resolves the issue.'),
            'repair_targets': finding.get('repair_targets', []),
            'confidence': 'medium' if finding['severity'] in ('critical', 'major') else 'high',
        })
    return {
        'schema_version': 'novelops.spot-fix-suggestions.v1',
        'tool': 'suggest_spot_fixes',
        'generated_at': iso_now(),
        'project': report.get('project'),
        'chapter': report.get('chapter'),
        'chapter_file': report.get('chapter_file') or report.get('chapter'),
        'based_on': {
            'schema_version': report.get('schema_version'),
            'overall': report.get('overall'),
        },
        'summary': {
            'suggestion_count': len(suggestions),
            'local_dimensions': sorted(list(set([s['dimension'] for s in suggestions]))),
        },
        'suggestions': suggestions,
    }


def print_markdown(data):
    print('# Spot-Fix Suggestions')
    print()
    if not data['suggestions']:
        print('- none')
        return
    for item in data['suggestions']:
        print('- [%s/%s] %s' % (item['suggestion_id'], item['rule_id'], item['suggested_action']))
        print('  - dimension: %s' % item['dimension'])
        print('  - confidence: %s' % item['confidence'])
        if item['snippet']:
            print('  - snippet: %s' % item['snippet'])
        if item['repair_targets']:
            print('  - repair_targets: %s' % '; '.join(item['repair_targets']))


def main():
    parser = argparse.ArgumentParser(description='Suggest low-risk spot fixes from a chapter audit.')
    parser.add_argument('--project')
    parser.add_argument('--chapter-file')
    parser.add_argument('--audit-report', help='Existing audit JSON report. If omitted, audit is run on the fly.')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    args = parser.parse_args()

    if not args.audit_report and (not args.project or not args.chapter_file):
        raise SystemExit('Either provide --audit-report or both --project and --chapter-file.')

    data = build_suggestions(args.project, args.chapter_file, args.audit_report)

    if args.write_report:
        project_dir = data.get('project')
        chapter_ref = data.get('chapter_file') or data.get('chapter')
        if not project_dir or not chapter_ref:
            raise SystemExit(
                '--write-report requires "project" and "chapter"/"chapter_file" in the audit report; '
                'the provided --audit-report JSON is missing them. '
                'Pass --project/--chapter-file instead, or omit --write-report.')
        chapter_stem = Path(chapter_ref).stem
        out = Path(project_dir) / 'reviews' / ('%s.spot-fixes.json' % chapter_stem)
        data['report_path'] = posix_path(out)
        write_json(out, data)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_markdown(data)


if __name__ == '__main__':
    main()
