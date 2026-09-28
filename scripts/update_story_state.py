#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from novelops_common import atomic_write_text, iso_now, read_text, require_project_markers, write_json


def one_line(value):
    """把自由文本字段压成单行。

    字段里带换行时，后半截会落到行首，被 markdown 当成新的结构——例如
    `--state-change $'A\\n## Timeline position'` 会注入一个同名标题，
    破坏后续 upsert_section 的定位。
    """
    return re.sub(r'\s+', ' ', (value or '').strip())


def append_block(path, text):
    """追加一个块。改为读-改-原子写，避免追加中途失败留下半截块。"""
    path = Path(path)
    existing = read_text(path)
    block = text.rstrip() + '\n'
    new_text = existing.rstrip('\n') + '\n\n' + block if existing.strip() else block
    atomic_write_text(path, new_text)


def upsert_section(text, heading, body_lines):
    body = '\n'.join(body_lines).strip()
    block = '## %s\n%s\n' % (heading, body)
    pattern = r'(?ms)^##\s+%s\s*$.*?(?=^##\s+|\Z)' % re.escape(heading)
    if re.search(pattern, text):
        updated = re.sub(pattern, block, text, count=1)
    else:
        updated = text.rstrip() + '\n\n' + block if text.strip() else block
    return updated.rstrip() + '\n'


def build_current_state_text(text, chapter, title, summary, state_changes):
    """纯函数：由现有内容算出更新后的 current_state.md 文本（不落盘）。"""
    timeline_value = 'ch%s accepted - %s' % (chapter, title)
    text = upsert_section(text, 'Timeline position', ['- %s' % timeline_value])

    latest_update = [
        '- chapter: %s' % chapter,
        '- title: %s' % title,
        '- summary: %s' % summary,
        '- state changes:',
    ]
    if state_changes:
        latest_update.extend(['  - %s' % item for item in state_changes])
    else:
        latest_update.append('  - none')
    return upsert_section(text, 'Latest accepted update', latest_update)


def apply_update(project, chapter, title, summary, state_changes, hook_open, hook_advance, hook_close, relationships, emotions):
    project = require_project_markers(project)
    # 所有自由文本先压成单行：换行会落到行首被当成新的 markdown 结构。
    title = one_line(title)
    summary = one_line(summary)
    state_changes = [one_line(x) for x in state_changes]
    hook_open = [one_line(x) for x in hook_open]
    hook_advance = [one_line(x) for x in hook_advance]
    hook_close = [one_line(x) for x in hook_close]
    relationships = [one_line(x) for x in relationships]
    emotions = [one_line(x) for x in emotions]
    summary_path = project / 'chapter_summaries.md'
    current_state_path = project / 'current_state.md'
    hooks_path = project / 'pending_hooks.md'
    matrix_path = project / 'character_matrix.md'
    emotion_path = project / 'emotional_arcs.md'
    updated_files = []

    chapter_block = [
        '## Chapter %s - %s' % (chapter, title),
        '- Summary: %s' % summary,
    ]

    if state_changes:
        chapter_block.append('- State changes:')
        chapter_block.extend(['  - %s' % x for x in state_changes])
    if hook_open:
        chapter_block.append('- Hooks opened:')
        chapter_block.extend(['  - %s' % x for x in hook_open])
    if hook_advance:
        chapter_block.append('- Hooks advanced:')
        chapter_block.extend(['  - %s' % x for x in hook_advance])
    if hook_close:
        chapter_block.append('- Hooks closed:')
        chapter_block.extend(['  - %s' % x for x in hook_close])
    if relationships:
        chapter_block.append('- Relationship changes:')
        chapter_block.extend(['  - %s' % x for x in relationships])
    if emotions:
        chapter_block.append('- Emotional arc changes:')
        chapter_block.extend(['  - %s' % x for x in emotions])

    # 先把两个真值文件的新内容都算出来，再统一落盘：构造期出错不会改动任何文件，
    # 避免出现 chapter_summaries 已更新而 current_state 还是旧值的半套状态。
    summaries_block = '\n'.join(chapter_block)
    current_state_text = build_current_state_text(
        read_text(current_state_path), chapter, title, summary, state_changes)

    append_block(summary_path, summaries_block)
    updated_files.append(str(summary_path))

    atomic_write_text(current_state_path, current_state_text)
    updated_files.append(str(current_state_path))

    if hook_open or hook_advance or hook_close:
        for hook in hook_open:
            append_block(hooks_path, '- [OPEN] %s (opened: ch%s)' % (hook, chapter))
        for hook in hook_advance:
            append_block(hooks_path, '- [ADVANCED] %s (updated: ch%s)' % (hook, chapter))
        for hook in hook_close:
            append_block(hooks_path, '- [PAID OFF] %s (closed: ch%s)' % (hook, chapter))
        updated_files.append(str(hooks_path))

    if relationships:
        for rel in relationships:
            append_block(matrix_path, '- %s (updated: ch%s)' % (rel, chapter))
        updated_files.append(str(matrix_path))

    if emotions:
        for emo in emotions:
            append_block(emotion_path, '- %s (updated: ch%s)' % (emo, chapter))
        updated_files.append(str(emotion_path))

    return {
        'schema_version': 'novelops.state-update.v1',
        'tool': 'update_story_state',
        'generated_at': iso_now(),
        'project': str(project),
        'chapter': chapter,
        'title': title,
        'summary': summary,
        'operations': {
            'state_changes': state_changes,
            'hooks_opened': hook_open,
            'hooks_advanced': hook_advance,
            'hooks_closed': hook_close,
            'relationship_changes': relationships,
            'emotion_changes': emotions,
        },
        'updated_files': updated_files,
    }


def main():
    parser = argparse.ArgumentParser(description='Append structured story-state updates.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--chapter', required=True, type=int)
    parser.add_argument('--title', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--state-change', action='append', default=[])
    parser.add_argument('--hook-open', action='append', default=[])
    parser.add_argument('--hook-advance', action='append', default=[])
    parser.add_argument('--hook-close', action='append', default=[])
    parser.add_argument('--relationship', action='append', default=[])
    parser.add_argument('--emotion', action='append', default=[])
    parser.add_argument('--json', action='store_true', help='Output JSON report.')
    parser.add_argument('--write-report', action='store_true', help='Write JSON report into project/reviews/.')
    args = parser.parse_args()

    report = apply_update(
        args.project,
        args.chapter,
        args.title,
        args.summary,
        args.state_change,
        args.hook_open,
        args.hook_advance,
        args.hook_close,
        args.relationship,
        args.emotion,
    )

    if args.write_report:
        out = Path(args.project) / 'reviews' / ('ch%02d.state-update.json' % args.chapter)
        report['report_path'] = str(out)
        write_json(out, report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('Updated story state in %s' % args.project)


if __name__ == '__main__':
    main()
