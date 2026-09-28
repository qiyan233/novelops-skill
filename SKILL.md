---
name: novelops-skill
description: Novel-production operating system skill for long-form fiction, web novels, serials, fanfiction, and side stories. Use when designing or running a structured writing pipeline with persistent world state, chapter summaries, hooks, character matrices, continuity audits, rewrite/revise loops, style guides, or per-book rules. Best for requests like building an InkOS-inspired novel workflow skill, creating a long-novel workflow, keeping multi-chapter story consistency, generating/auditing/revising chapters, or maintaining story files across many chapters.
---

# NovelOps Skill

Version: 1.1.0

Build and run long-form fiction as a stateful pipeline, not a one-shot prompt.

Treat this skill as a **novel OS skeleton**: it provides project structure, workflow, audit criteria, and helper scripts for a stateful long-form writing system that is conceptually close to InkOS.

**Agent-oriented, not host-specific.** The bundled tooling is a plain Python 3 CLI (stdlib only) over plain-text Markdown/JSON state files, so it does not depend on any particular agent runtime — OpenClaw, Claude Code, IDE-embedded agents, terminal agents, or a human at a terminal can all drive it. See `docs/agent-integration.md` for per-host setup.

## Core operating model / 核心运行模型

Use this loop:

1. **Load truth files**
2. **Plan the next chapter**
3. **Draft with constraints** — 可由人或 agent 执笔；也可用 `draft` 命令交给 Hermes 等 OpenAI 兼容模型自动起草（见下文 Bundled tools）
4. **Run knowledge-boundary checks when the chapter depends on hidden truths or limited POV**
5. **Audit for continuity / style / pacing / leaks**
6. **Revise with spot fixes first** — 局部性问题可用 `auto-revise` 命令做 LLM 段落级最小化重写（默认只出 diff，`--apply` 才写回）
7. **Extract candidate state updates from the accepted draft**
8. **Update story state**
9. **Queue unresolved issues for human review**

Prefer stable files over fragile memory. If information matters in later chapters, write it into a truth file.

## Project layout / 项目结构

When starting a new project, copy the template from `assets/project-template/`.

Expected files:

- `story_bible.md` — world rules, premise, factions, locations, power system
- `book_rules.md` — per-book rules, prohibitions, protagonist locks, tone limits
- `outline.md` — macro arc, chapter targets, payoff plan
- `current_state.md` — authoritative latest world state
- `chapter_summaries.md` — per-chapter summaries and state deltas
- `pending_hooks.md` — open promises, foreshadowing, unresolved conflicts
- `character_matrix.md` — who met whom, trust/conflict, information boundaries
- `character_knowledge.md` — optional structured knowledge boundary tracker for major characters
- `emotional_arcs.md` — tracked emotional movement by key character
- `subplot_board.md` — A/B/C line progress and stagnation notes
- `continuity_issues.md` — known inconsistencies or manual review backlog
- `style_guide.md` — qualitative style guide
- `style_profile.json` — optional quantitative style stats
- `novelops.config.json` — optional project config: LLM endpoint/model, audit rule overrides, knowledge-check overrides
- `chapters/` — chapter markdown files
- `reviews/` — audit and revision reports

`current_state.md` is the most important operational file. Keep it compact, current, and explicit.

## Recommended CLI workflow / 推荐 CLI 工作流

默认优先使用统一入口：

```bash
python scripts/novelops_cli.py <command> ...
```

这样更适合日常使用、文档引用和后续自动化；底层脚本仍可直接调用，但建议视为 advanced / lower-level usage。

### Quick start / 快速开始

#### 1) Initialize a project / 初始化项目

推荐：

```bash
python scripts/novelops_cli.py init /path/to/project "Book Title"
```

默认不会初始化到非空目录，避免覆盖已有小说项目；如果你确认要覆盖模板文件，可显式追加 `--force`。

Lower-level usage / 底层脚本方式：

```bash
bash scripts/init_novel_project.sh /path/to/project "Book Title"
```

This copies the template and creates the standard directory layout.
For cross-platform usage, prefer `python scripts/novelops_cli.py init ...`.

#### 2) Build next-chapter context / 构建下一章上下文

推荐：

```bash
python scripts/novelops_cli.py context \
  --project /path/to/project \
  --recent-chapters 3 \
  --json
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/build_next_chapter_context.py \
  --project /path/to/project \
  --recent-chapters 3 \
  --json
```

#### 3) Build write-next packet / 构建下一章工作包

推荐：

```bash
python scripts/novelops_cli.py write-next \
  --project /path/to/project \
  --json
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/build_write_next_packet.py \
  --project /path/to/project \
  --json
```

Use this when you want a more structured handoff than raw context: chapter goal, active hooks, constraints, state targets, suggested scene beats, and a single-chapter output contract.

## Workflow / 工作流

### 1) Before writing a chapter / 写章前准备

Read at least:

- `story_bible.md`
- `book_rules.md`
- `outline.md`
- `current_state.md`
- latest section of `chapter_summaries.md`
- `pending_hooks.md`
- `character_matrix.md`

If maintained, also read:

- `character_knowledge.md`

If the request is for a side story, prequel, sequel, or alternate timeline, also establish:

- parent canon constraints
- divergence point
- what characters do **not** know yet
- which original hooks must remain untouched

### 2) Planning rules / 规划规则

Before drafting, explicitly decide:

- chapter purpose
- POV
- conflict driver
- payoff or partial payoff
- hooks to advance, delay, or close
- state changes that must occur
- constraints that must not be violated

Write a short chapter plan into the response or a scratch file if useful.

### 3) Drafting rules / 起草规则

Draft from observed reality, not abstract explanation.

Prefer:

- concrete action
- sensory evidence
- state changes that can be tracked later
- character knowledge limited to what they have seen, inferred, or been told
- exactly one target chapter per draft

Avoid:

- breaking protagonist personality lock
- introducing untracked items/powers/injuries
- resolving major hooks accidentally
- report-speak in narrative prose
- broad whole-crowd reactions unless earned
- full-chapter rewrites when only a few lines are broken
- drafting chapter N and chapter N+1 in the same response
- multiple chapter headings in one draft
- continuing into later chapters after the current chapter has already landed its ending beat

### 4) Knowledge-boundary pass / 信息边界检查

When the chapter depends on mystery, hidden truths, or strict POV, run:

推荐：

```bash
python scripts/novelops_cli.py knowledge-check \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch12.md \
  --json
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/knowledge_check.py \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch12.md \
  --json
```

Use this to catch:

- characters knowing facts too early
- narration slipping into omniscient scope
- side-story / prequel spoiler contamination
- certainty that should still be suspicion

### 5) Audit pass / 审计检查

After drafting, audit against `references/audit-dimensions.md`.

Minimum audit set:

- continuity / timeline
- character consistency
- information boundary leaks
- world-rule violations
- unresolved logic gaps
- pacing / subplot movement
- repetitive diction / fatigue terms
- outline drift

Recommended command:

```bash
python scripts/novelops_cli.py audit \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch12.md \
  --json
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/audit_chapter.py \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch12.md \
  --json
```

Write reports into `reviews/` when operating on files.

### 6) Revision policy / 修订策略

Prefer this order:

1. **spot-fix** — patch only bad sentences/paragraphs
2. **polish** — improve local expression without changing story events
3. **rewrite scene** — only if scene logic is broken
4. **rewrite chapter** — last resort

Do not silently change:

- names
- outcomes of key events
- resource counts / power levels
- relationship states
- what characters know

If any of the above changes, also update truth files.

### 7) State extraction and update / 状态提取与更新

After a chapter is accepted, first extract candidate updates:

推荐：

```bash
python scripts/novelops_cli.py extract-state \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch12.md \
  --json
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/extract_state.py \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch12.md \
  --json
```

This produces candidate:

- summary
- state changes
- hook open / advance / close items
- relationship changes
- emotional changes

Then feed approved items into:

推荐：

```bash
python scripts/novelops_cli.py state-update \
  --project /path/to/project \
  --chapter 12 \
  --title "The Price of Silence" \
  --summary "..." \
  --state-change "Lin Jin now knows the token is fake" \
  --hook-open "Who replaced the token?" \
  --relationship "Lin Jin -> Xu An: trust decreased" \
  --emotion "Lin Jin: suspicion hardens into anger"
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/update_story_state.py \
  --project /path/to/project \
  --chapter 12 \
  --title "The Price of Silence" \
  --summary "..." \
  --state-change "Lin Jin now knows the token is fake" \
  --hook-open "Who replaced the token?" \
  --relationship "Lin Jin -> Xu An: trust decreased" \
  --emotion "Lin Jin: suspicion hardens into anger"
```

This updates `chapter_summaries.md` and also syncs `current_state.md` with the latest accepted chapter position plus a compact accepted-update block.

### 8) Hook pressure review / 钩子压力复核

When many hooks are active, run:

推荐：

```bash
python scripts/novelops_cli.py hook-report \
  --project /path/to/project \
  --stale-after 5 \
  --json
```

Lower-level usage / 底层脚本方式：

```bash
python scripts/hook_report.py \
  --project /path/to/project \
  --stale-after 5 \
  --json
```

Use this to spot:

- stale hooks that have been open too long
- current hook counts by status
- backlog pressure before the next chapter

## Modes to support / 支持模式

### Full pipeline mode / 全流程模式

Use when the user says things like:

- write the next chapter
- continue the novel
- run the full story pipeline
- draft and audit this chapter

Sequence:

1. run `write-next`
2. plan from chapter function and scene beats
3. draft
4. run `revise` or, if needed, knowledge-check + audit separately
5. extract candidate state
6. update state

In this mode, the draft should be **exactly one chapter**, not a chapter bundle.

### Audit-only mode / 仅审计模式

Use when the user already has chapter text and wants:

- continuity check
- OOC check
- pacing review
- world-rule validation
- AI-ish writing detection

Read `references/audit-dimensions.md`, produce findings grouped by severity, then propose minimal edits.

### State-maintenance mode / 状态维护模式

Use when the user says:

- remember this chapter
- update the story bible
- update hooks / character relations / arcs
- summarize what changed

Focus on truth-file accuracy, not prose generation.

### Side-story / fanfic / sequel mode / 外传同人续作模式

Use when the project depends on another canon. Read `references/canon-side-story.md` and establish:

- parent canon facts
- allowed divergence
- forbidden spoilers
- hook isolation

## File discipline / 文件纪律

When working over many chapters:

- prefer additive updates over destructive rewrites
- never delete hook history without a reason
- mark hooks as `OPEN`, `PAID OFF`, `BROKEN`, `DEFERRED`, or `ADVANCED`
- mark uncertain facts as `UNCONFIRMED`
- separate **world facts** from **character beliefs**

Good pattern:

```md
## Facts
- The seal broke in chapter 17.

## Character beliefs
- Lin Jin believes Xu An caused it.
- Xu An does not know the true source.
```

## Bundled tools / 内置工具入口

推荐优先记住这一个入口：`scripts/novelops_cli.py`。

Common commands:

- `python scripts/novelops_cli.py init ...` — scaffold a new novel project
- `python scripts/novelops_cli.py context ...` — assemble next-chapter context
- `python scripts/novelops_cli.py write-next ...` — build a structured write-next packet
- `python scripts/novelops_cli.py draft ...` — draft the next chapter with an OpenAI-compatible LLM (Hermes-first; supports `--dry-run` / `--mock-response`)
- `python scripts/novelops_cli.py auto-revise ...` — LLM paragraph-level minimal revision (diff by default, `--apply` writes back after snapshot + backup)
- `python scripts/novelops_cli.py audit ...` — run a chapter audit
- `python scripts/novelops_cli.py knowledge-check ...` — detect knowledge-boundary / POV leaks
- `python scripts/novelops_cli.py extract-state ...` — extract candidate state updates
- `python scripts/novelops_cli.py hook-report ...` — summarize hook lifecycle state
- `python scripts/novelops_cli.py state-update ...` — append structured story-state deltas and sync the latest accepted update into `current_state.md`
- `python scripts/novelops_cli.py revision-plan ...` — build revision plan from chapter or audit
- `python scripts/novelops_cli.py spot-fixes ...` — suggest low-risk local fixes
- `python scripts/novelops_cli.py revise ...` — run the revision workflow as one cycle
- `python scripts/novelops_cli.py snapshot ...` — create a state snapshot
- `python scripts/novelops_cli.py diff ...` — diff snapshots or current state
- `python scripts/novelops_cli.py smoke-test` — run smoke tests
- `python scripts/novelops_cli.py package` — create a clean `.skill` package

Advanced / lower-level usage:

- `scripts/init_novel_project.sh`
- `scripts/build_next_chapter_context.py`
- `scripts/build_write_next_packet.py`
- `scripts/draft_chapter.py`
- `scripts/auto_revise.py`
- `scripts/llm_client.py`（LLM 传输层）
- `scripts/novelops_config.py`（项目配置加载）
- `scripts/audit_chapter.py`
- `scripts/knowledge_check.py`
- `scripts/extract_state.py`
- `scripts/hook_report.py`
- `scripts/update_story_state.py`
- `scripts/build_revision_plan.py`
- `scripts/suggest_spot_fixes.py`
- `scripts/run_revision_cycle.py`
- `scripts/snapshot_story_state.py`
- `scripts/diff_story_state.py`
- `scripts/smoke_test.py`
- `scripts/package_skill.py`
- `scripts/smoke_test.sh` (legacy shell entry)
- `scripts/package_skill.sh` (legacy shell entry)

## Use bundled references / 参考文档

Read these only when needed:

- `references/audit-dimensions.md` — audit taxonomy and severity model
- `references/file-schemas.md` — what each truth file should contain
- `references/workflow-playbooks.md` — step-by-step operating playbooks
- `references/worked-examples.md` — concrete end-to-end examples from project setup to chapter progression
- `references/json-schemas.md` — stable JSON output contracts for tooling and automation
- `references/audit-rules.md` — structured rule inventory for the chapter auditor
- `references/revision-workflow.md` — how audit, revision plans, spot fixes, and snapshots fit together
- `references/canon-side-story.md` — how to handle prequels / sequels / alternate lines
- `references/style-learning.md` — how to learn and apply style without overfitting
- `docs/agent-integration.md` — how to wire this skill into a specific host (Claude Code / OpenClaw / IDE-embedded or terminal agents); read it when the user asks how to install or integrate the skill

## Output expectations / 输出期望

When responding in chat, prefer concise operational structure:

- **Plan**
- **Draft / Findings / Proposed fixes**
- **State updates needed**
- **Open questions**

When producing audits, use severity:

- `critical` — breaks logic / continuity / core characterization
- `major` — noticeably weakens chapter or damages setup/payoff
- `minor` — style, clarity, repetition, local pacing
- `note` — optional enhancement

## Design goal / 设计目标

This skill is not a magic novel writer. It is a discipline layer that makes long-form AI writing more stable, inspectable, and maintainable.

