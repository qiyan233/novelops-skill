#!/usr/bin/env python3
import argparse
import difflib
import json
from pathlib import Path

from novelops_common import iso_now, read_text, require_project_markers, snapshot_roots, state_root
from snapshot_story_state import TRACKED_FILES


def is_snapshot_dir(path):
    """快照目录必须含 manifest.json。

    snapshot() 最后才写 manifest，所以它是「快照完整」的标记；只按 is_dir() 判断
    会把中途失败留下的半截目录（缺文件、无 manifest）也当成快照读进来。
    """
    return path.is_dir() and (path / 'manifest.json').is_file()


def resolve_snapshot(project, ref):
    project = Path(project)
    roots = snapshot_roots(project)
    if ref == 'current':
        return {'kind': 'current', 'id': 'current', 'path': project, 'path_str': str(project)}
    if ref == 'latest':
        choices = sorted(
            [p for root in roots for p in root.iterdir() if is_snapshot_dir(p)],
            key=lambda p: p.name,
        )
        if not choices:
            raise SystemExit('No snapshots found under %s' % (state_root(project) / 'snapshots'))
        target = choices[-1]
        return {'kind': 'snapshot', 'id': target.name, 'path': target, 'path_str': str(target)}
    path = Path(ref)
    if is_snapshot_dir(path):
        return {'kind': 'snapshot', 'id': path.name, 'path': path, 'path_str': str(path)}
    for root in roots:
        target = root / ref
        if is_snapshot_dir(target):
            return {'kind': 'snapshot', 'id': target.name, 'path': target, 'path_str': str(target)}
    raise SystemExit('Snapshot ref not found (or incomplete, missing manifest.json): %s' % ref)


def load_file(base, rel):
    """读取快照/项目里的文件，返回 (内容, 是否存在)。

    read_text 对缺失文件返回空串，无法区分「文件被删除」与「文件本来就是空的」，
    会让 diff 的 added/removed 判定失真。
    """
    path = Path(base) / rel
    if not path.is_file():
        return '', False
    return read_text(path), True


def diff_report(project, from_ref, to_ref):
    project = require_project_markers(project)
    left = resolve_snapshot(project, from_ref)
    right = resolve_snapshot(project, to_ref)

    file_diffs = []
    added_total = 0
    removed_total = 0
    changed = 0

    for rel in TRACKED_FILES:
        before, before_present = load_file(left['path'], rel)
        after, after_present = load_file(right['path'], rel)
        if before == after and before_present == after_present:
            continue
        changed += 1
        before_lines = before.splitlines()
        after_lines = after.splitlines()
        udiff = list(difflib.unified_diff(before_lines, after_lines, fromfile='%s:%s' % (left['id'], rel), tofile='%s:%s' % (right['id'], rel), lineterm=''))
        added = sum(1 for line in udiff if line.startswith('+') and not line.startswith('+++'))
        removed = sum(1 for line in udiff if line.startswith('-') and not line.startswith('---'))
        added_total += added
        removed_total += removed
        status = 'changed'
        if not before_present and after_present:
            status = 'added'
        elif before_present and not after_present:
            status = 'removed'
        file_diffs.append({
            'path': rel,
            'status': status,
            'present': {'from': before_present, 'to': after_present},
            'added_lines': added,
            'removed_lines': removed,
            'diff_excerpt': udiff[:80],
        })

    return {
        'schema_version': 'novelops.state-diff.v1',
        'tool': 'diff_story_state',
        'generated_at': iso_now(),
        'project': str(project),
        'from': {'kind': left['kind'], 'id': left['id'], 'path': left['path_str']},
        'to': {'kind': right['kind'], 'id': right['id'], 'path': right['path_str']},
        'summary': {
            'changed_files': changed,
            'added_lines': added_total,
            'removed_lines': removed_total,
        },
        'file_diffs': file_diffs,
    }


def print_markdown(report):
    print('# Story State Diff')
    print()
    print('## Summary')
    print('- from: %s' % report['from']['id'])
    print('- to: %s' % report['to']['id'])
    print('- changed_files: %s' % report['summary']['changed_files'])
    print('- added_lines: %s' % report['summary']['added_lines'])
    print('- removed_lines: %s' % report['summary']['removed_lines'])
    print()
    print('## File diffs')
    if not report['file_diffs']:
        print('- none')
        return
    for item in report['file_diffs']:
        print('- %s (%s, +%s/-%s)' % (item['path'], item['status'], item['added_lines'], item['removed_lines']))


def main():
    parser = argparse.ArgumentParser(description='Diff story-state snapshots or compare a snapshot to current state.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--from', dest='from_ref', required=True)
    parser.add_argument('--to', dest='to_ref', default='current')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    report = diff_report(args.project, args.from_ref, args.to_ref)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)


if __name__ == '__main__':
    main()
