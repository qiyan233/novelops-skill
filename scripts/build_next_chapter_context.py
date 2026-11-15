#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from novelops_common import (
    CHAPTER_HEADING_RE,
    infer_next_chapter_from_project,
    iso_now,
    limit_chars,
    latest_sections,
    read_text,
    require_project_markers,
    posix_path,
)

FILES = [
    'story_bible.md',
    'book_rules.md',
    'outline.md',
    'current_state.md',
    'chapter_summaries.md',
    'pending_hooks.md',
    'character_matrix.md',
    'character_knowledge.md',
    'emotional_arcs.md',
    'subplot_board.md',
    'style_guide.md',
]


def select_outline_excerpt(text, target_chapter, max_chars):
    text = (text or '').strip()
    if not text:
        return ''
    lines = text.splitlines()
    patterns = [
        r'^\s*-\s*ch%s:\s*(.+)$' % target_chapter,
        r'^\s*-\s*chapter\s+%s:\s*(.+)$' % target_chapter,
        r'^\s*-\s*第\s*%s\s*章[:：]\s*(.+)$' % target_chapter,
    ]
    matched_index = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if any(re.match(pattern, stripped, flags=re.I) for pattern in patterns):
            matched_index = idx
            break
    if matched_index is None:
        return limit_chars(text, max_chars)

    heading_index = matched_index
    while heading_index > 0:
        if re.match(r'^\s*##\s+', lines[heading_index], flags=re.M):
            break
        heading_index -= 1

    excerpt_lines = []
    if re.match(r'^\s*##\s+', lines[heading_index], flags=re.M):
        excerpt_lines.append(lines[heading_index].rstrip())
    excerpt_lines.append(lines[matched_index].rstrip())
    excerpt = '\n'.join(excerpt_lines).strip()
    return limit_chars(excerpt or text, max_chars)


def build_context_report(project, recent_chapters, max_chars_per_file, chapter=None):
    project = require_project_markers(project)
    target_chapter = infer_next_chapter_from_project(project, chapter)
    sections = {}
    section_meta = {}

    for name in FILES:
        text = read_text(project / name)
        if not text:
            continue
        original_chars = len(text.strip())
        if name == 'chapter_summaries.md':
            text = latest_sections(text, CHAPTER_HEADING_RE, recent_chapters, max_chars=max_chars_per_file)
        elif name == 'outline.md':
            text = select_outline_excerpt(text, target_chapter, max_chars_per_file)
        else:
            text = limit_chars(text, max_chars_per_file)
        sections[name] = text.strip()
        section_meta[name] = {
            'chars': len(sections[name]),
            'truncated': len(sections[name]) < original_chars,
        }

    prompt = []
    prompt.append('# Next Chapter Context')
    prompt.append('')
    prompt.append('Use this context to plan and draft the next chapter. Preserve continuity, character locks, world rules, and hook discipline.')
    prompt.append('')
    prompt.append('Target chapter: %s' % target_chapter)
    prompt.append('')
    for name in FILES:
        if name not in sections:
            continue
        prompt.append('## %s' % name)
        prompt.append(sections[name])
        prompt.append('')

    prompt.append('## Writing instructions')
    prompt.append('- Draft exactly one chapter only: chapter %s.' % target_chapter)
    prompt.append('- State the chapter function before drafting.')
    prompt.append('- Advance at least one active hook unless the chapter is deliberately transitional.')
    prompt.append('- Respect information boundaries: do not let characters know what they should not know.')
    prompt.append('- Do not output chapter %s, chapter %s, or multiple chapter headings in one response.' % (target_chapter + 1, target_chapter + 2))
    prompt.append('- Prefer spot-fixable prose over risky structural overreach.')
    prompt.append('- Stop after the current chapter ends; do not continue into later chapters.')
    prompt.append('- After acceptance, update chapter_summaries, current_state, pending_hooks, and relationship/emotion files.')

    return {
        'schema_version': 'novelops.next-context.v1',
        'tool': 'build_next_chapter_context',
        'generated_at': iso_now(),
        'project': posix_path(project),
        'target_chapter': target_chapter,
        'config': {
            'recent_chapters': recent_chapters,
            'max_chars_per_file': max_chars_per_file,
        },
        'single_chapter_contract': [
            'Draft exactly one chapter only: chapter %s.' % target_chapter,
            'Do not output multiple chapter headings or continue into later chapters.',
            'Stop after the current chapter ends.',
        ],
        'files_loaded': list(sections.keys()),
        'summary': {
            'section_count': len(sections),
            'context_chars': len('\n'.join(prompt).strip()),
        },
        'section_meta': section_meta,
        'sections': sections,
        'context': '\n'.join(prompt).strip() + '\n',
    }


def main():
    parser = argparse.ArgumentParser(description='Build a compact next-chapter context from truth files.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--chapter', type=int)
    parser.add_argument('--recent-chapters', type=int, default=3)
    parser.add_argument('--max-chars-per-file', type=int, default=1800)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if args.recent_chapters < 0:
        raise SystemExit('--recent-chapters must be >= 0')
    if args.max_chars_per_file < 0:
        raise SystemExit('--max-chars-per-file must be >= 0')

    report = build_context_report(args.project, args.recent_chapters, args.max_chars_per_file, args.chapter)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report['context'])


if __name__ == '__main__':
    main()
