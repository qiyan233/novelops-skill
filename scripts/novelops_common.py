#!/usr/bin/env python3
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


# 章节号可用的数字字符：阿拉伯数字 + 中文数字（网文常用「第一章」）。
# 供章节标题正则与 parse_chapter_number 共用，避免两处能力不一致。
CN_NUMERAL_CHARS = '0-9零一二两三四五六七八九十百千'
CHAPTER_HEADING_RE = r'^##\s+(?:Chapter\s+\d+.*|第\s*[%s]+\s*章.*)$' % CN_NUMERAL_CHARS
TRUNCATION_SUFFIX = '\n...[truncated]'
DEFAULT_PROJECT_MARKERS = [
    'README-project.md',
    'story_bible.md',
    'book_rules.md',
    'outline.md',
    'current_state.md',
]
STATE_DIR_NAME = '.novelops-state'
LEGACY_STATE_DIR_NAME = '.inkos-state'


def state_root(project):
    """写入用：始终返回 <project>/.novelops-state（不创建目录）。"""
    return Path(project) / STATE_DIR_NAME


def snapshot_roots(project):
    """读取用：按优先级返回存在的快照根目录列表（新目录在前，旧目录兜底）。"""
    project = Path(project)
    return [project / name / 'snapshots'
            for name in (STATE_DIR_NAME, LEGACY_STATE_DIR_NAME)
            if (project / name / 'snapshots').exists()]


def configure_stdio_utf8():
    for stream in (getattr(sys, 'stdout', None), getattr(sys, 'stderr', None)):
        if stream is None:
            continue
        reconfigure = getattr(stream, 'reconfigure', None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


configure_stdio_utf8()


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def require_existing_dir(path, label='Project'):
    path = Path(path)
    if not path.exists():
        raise SystemExit('%s does not exist: %s' % (label, path))
    if not path.is_dir():
        raise SystemExit('%s is not a directory: %s' % (label, path))
    return path


def require_existing_file(path, label='File'):
    path = Path(path)
    if not path.exists():
        raise SystemExit('%s does not exist: %s' % (label, path))
    if not path.is_file():
        raise SystemExit('%s is not a file: %s' % (label, path))
    return path


def require_project_markers(project, markers=None):
    project = require_existing_dir(project, 'Project')
    markers = list(markers or DEFAULT_PROJECT_MARKERS)
    if markers and not any((project / name).exists() for name in markers):
        raise SystemExit('Project does not look initialized: no standard NovelOps files found under %s' % project)
    return project


def read_text(path):
    path = Path(path)
    return path.read_text(encoding='utf-8') if path.exists() else ''


def detect_newline(path, default='\n'):
    """探测文件原有换行风格，供整文件回写时保持一致，避免 LF/CRLF 被整体翻转。"""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return default
    crlf = raw.count(b'\r\n')
    lf = raw.count(b'\n') - crlf
    return '\r\n' if crlf > lf else default


def atomic_write_text(path, text, encoding='utf-8'):
    """同目录临时文件 + fsync + os.replace 原子替换，返回最终路径。

    write_text 会先截断原文件；中途失败（进程被杀、磁盘写满、Windows 文件被占用）
    会留下半截内容——对小说正文和真值文件来说等于丢稿，且没有回滚点。
    写入用 newline='' 关闭换行转换，保留调用方给出的原始换行。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding=encoding, newline='') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def limit_chars(text, max_chars):
    text = (text or '').strip()
    if max_chars is None:
        return text
    if max_chars <= 0:
        return ''
    if len(text) <= max_chars:
        return text
    if max_chars <= len(TRUNCATION_SUFFIX):
        return text[:max_chars]
    return text[: max_chars - len(TRUNCATION_SUFFIX)].rstrip() + TRUNCATION_SUFFIX


def chapter_sections(text, heading_re):
    matches = list(re.finditer(heading_re, text or '', flags=re.M))
    if not matches:
        return []
    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((match.group(0), text[start:end].strip()))
    return sections


def latest_sections(markdown, heading_re, count, max_chars=2000):
    count = int(count or 0)
    sections = chapter_sections(markdown, heading_re)
    if count <= 0:
        return ''
    if not sections:
        return limit_chars(markdown, max_chars)
    joined = '\n\n'.join(section for _heading, section in sections[-count:])
    return limit_chars(joined, max_chars)


def extract_bullets(text):
    return [m.group(1).strip() for m in re.finditer(r'^-\s+(.+)$', text or '', flags=re.M)]


def extract_keywords(text, min_len=2, limit=None):
    # [^\W_] = \u5355\u8bcd\u5b57\u7b26\u53bb\u6389\u4e0b\u5212\u7ebf\uff0c\u5373\u300c\u4e2d\u65e5\u97e9 + \u5b57\u6bcd + \u6570\u5b57\u300d\u7684\u8fde\u7eed\u4e32\u3002
    # \u6570\u5b57\u8981\u4fdd\u7559\u5728\u8bcd\u91cc\uff1a\u5426\u5219\u300c\u7b2c1990\u5e74\u7684\u7ea6\u5b9a\u300d\u4f1a\u88ab\u5207\u6210\u300c\u5e74\u7684\u7ea6\u5b9a\u300d\uff0c
    # \u5e74\u4efd\u6d88\u5931\u540e\u8fd9\u7c7b\u788e\u7247\u5728\u6b63\u6587\u91cc\u968f\u5904\u53ef\u89c1\uff0c\u4f1a\u8ba9 outline-drift \u4e4b\u7c7b\u7684\u6bd4\u5bf9\u5931\u771f\u3002
    words = re.findall(r'[^\W_]{%d,}' % min_len, text or '')
    out = []
    seen = set()
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        out.append(word)
        if limit and len(out) >= limit:
            break
    return out


def normalize_space(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def strip_markdown_headings(text):
    lines = []
    for line in (text or '').splitlines():
        if re.match(r'^\s*#', line):
            continue
        lines.append(line)
    return '\n'.join(lines)


_FENCE_RE = re.compile(r'^\s*```[^\n]*\n(?P<body>.*?)\n?\s*```\s*$', re.S)

# 「以下是正文」式开场白的关键词。必须配合「短行 + 冒号结尾」才判定，
# 否则会把「可以想象……」这类正常句子开头误伤。
_LEADIN_KEYWORDS = (
    '好的', '当然', '明白', '收到', '以下', '下面', '如下', '这是',
    '创作说明', '说明如下', '修订后', '修改后', '重写后', '改写后',
)

# 整行都是创作说明的（出现在开头或结尾）
_META_LINE_RE = re.compile(
    r'^\s*[（(【\[]?\s*(?:创作说明|修改说明|修订说明|改写说明)\s*[:：]')


def _is_lead_in(line):
    """短行 + 冒号结尾 + 含引导词 → 判为模型开场白。

    正文段落几乎不会以冒号结尾，而开场白几乎总是，所以这个组合足够保守。
    """
    line = line.strip()
    if not line or len(line) > 40 or not line.endswith(('：', ':')):
        return False
    return any(keyword in line for keyword in _LEADIN_KEYWORDS)


def strip_code_fence(text):
    """整体被 ``` 包裹时剥掉围栏，返回围栏内容；否则原样返回。"""
    text = (text or '').strip()
    match = _FENCE_RE.match(text)
    return match.group('body').strip() if match else text


def strip_model_preamble(text):
    """去掉模型加在正文前后的客套话与创作说明行。

    模型即使被要求「只输出正文」，也常加「好的，以下是修订后的段落：」这类开场白；
    这些文字一旦写回就变成作品正文的一部分。
    """
    lines = (text or '').splitlines()
    while lines and (not lines[0].strip() or _META_LINE_RE.match(lines[0].strip()) or _is_lead_in(lines[0])):
        lines.pop(0)
    while lines and (not lines[-1].strip() or _META_LINE_RE.match(lines[-1].strip())):
        lines.pop()
    return '\n'.join(lines).strip()


def clean_model_output(text):
    """模型输出通用净化：交替剥离开场白与代码围栏，直到结果稳定。

    必须反复迭代：模型常写成「好的，以下是…：」+ 围栏包裹，只做一轮的话
    先剥围栏会因文本不以 ``` 开头而失效，先剥开场白又会把围栏留在原地。
    """
    text = (text or '').strip()
    for _ in range(5):
        updated = strip_model_preamble(strip_code_fence(text))
        if updated == text:
            break
        text = updated
    return text


SENTENCE_END_CHARS = '。！？!?'
QUOTE_PAIRS = {'「': '」', '『': '』', '“': '”', '‘': '’', '《': '》'}
QUOTE_CLOSERS = set(QUOTE_PAIRS.values())


def split_sentences(text):
    """按句末标点切句；成对中文引号/书名号内部的标点不切开。

    否则对话会被切碎：「你到底是谁？」会变成「你到底是谁 与孤立的 」
    两个片段，残片会混进候选句、证据串和摘要。
    跨行时重置引号深度，避免一个未闭合的「把整章吞成一个句子。
    """
    text = strip_markdown_headings(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    segments = []
    buffer = []
    depth = 0
    for ch in text:
        if ch == '\n':
            if buffer:
                segments.append(''.join(buffer))
                buffer = []
            depth = 0
            continue
        buffer.append(ch)
        if ch in QUOTE_PAIRS:
            depth += 1
            continue
        if ch in QUOTE_CLOSERS and depth > 0:
            depth -= 1
            continue
        if depth == 0 and ch in SENTENCE_END_CHARS:
            segments.append(''.join(buffer))
            buffer = []
    if buffer:
        segments.append(''.join(buffer))

    parts = []
    for segment in segments:
        part = normalize_space(segment)
        if not part:
            continue
        parts.append(part)
    return parts


def extract_markdown_section(text, heading_title):
    pattern = r'^##\s+%s\s*$' % re.escape(heading_title)
    match = re.search(pattern, text or '', flags=re.M)
    if not match:
        return ''
    start = match.end()
    next_match = re.search(r'^##\s+.+$', (text or '')[start:], flags=re.M)
    end = start + next_match.start() if next_match else len(text or '')
    return (text or '')[start:end].strip()


CN_NUM_DIGITS = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
                 '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
CN_NUM_UNITS = {'十': 10, '百': 100, '千': 1000}


def parse_chinese_numeral(text):
    """把中文数字（一/十二/一百零三/两百/三千二百一十五，支持到千位）解析为 int；无法解析返回 None。"""
    text = (text or '').strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    total = 0
    num = 0
    seen = False
    for ch in text:
        if ch in CN_NUM_DIGITS:
            num = CN_NUM_DIGITS[ch]
            seen = True
        elif ch in CN_NUM_UNITS:
            total += (num or 1) * CN_NUM_UNITS[ch]
            num = 0
            seen = True
        else:
            return None
    return total + num if seen else None


def parse_chapter_number(label):
    text = normalize_space(label)
    match = re.search(r'Chapter\s+(\d+)', text, flags=re.I)
    if match:
        return int(match.group(1))
    match = re.search(r'第\s*([%s]+)\s*章' % CN_NUMERAL_CHARS, text)
    if match:
        return parse_chinese_numeral(match.group(1))
    match = re.search(r'\bch(?:apter)?[\s_-]*(\d+)\b', text, flags=re.I)
    if match:
        return int(match.group(1))
    return None


def infer_next_chapter_from_project(project, explicit_chapter=None):
    if explicit_chapter is not None:
        return int(explicit_chapter)

    project = Path(project)
    numbers = []

    summaries = read_text(project / 'chapter_summaries.md')
    for heading, _section in chapter_sections(summaries, CHAPTER_HEADING_RE):
        chapter = parse_chapter_number(heading)
        if chapter is not None:
            numbers.append(chapter)

    chapters_dir = project / 'chapters'
    if chapters_dir.exists():
        for path in chapters_dir.iterdir():
            if not path.is_file():
                continue
            chapter = parse_chapter_number(path.stem) or parse_chapter_number(path.name)
            if chapter is not None:
                numbers.append(chapter)

    return max(numbers) + 1 if numbers else 1
