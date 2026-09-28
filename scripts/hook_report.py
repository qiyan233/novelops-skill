#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter

from novelops_common import (
    CHAPTER_HEADING_RE,
    iso_now,
    parse_chapter_number,
    read_text,
    require_project_markers,
)

STATUS_ALIASES = {
    'OPEN': 'OPEN',
    'ADVANCED': 'ADVANCED',
    'PAID OFF': 'PAID_OFF',
    'PAID_OFF': 'PAID_OFF',
    'DEFERRED': 'DEFERRED',
    'BROKEN': 'BROKEN',
}

STATUS_ORDER = ['OPEN', 'ADVANCED', 'PAID_OFF', 'DEFERRED', 'BROKEN']


def parse_line(line):
    match = re.match(r'^-\s*\[([^\]]+)\]\s*(.+)$', line.strip())
    if not match:
        return None
    raw_status = match.group(1).strip().upper()
    status = STATUS_ALIASES.get(raw_status)
    if not status:
        return None
    rest = match.group(2).strip()
    chapter_match = re.search(r'\b(?:opened|updated|closed)\s*:\s*ch\s*(\d+)\b', rest, flags=re.I)
    text = re.sub(r'\([^\)]*\)', '', rest).strip()
    return {
        'status': status,
        'hook': text,
        'chapter': int(chapter_match.group(1)) if chapter_match else None,
        'raw': line.strip(),
    }


def fallback_open_hooks(text):
    hooks = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('- '):
            continue
        hooks.append({'status': 'OPEN', 'hook': line[2:].strip(), 'chapter': None, 'raw': line})
    return hooks


def load_hooks(project):
    text = read_text(project / 'pending_hooks.md')
    parsed = [item for item in (parse_line(line) for line in text.splitlines()) if item]
    if parsed:
        return parsed
    return fallback_open_hooks(text)


def latest_chapter_seen(project):
    """最新章号；复用共享解析器以支持中文数字（「第十二章」）。"""
    text = read_text(project / 'chapter_summaries.md')
    chapters = [number for number in
                (parse_chapter_number(match.group(0))
                 for match in re.finditer(CHAPTER_HEADING_RE, text, flags=re.M))
                if number is not None]
    return max(chapters) if chapters else 0


def build_report(project, stale_after):
    project = require_project_markers(project)
    stale_after = int(stale_after)
    if stale_after < 0:
        raise SystemExit('--stale-after must be >= 0')
    hooks = load_hooks(project)
    counts = Counter(item['status'] for item in hooks)
    current_chapter = latest_chapter_seen(project)
    stale_hooks = []
    for item in hooks:
        if item['status'] != 'OPEN':
            continue
        if item['chapter'] is None:
            continue
        age = max(0, current_chapter - item['chapter'])
        if age >= stale_after:
            stale_hooks.append({
                'hook': item['hook'],
                'opened_in': item['chapter'],
                'age_chapters': age,
                'status': item['status'],
            })
    stale_hooks.sort(key=lambda x: (-x['age_chapters'], x['hook']))
    return {
        'schema_version': 'novelops.hook-report.v1',
        'tool': 'hook_report',
        'generated_at': iso_now(),
        'project': str(project),
        'config': {'stale_after': stale_after},
        'summary': {
            'hook_count': len(hooks),
            'counts': {status.lower(): counts.get(status, 0) for status in STATUS_ORDER},
            'current_chapter': current_chapter,
            'stale_hook_count': len(stale_hooks),
        },
        'hooks': hooks,
        'stale_hooks': stale_hooks,
    }


def print_markdown(report):
    print('# Hook Report')
    print()
    print('## Counts')
    for key, value in report['summary']['counts'].items():
        print('- %s: %s' % (key, value))
    print()
    print('## Stale hooks')
    if not report['stale_hooks']:
        print('- none')
    else:
        for item in report['stale_hooks']:
            print('- [%s] %s (opened: ch%s, age: %s)' % (item['status'], item['hook'], item['opened_in'], item['age_chapters']))


def main():
    parser = argparse.ArgumentParser(description='Summarize hook lifecycle status from pending_hooks.md.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--stale-after', type=int, default=5)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    report = build_report(args.project, args.stale_after)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)


if __name__ == '__main__':
    main()
