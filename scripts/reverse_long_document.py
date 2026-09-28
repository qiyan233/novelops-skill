#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from extract_state import build_report_from_text
from novelops_common import (
    atomic_write_text,
    iso_now,
    parse_chinese_numeral,
    read_text,
    require_existing_file,
    write_json,
)

HEADING_PATTERNS = [
    re.compile(r'^\s*#{1,6}\s*(Chapter\s+\d+.*)$', re.I),
    re.compile(r'^\s*(Chapter\s+\d+.*)$', re.I),
    re.compile(r'^\s*(第\s*[0-9一二三四五六七八九十百千零两]+[章节回卷集部篇节].*)$'),
]


def normalize_text(text):
    return (text or '').replace('\r\n', '\n').replace('\r', '\n')


def detect_heading(line):
    stripped = line.strip()
    for pattern in HEADING_PATTERNS:
        match = pattern.match(stripped)
        if match:
            return match.group(1).strip()
    return None


def split_into_chapters(text):
    text = normalize_text(text)
    lines = text.split('\n')
    headings = []
    for idx, line in enumerate(lines):
        heading = detect_heading(line)
        if heading:
            headings.append((idx, heading))
    if not headings:
        raise SystemExit('Could not detect chapter headings in source file.')

    chapters = []
    preface = '\n'.join(lines[:headings[0][0]]).strip()
    for index, (line_no, heading) in enumerate(headings):
        start = line_no
        end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        content_lines = lines[start:end]
        content = '\n'.join(content_lines).strip()
        if index == 0 and preface:
            content = preface + '\n\n' + content
        chapters.append({
            'heading': heading,
            'content': content,
        })
    return chapters


def chapter_number_from_heading(heading, fallback):
    match = re.search(r'Chapter\s+(\d+)', heading, flags=re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'第\s*([0-9一二三四五六七八九十百千零两]+)\s*[章节回卷集部篇节]', heading)
    if match:
        value = parse_chinese_numeral(match.group(1))
        if value is not None:
            return value
    return fallback


def chapter_id(chapter_num):
    return 'ch%04d' % chapter_num


def chunk_file_name(block_index, start_chapter, end_chapter):
    """分块文件名以块序号打头。

    只用起止章号命名的话，源文档章号重复或非单调（例如两章都被解析成同一编号）
    会算出同名文件，后写的块直接覆盖先写的，静默丢掉分块与 chunk_analysis。
    """
    return 'chunk_%04d_chapter_%04d_%04d.json' % (block_index, start_chapter, end_chapter)


def build_index(source_path, chapters, chapters_per_file):
    total = len(chapters)
    chunk_files = []
    chapter_rows = []
    for block_index, chunk_start in enumerate(range(0, total, chapters_per_file)):
        chunk = chapters[chunk_start:chunk_start + chapters_per_file]
        start_chapter = chunk[0]['chapter_num']
        end_chapter = chunk[-1]['chapter_num']
        file_name = chunk_file_name(block_index, start_chapter, end_chapter)
        chunk_files.append({
            'file': file_name,
            'start_chapter': start_chapter,
            'end_chapter': end_chapter,
            'chapter_count': len(chunk),
        })
        for item in chunk:
            chapter_rows.append({
                'chapter_num': item['chapter_num'],
                'chapter_id': item['chapter_id'],
                'title': item['title'],
                'file': file_name,
            })
    return {
        'schema_version': 'novelops.longdoc-index.v1',
        'generated_at': iso_now(),
        'source': str(source_path),
        'total_chapters': total,
        'chapters_per_file': chapters_per_file,
        'chapters': chapter_rows,
        'chunk_files': chunk_files,
    }


def build_chunk_payload(source_path, chapters):
    return {
        'schema_version': 'novelops.longdoc-chunk.v1',
        'generated_at': iso_now(),
        'source': str(source_path),
        'start_chapter': chapters[0]['chapter_num'],
        'end_chapter': chapters[-1]['chapter_num'],
        'chapters': [
            {
                'chapter_num': item['chapter_num'],
                'chapter_id': item['chapter_id'],
                'title': item['title'],
                'char_count': len(item['content']),
                'content': item['content'],
            }
            for item in chapters
        ],
    }


def analyze_chapter(item, source_file):
    report = build_report_from_text(
        item['content'],
        chapter_file='%s:%s' % (source_file, item['chapter_id']),
        chapter_num=item['chapter_num'],
        title_guess_value=item['title'],
    )
    return {
        'chapter_num': item['chapter_num'],
        'chapter_id': item['chapter_id'],
        'title': item['title'],
        'summary': report['summary'],
        'state_changes': report['state_changes'],
        'hooks': {
            'open': report['hook_open'],
            'advance': report['hook_advance'],
            'close': report['hook_close'],
        },
        'relationships': report['relationships'],
        'emotions': report['emotions'],
    }


def build_chunk_analysis(source_file, chunk_payload):
    return {
        'schema_version': 'novelops.longdoc-chunk-analysis.v1',
        'generated_at': iso_now(),
        'source_file': source_file,
        'chapters': [
            analyze_chapter(item, source_file)
            for item in chunk_payload['chapters']
        ],
    }


def dedupe(items):
    out = []
    seen = set()
    for item in items:
        item = (item or '').strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_summary(source_path, analyses):
    chapters = []
    all_state_changes = []
    all_open = []
    all_advance = []
    all_close = []
    all_relationships = []
    all_emotions = []

    for analysis in analyses:
        for chapter in analysis['chapters']:
            chapters.append(chapter)
            all_state_changes.extend(chapter['state_changes'])
            all_open.extend(chapter['hooks']['open'])
            all_advance.extend(chapter['hooks']['advance'])
            all_close.extend(chapter['hooks']['close'])
            all_relationships.extend(chapter['relationships'])
            all_emotions.extend(chapter['emotions'])

    return {
        'schema_version': 'novelops.longdoc-summary.v1',
        'generated_at': iso_now(),
        'source': str(source_path),
        'total_chapters': len(chapters),
        'summary': {
            'total_state_changes': len(dedupe(all_state_changes)),
            'total_hooks': len(dedupe(all_open + all_advance + all_close)),
            'total_relationships': len(dedupe(all_relationships)),
        },
        'chapters': chapters,
        'aggregated': {
            'all_state_changes': dedupe(all_state_changes),
            'all_hooks': {
                'open': dedupe(all_open),
                'advance': dedupe(all_advance),
                'close': dedupe(all_close),
            },
            'all_relationships': dedupe(all_relationships),
            'all_emotions': dedupe(all_emotions),
        },
    }


def summary_markdown(summary):
    lines = [
        '# Long Document Summary',
        '',
        '- total_chapters: %s' % summary['total_chapters'],
        '- total_state_changes: %s' % summary['summary']['total_state_changes'],
        '- total_hooks: %s' % summary['summary']['total_hooks'],
        '- total_relationships: %s' % summary['summary']['total_relationships'],
        '',
        '## Chapters',
    ]
    for chapter in summary['chapters']:
        lines.append('### Chapter %s - %s' % (chapter['chapter_num'], chapter['title']))
        lines.append('- Summary: %s' % chapter['summary'])
        if chapter['state_changes']:
            lines.append('- State changes:')
            lines.extend(['  - %s' % item for item in chapter['state_changes']])
        if chapter['hooks']['open']:
            lines.append('- Hooks opened:')
            lines.extend(['  - %s' % item for item in chapter['hooks']['open']])
        if chapter['hooks']['advance']:
            lines.append('- Hooks advanced:')
            lines.extend(['  - %s' % item for item in chapter['hooks']['advance']])
        if chapter['hooks']['close']:
            lines.append('- Hooks closed:')
            lines.extend(['  - %s' % item for item in chapter['hooks']['close']])
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def run_pipeline(source, workspace, chapters_per_file):
    source_path = require_existing_file(source, 'Source file')
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    index_dir = workspace / 'index'
    chunks_dir = workspace / 'chunks'
    analysis_dir = workspace / 'reverse_analysis' / 'chunk_analysis'
    summary_dir = workspace / 'reverse_analysis' / 'summary'
    for path in (index_dir, chunks_dir, analysis_dir, summary_dir):
        path.mkdir(parents=True, exist_ok=True)

    raw_text = read_text(source_path)
    chapters_raw = split_into_chapters(raw_text)
    chapters = []
    for idx, item in enumerate(chapters_raw, 1):
        chapter_num = chapter_number_from_heading(item['heading'], idx)
        chapters.append({
            'chapter_num': chapter_num,
            'chapter_id': chapter_id(chapter_num),
            'title': item['heading'],
            'content': item['content'],
        })

    index_payload = build_index(source_path, chapters, chapters_per_file)
    index_path = index_dir / 'chapter_list.json'
    write_json(index_path, index_payload)

    analyses = []
    chunk_files = []
    for block_index, start in enumerate(range(0, len(chapters), chapters_per_file)):
        chunk = chapters[start:start + chapters_per_file]
        file_name = chunk_file_name(block_index, chunk[0]['chapter_num'], chunk[-1]['chapter_num'])
        chunk_path = chunks_dir / file_name
        chunk_payload = build_chunk_payload(source_path, chunk)
        write_json(chunk_path, chunk_payload)
        chunk_files.append(str(chunk_path))

        analysis_payload = build_chunk_analysis(file_name, chunk_payload)
        analysis_path = analysis_dir / file_name.replace('.json', '_analysis.json')
        write_json(analysis_path, analysis_payload)
        analyses.append(analysis_payload)

    summary_payload = build_summary(source_path, analyses)
    summary_json_path = summary_dir / 'summary.json'
    summary_md_path = summary_dir / 'summary.md'
    write_json(summary_json_path, summary_payload)
    atomic_write_text(summary_md_path, summary_markdown(summary_payload))

    return {
        'schema_version': 'novelops.longdoc-reverse.v1',
        'tool': 'reverse_long_document',
        'generated_at': iso_now(),
        'source': str(source_path),
        'workspace': str(workspace),
        'summary': {
            'total_chapters': len(chapters),
            'chunk_file_count': len(chunk_files),
            'analysis_file_count': len(analyses),
        },
        'outputs': {
            'index': str(index_path),
            'chunks_dir': str(chunks_dir),
            'chunk_analysis_dir': str(analysis_dir),
            'summary_json': str(summary_json_path),
            'summary_md': str(summary_md_path),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Split and reverse-analyze a very long chaptered source document.')
    parser.add_argument('--source', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--chapters-per-file', type=int, default=10)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if args.chapters_per_file <= 0:
        raise SystemExit('--chapters-per-file must be > 0')

    report = run_pipeline(args.source, args.workspace, args.chapters_per_file)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report['outputs']['summary_json'])


if __name__ == '__main__':
    main()
