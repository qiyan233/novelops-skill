#!/usr/bin/env python3
import argparse
import shutil
import sys
import zipfile
from pathlib import Path

from novelops_common import configure_stdio_utf8

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = 'novelops-skill'
DEFAULT_OUTDIR = ROOT.parent.parent / 'dist'
IGNORE_NAMES = {
    '.git',
    '.smoke-work',
    '.package-work',
    '.novelops-state',
    '.inkos-state',
    'dist',
    'node_modules',
}
IGNORE_FILE_SUFFIXES = {
    '.pyc',
}
IGNORE_FILE_NAMES = {
    '.DS_Store',
}

# 顶层采用白名单：只有这里列出的条目会进入发布包。
# 用排除名单无法识别「用户在仓库内 init 出来的小说项目」——那种目录含整本正文与
# .novelops-state 快照，一旦被收录，发版就等于泄露用户创作数据。
INCLUDE_TOP_LEVEL = {
    '.github',
    '.gitignore',
    'AGENTS.md',
    'CHANGELOG.md',
    'CODE_OF_CONDUCT.md',
    'CONTRIBUTING.md',
    'LICENSE',
    'README.md',
    'SECURITY.md',
    'SKILL.md',
    'VERSION',
    'assets',
    'docs',
    'examples',
    'references',
    'scripts',
}

configure_stdio_utf8()


def normalize_tag(tag):
    tag = (tag or '').replace('\r', '').replace('\n', '').strip()
    if tag and not tag.startswith('v'):
        tag = 'v' + tag
    return tag


def default_version_suffix():
    version_file = ROOT / 'VERSION'
    if not version_file.exists():
        return ''
    return normalize_tag(version_file.read_text(encoding='utf-8'))


def should_skip(path):
    name = path.name
    if name in IGNORE_NAMES:
        return True
    if name.startswith('inkos-smoke-') or name.startswith('novelops-smoke-'):
        return True
    if name.startswith('inkos-package-') or name.startswith('novelops-package-'):
        return True
    if path.is_dir() and name == '__pycache__':
        return True
    if path.is_file() and (path.suffix in IGNORE_FILE_SUFFIXES or name in IGNORE_FILE_NAMES):
        return True
    return False


def copy_tree(src, dst, top_level=False):
    dst.mkdir(parents=True, exist_ok=True)
    skipped = []
    for item in src.iterdir():
        if top_level and item.name not in INCLUDE_TOP_LEVEL:
            skipped.append(item.name)
            continue
        if should_skip(item):
            continue
        target = dst / item.name
        if item.is_dir():
            copy_tree(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    if top_level and skipped:
        # 显式提示，避免维护者新增顶层目录后静默漏打包。
        sys.stderr.write('package: 跳过非发布内容 %s\n' % ', '.join(sorted(skipped)))


def write_zip(stage_root, outfile):
    with zipfile.ZipFile(outfile, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(stage_root.rglob('*')):
            if path.is_dir():
                continue
            arcname = path.relative_to(stage_root.parent)
            zf.write(path, arcname)


def package_skill(outdir='', version_suffix=''):
    outdir = Path(outdir) if outdir else DEFAULT_OUTDIR
    version_suffix = normalize_tag(version_suffix) if version_suffix else default_version_suffix()
    outdir.mkdir(parents=True, exist_ok=True)

    workdir = ROOT / '.package-work'
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        stage_root = workdir / SKILL_NAME
        copy_tree(ROOT, stage_root, top_level=True)

        outfile = outdir / f'{SKILL_NAME}.skill'
        if outfile.exists():
            outfile.unlink()
        write_zip(stage_root, outfile)
        outputs = [str(outfile)]

        if version_suffix:
            versioned = outdir / f'{SKILL_NAME}-{version_suffix}.skill'
            if versioned.exists():
                versioned.unlink()
            shutil.copy2(outfile, versioned)
            outputs.append(str(versioned))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return outputs


def main():
    parser = argparse.ArgumentParser(description='Package the skill into a .skill zip.')
    parser.add_argument('outdir', nargs='?', default='')
    parser.add_argument('version_suffix', nargs='?', default='')
    args = parser.parse_args()

    for output in package_skill(args.outdir, args.version_suffix):
        print(output)


if __name__ == '__main__':
    main()
