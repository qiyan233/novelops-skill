#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from novelops_common import iso_now, require_project_markers, state_root, write_json

TRACKED_FILES = [
    'story_bible.md',
    'book_rules.md',
    'outline.md',
    'current_state.md',
    'chapter_summaries.md',
    'pending_hooks.md',
    'character_matrix.md',
    'emotional_arcs.md',
    'subplot_board.md',
    'continuity_issues.md',
    'style_guide.md',
    'style_profile.json',
    'novelops.config.json',
    'README-project.md',
]


def safe_slug(text):
    text = (text or '').strip().lower()
    text = re.sub(r'[^\w\-]+', '-', text, flags=re.U)
    return text.strip('-') or 'snapshot'


def sha1_file(path):
    h = hashlib.sha1()
    with open(str(path), 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def unique_snapshot_dir(root, snapshot_id):
    dest = root / snapshot_id
    if not dest.exists():
        return snapshot_id, dest
    index = 2
    while True:
        candidate = '%s-%02d' % (snapshot_id, index)
        dest = root / candidate
        if not dest.exists():
            return candidate, dest
        index += 1


def snapshot(project, label=None, chapter=None, notes=None):
    project = require_project_markers(project)
    root = state_root(project) / 'snapshots'
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    parts = [stamp]
    if chapter is not None:
        parts.append('ch%03d' % chapter)
    if label:
        parts.append(safe_slug(label))
    snapshot_id = '-'.join(parts)
    snapshot_id, dest = unique_snapshot_dir(root, snapshot_id)
    dest.mkdir(parents=True, exist_ok=False)

    try:
        copied = []
        missing = []
        for rel in TRACKED_FILES:
            src = project / rel
            if not src.exists():
                missing.append(rel)
                continue
            dst = dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            copied.append({
                'path': rel,
                'bytes': src.stat().st_size,
                'sha1': sha1_file(src),
            })

        manifest = {
            'schema_version': 'novelops.state-snapshot.v1',
            'tool': 'snapshot_story_state',
            'generated_at': iso_now(),
            'project': str(project),
            'snapshot_id': snapshot_id,
            'snapshot_dir': str(dest),
            'label': label,
            'chapter': chapter,
            'notes': notes,
            'files_copied': copied,
            'files_missing': missing,
        }
        # manifest 是「快照完整」的标记：diff 的 latest 只认带 manifest 的目录。
        # 放在最后写，失败了就说明这个快照不完整。
        write_json(dest / 'manifest.json', manifest)

        index = state_root(project) / 'index.jsonl'
        index.parent.mkdir(parents=True, exist_ok=True)
        with index.open('a', encoding='utf-8') as f:
            f.write(json.dumps({
                'snapshot_id': snapshot_id,
                'generated_at': manifest['generated_at'],
                'chapter': chapter,
                'label': label,
                'snapshot_dir': str(dest),
            }, ensure_ascii=False) + '\n')
    except BaseException:
        # 中途失败（文件被占用、磁盘写满）会留下没有 manifest 的半截目录；
        # 留着会被 diff --from latest 选中并读出缺文件的内容。
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description='Create a versioned snapshot of story-state truth files.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--label')
    parser.add_argument('--chapter', type=int)
    parser.add_argument('--notes')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    manifest = snapshot(args.project, args.label, args.chapter, args.notes)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(manifest['snapshot_dir'])


if __name__ == '__main__':
    main()
