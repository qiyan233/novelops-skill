#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from novelops_common import atomic_write_text, compact_utc_stamp, configure_stdio_utf8, state_root

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
TEMPLATE_DIR = PROJECT_ROOT / 'assets' / 'project-template'
TITLE_PLACEHOLDER = '{{BOOK_TITLE}}'
TITLE_FILES = {'README-project.md', 'story_bible.md', 'book_rules.md', 'outline.md', 'current_state.md'}

configure_stdio_utf8()


def run(cmd, **kwargs):
    result = subprocess.run(cmd, **kwargs)
    raise SystemExit(result.returncode)


def py(script, args):
    return [sys.executable, str(ROOT / script)] + args


def template_relpaths():
    return [path.relative_to(TEMPLATE_DIR) for path in sorted(TEMPLATE_DIR.rglob('*')) if path.is_file()]


def render_template(rel, title):
    text = (TEMPLATE_DIR / rel).read_text(encoding='utf-8')
    if rel.as_posix() in TITLE_FILES:
        return text.replace(TITLE_PLACEHOLDER, title)
    return text


def backup_before_overwrite(project, rels):
    """覆盖前先把将被改写的文件备份到 .novelops-state/backups/pre-init-<stamp>/。

    这是 `init --force` 唯一的不可逆风险点：用户可能已经在模板同名文件里
    写了数十章的真值数据。备份失败就不允许继续覆盖。
    """
    if not rels:
        return None
    dest = state_root(project) / 'backups' / ('pre-init-%s' % compact_utc_stamp())
    for rel in rels:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(project / rel), str(target))
    return dest


def plan_init(project, title, keep_modified):
    """逐文件决定 create / overwrite / unchanged / skip-modified。"""
    plan = []
    for rel in template_relpaths():
        target = project / rel
        rendered = render_template(rel, title)
        if not target.exists():
            plan.append((rel, 'create', rendered))
            continue
        try:
            current = target.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            current = None
        if current == rendered:
            plan.append((rel, 'unchanged', rendered))
        elif keep_modified:
            plan.append((rel, 'skip-modified', rendered))
        else:
            plan.append((rel, 'overwrite', rendered))
    return plan


def init_project(project, title, force=False, keep_modified=False):
    project = Path(project)
    if project.exists() and not project.is_dir():
        raise SystemExit('Init target exists but is not a directory: %s' % project)
    non_empty = project.exists() and any(project.iterdir())
    if non_empty and not force and not keep_modified:
        raise SystemExit(
            'Refusing to initialize non-empty directory: %s. '
            'Use --force to back up existing files then reset them to the template, '
            'or --keep-modified to only fill in missing files.' % project)
    project.mkdir(parents=True, exist_ok=True)
    (project / 'chapters').mkdir(parents=True, exist_ok=True)
    (project / 'reviews').mkdir(parents=True, exist_ok=True)

    plan = plan_init(project, title, keep_modified)
    overwritten = [rel for rel, action, _ in plan if action == 'overwrite']
    backup_dir = backup_before_overwrite(project, overwritten)

    created = []
    for rel, action, rendered in plan:
        if action in ('create', 'overwrite'):
            atomic_write_text(project / rel, rendered)
            created.append(rel)

    skipped = [rel.as_posix() for rel, action, _ in plan if action == 'skip-modified']
    unchanged = sum(1 for _, action, _ in plan if action == 'unchanged')

    print('Initialized novel project at: %s' % project)
    print('Title: %s' % title)
    print('Files: %d written, %d unchanged, %d skipped (modified)'
          % (len(created), unchanged, len(skipped)))
    if skipped:
        print('Skipped (you edited these; nothing was overwritten): %s' % ', '.join(skipped))
    if backup_dir is not None:
        print('Backup of overwritten files: %s' % backup_dir)



def main():
    parser = argparse.ArgumentParser(
        description='Unified CLI entrypoint for NovelOps Skill workflows.',
        epilog='Recommended local invocation: python scripts/novelops_cli.py <command> ...',
    )
    sub = parser.add_subparsers(dest='command')

    p = sub.add_parser('init', help='Initialize a novel project.')
    p.add_argument('project')
    p.add_argument('title')
    p.add_argument('--force', action='store_true',
                   help='Allow a non-empty directory and reset template files (existing files are backed up first).')
    p.add_argument('--keep-modified', action='store_true',
                   help='Only create missing files; never overwrite files you already edited.')

    p = sub.add_parser('context', help='Build next-chapter context.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter', type=int)
    p.add_argument('--recent-chapters', type=int, default=3)
    p.add_argument('--max-chars-per-file', type=int, default=1800)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('write-next', help='Build a structured write-next packet for the next chapter.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter', type=int)
    p.add_argument('--recent-chapters', type=int, default=3)
    p.add_argument('--max-chars-per-file', type=int, default=1800)
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')

    p = sub.add_parser('audit', help='Audit a chapter.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter-file', required=True)
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')

    p = sub.add_parser('knowledge-check', help='Check chapter knowledge boundaries and POV leaks.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter-file', required=True)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('extract-state', help='Extract candidate state updates from a chapter draft.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter-file', required=True)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('reverse-longdoc', help='Split and reverse-analyze a very long source document.')
    p.add_argument('--source', required=True)
    p.add_argument('--workspace', required=True)
    p.add_argument('--chapters-per-file', type=int, default=10)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('hook-report', help='Summarize hook lifecycle status.')
    p.add_argument('--project', required=True)
    p.add_argument('--stale-after', type=int, default=5)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('state-update', help='Append story-state updates.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--summary', required=True)
    p.add_argument('--state-change', action='append', default=[])
    p.add_argument('--hook-open', action='append', default=[])
    p.add_argument('--hook-advance', action='append', default=[])
    p.add_argument('--hook-close', action='append', default=[])
    p.add_argument('--relationship', action='append', default=[])
    p.add_argument('--emotion', action='append', default=[])
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')

    p = sub.add_parser('revision-plan', help='Build a revision plan from an audit or chapter file.')
    p.add_argument('--project')
    p.add_argument('--chapter-file')
    p.add_argument('--audit-report')
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')

    p = sub.add_parser('spot-fixes', help='Suggest low-risk spot fixes from an audit or chapter file.')
    p.add_argument('--project')
    p.add_argument('--chapter-file')
    p.add_argument('--audit-report')
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')

    p = sub.add_parser('revise', help='Run knowledge-check, audit, revision-plan, and spot-fixes as one workflow.')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter-file', required=True)
    p.add_argument('--skip-knowledge-check', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')
    p.add_argument('--summary', action='store_true',
                   help='Compact JSON (counts + coverage) instead of inlining all five reports; use with --json.')
    p.add_argument('--fail-on', choices=['none', 'critical', 'major', 'minor'], default='none',
                   help='Exit 2 when the worst finding reaches this severity (CI gate).')

    p = sub.add_parser('draft', help='Draft the next chapter with an OpenAI-compatible LLM (Hermes-first).')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter', type=int)
    p.add_argument('--out')
    p.add_argument('--force', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--mock-response')
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')
    p.add_argument('--model')
    p.add_argument('--base-url')
    p.add_argument('--temperature', type=float)
    p.add_argument('--top-p', dest='top_p', type=float)
    p.add_argument('--max-tokens', dest='max_tokens', type=int)
    p.add_argument('--timeout', dest='timeout_seconds', type=int)
    p.add_argument('--recent-chapters', type=int, default=3)
    p.add_argument('--max-chars-per-file', type=int, default=1800)

    p = sub.add_parser('auto-revise', help='LLM paragraph-level minimal auto revision (diff by default, --apply to write).')
    p.add_argument('--project', required=True)
    p.add_argument('--chapter-file', required=True)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--force', action='store_true', help='Apply even when the audit overall is "block".')
    p.add_argument('--mock-response')
    p.add_argument('--max-paragraphs', type=int, default=5)
    p.add_argument('--skip-knowledge-check', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('--write-report', action='store_true')
    p.add_argument('--model')
    p.add_argument('--base-url')
    p.add_argument('--temperature', type=float)
    p.add_argument('--top-p', dest='top_p', type=float)
    p.add_argument('--max-tokens', dest='max_tokens', type=int)
    p.add_argument('--timeout', dest='timeout_seconds', type=int)

    p = sub.add_parser('snapshot', help='Create a versioned story-state snapshot.')
    p.add_argument('--project', required=True)
    p.add_argument('--label')
    p.add_argument('--chapter', type=int)
    p.add_argument('--notes')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('diff', help='Diff story-state snapshots or current state.')
    p.add_argument('--project', required=True)
    p.add_argument('--from', dest='from_ref', required=True)
    p.add_argument('--to', dest='to_ref', default='current')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('package', help='Package the skill into a .skill zip (and a versioned copy when VERSION exists).')
    p.add_argument('outdir', nargs='?', default='')
    p.add_argument('version_suffix', nargs='?', default='')

    sub.add_parser('smoke-test', help='Run smoke tests.')

    args = parser.parse_args()

    if args.command == 'init':
        init_project(args.project, args.title, force=args.force, keep_modified=args.keep_modified)
    elif args.command == 'context':
        if args.recent_chapters < 0:
            raise SystemExit('--recent-chapters must be >= 0')
        if args.max_chars_per_file < 0:
            raise SystemExit('--max-chars-per-file must be >= 0')
        cmd = py('build_next_chapter_context.py', ['--project', args.project, '--recent-chapters', str(args.recent_chapters), '--max-chars-per-file', str(args.max_chars_per_file)])
        if args.chapter is not None:
            cmd.extend(['--chapter', str(args.chapter)])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'write-next':
        if args.recent_chapters < 0:
            raise SystemExit('--recent-chapters must be >= 0')
        if args.max_chars_per_file < 0:
            raise SystemExit('--max-chars-per-file must be >= 0')
        cmd = py('build_write_next_packet.py', ['--project', args.project, '--recent-chapters', str(args.recent_chapters), '--max-chars-per-file', str(args.max_chars_per_file)])
        if args.chapter is not None:
            cmd.extend(['--chapter', str(args.chapter)])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'audit':
        cmd = py('audit_chapter.py', ['--project', args.project, '--chapter-file', args.chapter_file])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'knowledge-check':
        cmd = py('knowledge_check.py', ['--project', args.project, '--chapter-file', args.chapter_file])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'extract-state':
        cmd = py('extract_state.py', ['--project', args.project, '--chapter-file', args.chapter_file])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'reverse-longdoc':
        if args.chapters_per_file <= 0:
            raise SystemExit('--chapters-per-file must be > 0')
        cmd = py('reverse_long_document.py', ['--source', args.source, '--workspace', args.workspace, '--chapters-per-file', str(args.chapters_per_file)])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'hook-report':
        if args.stale_after < 0:
            raise SystemExit('--stale-after must be >= 0')
        cmd = py('hook_report.py', ['--project', args.project, '--stale-after', str(args.stale_after)])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'state-update':
        cmd = py('update_story_state.py', ['--project', args.project, '--chapter', str(args.chapter), '--title', args.title, '--summary', args.summary])
        for item in args.state_change:
            cmd.extend(['--state-change', item])
        for item in args.hook_open:
            cmd.extend(['--hook-open', item])
        for item in args.hook_advance:
            cmd.extend(['--hook-advance', item])
        for item in args.hook_close:
            cmd.extend(['--hook-close', item])
        for item in args.relationship:
            cmd.extend(['--relationship', item])
        for item in args.emotion:
            cmd.extend(['--emotion', item])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'revision-plan':
        cmd = py('build_revision_plan.py', [])
        if args.project:
            cmd.extend(['--project', args.project])
        if args.chapter_file:
            cmd.extend(['--chapter-file', args.chapter_file])
        if args.audit_report:
            cmd.extend(['--audit-report', args.audit_report])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'spot-fixes':
        cmd = py('suggest_spot_fixes.py', [])
        if args.project:
            cmd.extend(['--project', args.project])
        if args.chapter_file:
            cmd.extend(['--chapter-file', args.chapter_file])
        if args.audit_report:
            cmd.extend(['--audit-report', args.audit_report])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'revise':
        cmd = py('run_revision_cycle.py', ['--project', args.project, '--chapter-file', args.chapter_file])
        if args.skip_knowledge_check:
            cmd.append('--skip-knowledge-check')
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        if args.summary:
            cmd.append('--summary')
        if args.fail_on != 'none':
            cmd.extend(['--fail-on', args.fail_on])
        run(cmd)
    elif args.command == 'draft':
        cmd = py('draft_chapter.py', ['--project', args.project])
        if args.chapter is not None:
            cmd.extend(['--chapter', str(args.chapter)])
        if args.out:
            cmd.extend(['--out', args.out])
        if args.force:
            cmd.append('--force')
        if args.dry_run:
            cmd.append('--dry-run')
        if args.mock_response:
            cmd.extend(['--mock-response', args.mock_response])
        if args.model:
            cmd.extend(['--model', args.model])
        if args.base_url:
            cmd.extend(['--base-url', args.base_url])
        if args.temperature is not None:
            cmd.extend(['--temperature', str(args.temperature)])
        if args.top_p is not None:
            cmd.extend(['--top-p', str(args.top_p)])
        if args.max_tokens is not None:
            cmd.extend(['--max-tokens', str(args.max_tokens)])
        if args.timeout_seconds is not None:
            cmd.extend(['--timeout', str(args.timeout_seconds)])
        cmd.extend(['--recent-chapters', str(args.recent_chapters)])
        cmd.extend(['--max-chars-per-file', str(args.max_chars_per_file)])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'auto-revise':
        cmd = py('auto_revise.py', ['--project', args.project, '--chapter-file', args.chapter_file])
        if args.dry_run:
            cmd.append('--dry-run')
        if args.apply:
            cmd.append('--apply')
        if args.force:
            cmd.append('--force')
        if args.mock_response:
            cmd.extend(['--mock-response', args.mock_response])
        cmd.extend(['--max-paragraphs', str(args.max_paragraphs)])
        if args.skip_knowledge_check:
            cmd.append('--skip-knowledge-check')
        if args.model:
            cmd.extend(['--model', args.model])
        if args.base_url:
            cmd.extend(['--base-url', args.base_url])
        if args.temperature is not None:
            cmd.extend(['--temperature', str(args.temperature)])
        if args.top_p is not None:
            cmd.extend(['--top-p', str(args.top_p)])
        if args.max_tokens is not None:
            cmd.extend(['--max-tokens', str(args.max_tokens)])
        if args.timeout_seconds is not None:
            cmd.extend(['--timeout', str(args.timeout_seconds)])
        if args.json:
            cmd.append('--json')
        if args.write_report:
            cmd.append('--write-report')
        run(cmd)
    elif args.command == 'snapshot':
        cmd = py('snapshot_story_state.py', ['--project', args.project])
        if args.label:
            cmd.extend(['--label', args.label])
        if args.chapter is not None:
            cmd.extend(['--chapter', str(args.chapter)])
        if args.notes:
            cmd.extend(['--notes', args.notes])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'diff':
        cmd = py('diff_story_state.py', ['--project', args.project, '--from', args.from_ref, '--to', args.to_ref])
        if args.json:
            cmd.append('--json')
        run(cmd)
    elif args.command == 'package':
        cmd = py('package_skill.py', [])
        if args.outdir:
            cmd.append(args.outdir)
        if args.version_suffix:
            cmd.append(args.version_suffix)
        run(cmd)
    elif args.command == 'smoke-test':
        run(py('smoke_test.py', ['--invoked-by-cli']))
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == '__main__':
    main()
