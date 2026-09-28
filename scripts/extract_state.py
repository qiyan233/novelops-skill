#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from novelops_common import iso_now, parse_chapter_number, read_text, require_existing_file, require_project_markers, split_sentences

SUMMARY_HINTS = ['怀疑', '确认', '发现', '决定', '暴露', '受伤', '失去', '拿到']
RELATION_HINTS = ['信任', '怀疑', '敌意', '合作', '试探', '关系']
EMOTION_HINTS = ['愤怒', '恐惧', '警觉', '怀疑', '悲伤', '羞耻', 'anger', 'fear', 'suspicion']
HOOK_HINTS = ['谁', '为何', '为什么', '如何', '秘密', '真相', '幕后', '替换', '去向']
STATE_HINTS = ['确认', '发现', '决定', '知道', '拿到', '失去', '暴露', '受伤', '怀疑', '异常', '不该', '开始', '察觉']


def guess_title(chapter_text, chapter_file):
    for line in chapter_text.splitlines():
        line = line.strip()
        if re.match(r'^#\s+', line):
            return re.sub(r'^#\s+', '', line).strip()
    return Path(chapter_file).stem


def pick_summary(sentences):
    """挑一句作为本章摘要。

    原实现只在前 12 句里打分，长章节真正的转折常在第 12 句之后，摘要于是
    永远取自开头。改为全文打分：关键词命中数优先，其次长度，同分取靠前的那句。
    """
    if not sentences:
        return ''
    best_score = None
    best_sentence = sentences[0]
    for sentence in sentences:
        score = sum(1 for hint in SUMMARY_HINTS if hint in sentence)
        score += min(len(sentence), 120) / 120.0
        if best_score is None or score > best_score:
            best_score = score
            best_sentence = sentence
    return best_sentence


def dedupe_keep_order(items, limit=None):
    out = []
    seen = set()
    for item in items:
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
        if limit and len(out) >= limit:
            break
    return out


def extract_candidates(sentences):
    state_changes = []
    hooks = []
    relationships = []
    emotions = []

    for sentence in sentences:
        if any(hint in sentence for hint in STATE_HINTS):
            state_changes.append(sentence)
        if any(hint in sentence for hint in RELATION_HINTS):
            relationships.append(sentence)
        if any(hint in sentence for hint in EMOTION_HINTS):
            emotions.append(sentence)
        if any(hint in sentence for hint in HOOK_HINTS) and ('？' in sentence or '?' in sentence or '谁' in sentence or '为何' in sentence or '为什么' in sentence):
            hooks.append(sentence.rstrip('。！？!?'))

    hook_open = []
    hook_advance = []
    hook_close = []
    for hook in hooks:
        if any(token in hook for token in ['真相就是', '终于知道', '原来是']):
            hook_close.append(hook)
        elif any(token in hook for token in ['怀疑', '线索', '似乎', '也许']):
            hook_advance.append(hook)
        else:
            hook_open.append(hook)

    return {
        'state_changes': dedupe_keep_order(state_changes, limit=5),
        'hook_open': dedupe_keep_order(hook_open, limit=4),
        'hook_advance': dedupe_keep_order(hook_advance, limit=4),
        'hook_close': dedupe_keep_order(hook_close, limit=4),
        'relationships': dedupe_keep_order(relationships, limit=4),
        'emotions': dedupe_keep_order(emotions, limit=4),
    }


def build_report_from_text(chapter_text, chapter_file='', chapter_num=None, project=None, title_guess_value=None):
    sentences = split_sentences(chapter_text)
    candidates = extract_candidates(sentences)
    guessed_title = title_guess_value or guess_title(chapter_text, chapter_file or 'chapter')
    inferred_chapter = chapter_num
    if inferred_chapter is None:
        inferred_chapter = parse_chapter_number(Path(chapter_file).stem) if chapter_file else None
    if inferred_chapter is None:
        inferred_chapter = parse_chapter_number(chapter_text) or None
    return {
        'schema_version': 'novelops.extract-state.v1',
        'tool': 'extract_state',
        'generated_at': iso_now(),
        'project': str(project) if project is not None else '',
        'chapter': inferred_chapter,
        'chapter_file': str(chapter_file) if chapter_file else '',
        'title_guess': guessed_title,
        'summary': pick_summary(sentences),
        'state_changes': candidates['state_changes'],
        'hook_open': candidates['hook_open'],
        'hook_advance': candidates['hook_advance'],
        'hook_close': candidates['hook_close'],
        'relationships': candidates['relationships'],
        'emotions': candidates['emotions'],
        'write_mode': 'candidate-only',
    }


def build_report(project, chapter_file):
    project = require_project_markers(project)
    chapter_file = require_existing_file(chapter_file, 'Chapter file')
    chapter_text = read_text(chapter_file)
    return build_report_from_text(chapter_text, chapter_file=str(chapter_file), project=project)


def print_markdown(report):
    print('# Extracted State Candidates')
    print()
    print('- title_guess: %s' % report['title_guess'])
    print('- summary: %s' % report['summary'])
    print('- write_mode: %s' % report['write_mode'])
    print()
    for key in ['state_changes', 'hook_open', 'hook_advance', 'hook_close', 'relationships', 'emotions']:
        print('## %s' % key)
        if not report[key]:
            print('- none')
        else:
            for item in report[key]:
                print('- %s' % item)
        print()


def main():
    parser = argparse.ArgumentParser(description='Extract candidate story-state updates from a chapter draft.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--chapter-file', required=True)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    report = build_report(args.project, args.chapter_file)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)


if __name__ == '__main__':
    main()
