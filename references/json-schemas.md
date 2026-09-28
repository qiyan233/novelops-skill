# JSON Schemas

## CLI-first note / CLI 优先说明

这些 JSON 契约既可由底层脚本直接输出，也可通过 `python scripts/novelops_cli.py ... --json` 统一获取。对普通使用者，推荐优先走 CLI。

这些不是 JSON Schema draft 文件，而是当前脚本输出的稳定 JSON 契约说明。

## 1. `novelops.audit-report.v1`

来源：`scripts/audit_chapter.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`（因历史原因为章节文件路径字符串，语义保持不变）
- `chapter_file`（与 `chapter` 同值的章节文件路径，用于与 knowledge-check 的字段约定对齐）
- `overall`
- `summary`
- `source_files`
- `chapter_metrics`
- `findings[]`
- `minimal_fix_plan[]`
- `report_path`（仅 `--write-report` 时出现）

### `findings[]`
每条 finding 包含：
- `rule_id`
- `severity`
- `dimension`
- `message`
- `evidence[]`
- `repair_targets[]`

### `summary.config`
记录本次审计实际生效的项目配置（见第 14 节 `novelops.config.v1`）：
- `config_file`（`novelops.config.json` 的路径；未配置时为 `null`）
- `keyword_tables_overridden`（`{表名: extend|replace|disable}`）
- `thresholds_overridden[]`（被覆盖阈值的规则 id 列表）
- `rules_disabled[]`

注意：配置生效时 `summary.rules_evaluated` 与 `chapter_metrics.time_jump_markers` 会随配置变化；无配置时行为与 1.0.0 完全一致。

## 2. `novelops.next-context.v1`

来源：`scripts/build_next_chapter_context.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `config`
- `files_loaded[]`
- `summary`
- `section_meta`
- `sections`
- `context`

## 3. `novelops.state-update.v1`

来源：`scripts/update_story_state.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`
- `title`
- `summary`
- `operations`
- `updated_files[]`
- `report_path`（仅 `--write-report` 时出现）

## 4. `novelops.knowledge-check.v1`

来源：`scripts/knowledge_check.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`
- `chapter_file`
- `ok`
- `summary`
- `source_files[]`
- `violations[]`

### `summary`
- `violation_count`
- `counts`（`critical` / `major` / `minor` / `note`）
- `beliefs_loaded`（成功解析的 character-belief 条数）
- `malformed_beliefs[]`（`## Character beliefs` 下缺少「角色：事实」分隔符的行；这些行无法参与判定，列出来提示用户修数据）
- `config`

### `violations[]`
每条 violation 包含：
- `severity`
- `type`
- `character`
- `fact`
- `evidence`
- `reason`
- `suggested_fix`

### `summary.config`
记录本次检查实际生效的项目配置（见第 14 节 `novelops.config.v1`）：
- `config_file`（未配置时为 `null`）
- `keyword_tables_overridden`
- `leak_patterns_source`（`default` / `extend` / `replace` / `disable`）
- `kinds_disabled[]`

## 5. `novelops.hook-report.v1`

来源：`scripts/hook_report.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `config`
- `summary`
- `hooks[]`
- `stale_hooks[]`

## 6. `novelops.extract-state.v1`

来源：`scripts/extract_state.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`
- `chapter_file`
- `title_guess`
- `summary`
- `state_changes[]`
- `hook_open[]`
- `hook_advance[]`
- `hook_close[]`
- `relationships[]`
- `emotions[]`
- `write_mode`

## 7. `novelops.write-next.v1`

来源：`scripts/build_write_next_packet.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`
- `chapter_file_hint`
- `files_loaded[]`
- `chapter_function`
- `required_inputs`
- `single_chapter_contract[]`
- `suggested_scene_beats[]`
- `plan_template`
- `context_packet`
- `next_actions[]`
- `report_path`（仅 `--write-report` 时出现）

### `chapter_function`
- `primary_goal`
- `pressure[]`
- `planned_payoff_or_partial_payoff`

### `required_inputs`
- `suggested_pov`
- `active_hooks[]`
- `open_conflicts[]`
- `constraints[]`
- `state_targets[]`

## 8. `novelops.revision-cycle.v1`

来源：`scripts/run_revision_cycle.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`（章节文件路径字符串）
- `chapter_file`（与 `chapter` 同值）
- `status`
- `summary`
- `recommended_sequence[]`
- `hook_pressure`
- `knowledge_check`
- `audit`
- `revision_plan`
- `spot_fixes`
- `report_path`（仅 `--write-report` 时出现）

### `summary`
- `knowledge_check_run`
- `blocking_item_count`
- `audit_overall`
- `spot_fix_count`
- `human_review_needed`
- `stale_hook_count`

## 9. `novelops.longdoc-reverse.v1`

来源：`scripts/reverse_long_document.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `source`
- `workspace`
- `summary`
- `outputs`

### `summary`
- `total_chapters`
- `chunk_file_count`
- `analysis_file_count`

### `outputs`
- `index`
- `chunks_dir`
- `chunk_analysis_dir`
- `summary_json`
- `summary_md`

## 10. `novelops.revision-plan.v1`

来源：`scripts/build_revision_plan.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`（沿用 audit 报告中的章节文件路径）
- `chapter_file`（优先取 audit 报告的 `chapter_file`，缺失时回退 `chapter`）
- `based_on`
- `overall_strategy`
- `summary`
- `source_files[]`
- `minimal_fix_plan[]`
- `actions[]`
- `report_path`（仅 `--write-report` 时出现）

### `based_on`
- `schema_version`
- `overall`

### `overall_strategy`
- `mode`（`block-and-patch` / `targeted-scene-rewrite` / `targeted-rewrite` / `spot-fix-pass` / `light-pass-or-accept`）
- `reason`

### `summary`
- `action_count`
- `human_review_needed`
- `counts`

### `actions[]`
每条 action 包含：
- `action_id`（`REV-001` 起）
- `priority`
- `rule_id`
- `dimension`
- `target_scope`
- `needs_human_review`
- `goal`
- `recommended_strategy`
- `repair_targets[]`
- `evidence[]`

## 11. `novelops.spot-fix-suggestions.v1`

来源：`scripts/suggest_spot_fixes.py --json`

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `chapter`（沿用 audit 报告中的章节文件路径）
- `chapter_file`（优先取 audit 报告的 `chapter_file`，缺失时回退 `chapter`）
- `based_on`
- `summary`
- `suggestions[]`
- `report_path`（仅 `--write-report` 时出现）

### `summary`
- `suggestion_count`
- `local_dimensions[]`

### `suggestions[]`
每条 suggestion 包含：
- `suggestion_id`（`FIX-001` 起）
- `rule_id`
- `severity`
- `dimension`
- `snippet`
- `suggested_action`
- `repair_targets[]`
- `confidence`

## 12. `novelops.state-snapshot.v1`

来源：`scripts/snapshot_story_state.py --json`

快照写入 `<project>/.novelops-state/snapshots/<snapshot_id>/`，并在 `<project>/.novelops-state/index.jsonl` 追加一行索引。

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `snapshot_id`
- `snapshot_dir`
- `label`
- `chapter`
- `notes`
- `files_copied[]`
- `files_missing[]`

### `files_copied[]`
每条包含：
- `path`
- `bytes`
- `sha1`

## 13. `novelops.state-diff.v1`

来源：`scripts/diff_story_state.py --json`

`latest` 与裸快照 ID 的解析会优先查 `.novelops-state/snapshots/`，查不到时回退兼容旧的 `.inkos-state/snapshots/`。

核心字段：
- `schema_version`
- `tool`
- `generated_at`
- `project`
- `from`
- `to`
- `summary`
- `file_diffs[]`

### `from` / `to`
- `kind`（`current` / `snapshot`）
- `id`
- `path`

### `summary`
- `changed_files`
- `added_lines`
- `removed_lines`

### `file_diffs[]`
每条包含：
- `path`
- `status`（`added` / `removed` / `changed`）
- `present`（`{from, to}`：两侧文件是否实际存在；用于区分「文件被删除」与「文件本就是空的」）
- `added_lines`
- `removed_lines`
- `diff_excerpt[]`（unified diff 片段，最多 80 行）

## 14. `novelops.config.v1`

来源：项目根的 `novelops.config.json`（**输入契约**——这是本清单中唯一由用户书写、被脚本读取的契约；`init` 会从模板复制一份默认配置）。

三个节均可省略；省略或留空（`{}`）时一切走默认，行为与未配置完全一致。

### `llm` 节
- `provider`（标签，仅记录用；默认 `ollama`）
- `base_url`（默认 `http://localhost:11434/v1`；Nous Portal 云端填 `https://inference-api.nousresearch.com/v1`）
- `model`（默认 `hermes4`）
- `api_key`（明文 key，不推荐入库）/ `api_key_env`（环境变量名，默认 `NOVELOPS_LLM_API_KEY`，优先于 `api_key`）
- `temperature`（默认 0.6）/ `top_p`（默认 0.95）/ `max_tokens`（默认 4096）
- `timeout_seconds`（默认 300）
- `strip_think`（默认 `true`，剥离 Hermes 混合推理的 `<think>` 块）

### `audit` 节
- `keywords`：`{表名: {"mode": "extend"|"replace"|"disable", "items": [...]}}`；`mode` 缺省为 `extend`（默认表在前去重追加），`replace` 只用 `items`，`disable` 清空该表。可用表名即 `audit_chapter.py` 的 `DEFAULT_KEYWORD_TABLES`（`TRANSITIONS` / `REPORT_SPEAK` / `CROWD_CLICHES` / `TIME_JUMPS` / `TELLING_PHRASES` / `KNOWLEDGE_LEAPS` / `PROTAGONIST_LOCK_BREAKS` / `STATE_TURN_MARKERS` / `AUD110_LEAK_TRIGGERS`）
- `thresholds`：`{规则id: {阈值键: 值}}` 逐规则浅覆盖，只写要改的键；可用键见 `DEFAULT_THRESHOLDS`
- `rules_disabled[]`：禁用的规则 id（`AUD-101` ~ `AUD-114`；`AUD-000` 空章守卫不可禁用）

### `knowledge` 节
- `keywords`：同上语义，表名为 `BELIEF_NEGATION_TOKENS` / `BELIEF_SUSPICION_TOKENS` / `FACT_CONFIDENCE_TOKENS`
- `leak_patterns`：`{"mode": ..., "items": [{"kind": ..., "pattern": <正则>}]}`；`kind` 限 `knowledge-leak` / `premature-certainty` / `omniscient-leak`
- `kinds_disabled[]`：禁用的泄漏类型（禁用 `knowledge-leak` 同时会关闭 belief 路径的检查）

未知表名 / 规则 id / 阈值键 / kind / 顶层键一律直接报错退出，不静默忽略。

## 15. `novelops.draft.v1`

来源：`scripts/draft_chapter.py --json`（CLI：`draft`）

核心字段：
- `schema_version` / `tool` / `generated_at` / `project`
- `chapter`（int）
- `chapter_file`（目标落盘路径）
- `mode`（`dry-run` / `mock` / `live`）
- `llm`（`provider` / `base_url` / `model` / `temperature` / `top_p` / `max_tokens` / `api_key`（恒为 `null`，永不携带明文）/ `api_key_present` / `api_key_source`）
- `request`（dry-run 时为 `{payload}` 完整请求体；否则为 `{message_count, system_chars, user_chars}`）
- `response`（dry-run 时为 `null`；否则含 `raw_chars` / `content_chars` / `think_stripped` / `usage` / `model`）
- `validation`（`heading_count` / `heading_added` / `sanitized` / `warnings[]`）
  - `sanitized`：模型输出被剥掉代码围栏或开场白（如「好的，以下是…：」）时为 `true`
- `write`（`written` / `chapter_file` / `forced`）
- `next_actions[]`
- `report_path`（仅 `--write-report` 时出现）

## 16. `novelops.auto-revise.v1`

来源：`scripts/auto_revise.py --json`（CLI：`auto-revise`）

核心字段：
- `schema_version` / `tool` / `generated_at` / `project`
- `chapter_file` / `chapter`（解析失败时为 `null`）
- `mode`（`dry-run` / `diff` / `apply`）
- `llm`（同 draft.v1 的 `llm` 节，另含实际 `transport`）
- `based_on`（`revision_cycle_status` / `audit_overall`）
- `summary`（`local_finding_count` / `paragraphs_targeted` / `paragraphs_rewritten` / `paragraphs_skipped` / `applied`）
- `targets[]`
- `skipped_findings[]`（`rule_id` / `dimension` / `reason`：`no-evidence-anchor` / `evidence-not-found` / `evidence-too-broad` / `over-paragraph-budget`）
  - `evidence-too-broad`：evidence 是「突然」这类通用词，命中的段落数超过单条 finding 的预算（2 段），已按靠前的段落截取
- `diff[]`（整章 unified diff，最多 400 行）/ `diff_truncated`
- `snapshot`（仅 `--apply` 且有改动时：`snapshot_id` / `snapshot_dir` / `chapter_backup`；否则 `null`）
- `report_path`（仅 `--write-report` 时出现）

### `targets[]`
每条 target 包含：
- `paragraph_index`
- `findings[]`（`rule_id` / `dimension` / `severity` / `evidence[]`）
- `original` / `revised`（未重写时为 `null`）
- `status`（`rewritten` / `unchanged` / `skipped`）
- `skip_reason`（`empty-rewrite` / `rewrite-contains-heading` / `rewrite-out-of-bounds` 等）
- `payload`（仅 dry-run：该段的完整 chat 请求体）

## 稳定性原则

- 先新增字段，再考虑移除字段
- `schema_version` 升级时，尽量保留旧字段语义
- CLI 与后续自动修订脚本应优先依赖这些 JSON 输出，而不是解析 Markdown 文本

