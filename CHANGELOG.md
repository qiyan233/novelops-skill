# Changelog

这个文件记录 GitHub 上已发布版本的主要变化。

## Unreleased

一轮针对数据安全与检查准确性的修复（尚未发版）。技术细节与逐条根因见 [`docs/audit-fixes.md`](docs/audit-fixes.md)。

### Fixed

- **中文数字章节标题现在能正确识别**：此前只有 `## Chapter 1`、`## 第 1 章` 这类写法生效；用「## 第一章」写 `chapter_summaries.md` 时会连锁出错——下一章号推断错误、上一章 POV 读不到、送给模型的上下文退化成整份文件
- **生成章节时多章输出会被真正拦下**：模型若一次写了两章，此前用「## 第一章夜雨」这种不带空格的标题就能绕过单章检查；现在会拒绝，缺标题时也只会补一个
- **模型爱加的代码围栏和客套话不再进正文**：类似「好的，以下是修订后的段落：」外加 ``` 包裹的返回，现在会先剥离再落盘
- **写文件更安全**：章节正文、状态文件、快照全部改为原子写入，中途失败（进程被杀、磁盘写满、文件被占用）不会留下半截稿件；快照写失败会自动清理，不会污染 `diff --from latest`
- **只改一段不再翻动整个文件**：保留原有换行风格与文件末尾换行，git diff 只显示真正改动的内容
- **打包发布不会带上你的小说**：在仓库内 `init` 出来的项目（正文与 `.novelops-state` 快照）不再被打进 `.skill` 包
- **检查结果更可信**：知识边界检查不再因为「计划」「身份」这类泛词误报；同一句话触发多个问题时报最严重的那个，不再被轻问题盖住
- **长篇节奏检查恢复生效**：单换行分段的中文稿此前永远只算 1 段，段落节奏规则（AUD-104）实际上从未触发过
- 摘要不再只从章节开头挑选；「第1990年」这类写法里的数字不会再被关键词提取丢掉
- `state-update` 的字段内容里带换行，不会再破坏 markdown 文件结构

### Changed

- `auto-revise` 新增 `--force`：审计判定存在 critical 问题时 `--apply` 默认拒绝写入（局部重写修不了结构性问题），确认要继续时加 `--force`
- `auto-revise` 单条问题最多只牵引 2 个段落，避免「突然」这类通用词一次改写半个章节
- 中文引号内的句子不再被从中间切断（「你到底是谁？」此前会被切成两个片段）
- `llm` 配置里把某项显式写成 `null` 不再覆盖默认值

## v1.1.0 — 2026-07-26

### Added

- 新增 `draft` 命令：LLM 章节写作执行器（`scripts/draft_chapter.py`），把 write-next 工作包交给 Hermes 等 OpenAI 兼容模型生成单章草稿；默认接本地 Ollama，Nous Portal 云端改配置即可；支持 `--dry-run` 与 `--mock-response`/`NOVELOPS_LLM_MOCK` 离线通道；空响应/多章输出会被拒绝，缺标题自动补齐
- 新增 `auto-revise` 命令：LLM 段落级最小化自动修订（`scripts/auto_revise.py`）；默认只输出整章 diff，`--apply` 写回前自动 snapshot 并把章节原文备份到 `.novelops-state/backups/<id>/`
- 新增项目级配置 `novelops.config.json`（`scripts/novelops_config.py`，随 `init` 复制、随 snapshot 追踪）：`llm` 节（端点/模型/采样/超时）、`audit` 节（关键词表 extend/replace/disable、逐规则阈值、禁用规则）、`knowledge` 节（token 表、自定义泄漏正则、禁用类型）
- 新增 `scripts/llm_client.py`：纯标准库 OpenAI 兼容 chat completions 传输层，含 Hermes 混合推理 `<think>` 块剥离与清晰的连接/超时/鉴权报错文案
- 新增 JSON 契约：`novelops.config.v1`（输入契约）、`novelops.draft.v1`、`novelops.auto-revise.v1`；新增 `docs/llm-drafting.md`
- `reverse_long_document.py` 支持中文数字章节标题编号（第三章 → 3、第一百零三章 → 103），不再回退顺序编号
- audit / revision-plan / spot-fixes / revise 输出新增 `chapter_file` 字段（与 knowledge-check 字段约定对齐）；`references/json-schemas.md` 补齐 revision-plan / spot-fix-suggestions / state-snapshot / state-diff 四个契约

### Changed

- 共享模块 `scripts/inkos_common.py` 更名为 `scripts/novelops_common.py`（旧名保留为兼容 wrapper）
- 快照目录从 `.inkos-state` 更名为 `.novelops-state`；`diff` 的 `latest` 与快照 ID 解析自动回退兼容旧目录
- audit / knowledge-check 的关键词表与阈值可通过配置覆盖，输出新增 `summary.config`；无配置时行为与 1.0.0 完全一致
- 各文档管线叫法统一：教学简化线（`context -> draft -> audit -> ...`）与主线（`init -> write-next -> draft -> revise -> extract-state -> state-update`）的映射在 demo README / cli.md / getting-started.md / user-paths.md 中显式说明

### Fixed

- `iso_now()` 弃用 `datetime.utcnow()`，改为 timezone-aware 写法（输出格式不变）
- `revision-plan` / `spot-fixes` 对缺 `project`/`chapter` 键的手工 audit JSON 增加 `--write-report` 防护与读取兜底，不再抛 `Path(None)` TypeError
- demo 示例修正：第一章标题与正文统一为「库房异响」；`style_profile.json` 按模板 schema 重写；`style_guide.md` 按模板五节重组
- `smoke_test.sh` 章节标题兼容性用例残留的「第3章」摘要污染 write-next 下一章推断的问题（该失败因 CI 只执行 Python 版 smoke test 而长期未暴露）
- CHANGELOG 的文件用途说明句从文件中部移回顶部

### Assets

- `novelops-skill-v1.1.0.skill`

## v1.0.0 — 2026-06-12

### Changed

- 项目用户侧名称改为 **NovelOps Skill**，skill 标识与打包名改为 `novelops-skill`
- 推荐 CLI 入口从 `scripts/inkos_cli.py` 更名为 `scripts/novelops_cli.py`，旧入口保留为兼容 wrapper
- JSON schema namespace 从 `inkos.*` 调整为 `novelops.*`

### Fixed

- `init` 默认拒绝写入非空目录，避免误覆盖已有小说项目；确认覆盖时需显式使用 `--force`

### Assets

- `novelops-skill-v1.0.0.skill`

## v0.5.1 — 2026-04-13

### Added

- 新增 `scripts/reverse_long_document.py`，提供长文档拆解 MVP：章节索引、按章节分块、chunk 级拆解、汇总输出
- `scripts/inkos_cli.py` 新增 `reverse-longdoc` 入口

### Changed

- `build_next_chapter_context.py` 现在支持显式目标章节与更强的单章输出约束
- `build_write_next_packet.py` 现在补充 `single_chapter_contract`、`chapter_file_hint`、`plan_template`
- 活跃文档与 skill 示例中的 `python3` 已统一收口为更兼容 Windows 的 `python`
- `README.md` 已进一步简化为更偏人类阅读的项目概览，而不是命令手册

### Fixed

- 修复单章起草时上下文把后续多章一并带入，导致一次生成多个章节内容的问题
- 修复 Windows / GBK 环境下部分子进程输出解码不稳定的问题
- 修复 `python3` 在 Windows 环境下常见不可用带来的使用门槛

### Notes

- 这是一个以 issue 收口为重点的 follow-up release
- 当前 open issues 已清空，长文档拆解需求已完成首个可运行版本

### Assets

- `inkos-like-novel-os-v0.5.1.skill`

## v0.5.0 — 2026-04-05

### Added

- 新增 `scripts/build_write_next_packet.py`，用于把下一章写作准备整理成结构化 `write-next` packet
- 新增 `scripts/run_revision_cycle.py`，用于统一输出 knowledge-check、audit、revision plan 与 spot-fix 建议
- `scripts/inkos_cli.py` 新增 `write-next` / `revise` 工作流级命令

### Changed

- 仓库定位从“统一脚本入口”进一步升级为更可运行的 workflow 层
- `README.md`、`docs/cli.md`、`references/json-schemas.md` 开始以 `write-next / revise` 作为 0.5.0 的主要升级点
- `smoke_test.py` / `smoke_test.sh` 现在覆盖 `write-next / revise`
- `VERSION` 与 `SKILL.md` 已同步更新为 `0.5.0`

### Notes

- 这是一个以完整工作流入口为重点的功能版本，不再只是维护性小修
- 当前推荐主线：`write-next -> draft -> revise -> extract-state -> state-update`

### Assets

- `inkos-like-novel-os-v0.5.0.skill`

## v0.4.3 — 2026-04-04

### Added

- 新增 `scripts/smoke_test.py`，提供跨平台的 Python 回归入口，覆盖 `init → context → audit → state-update → package → smoke-test` 主链路
- 新增 `scripts/package_skill.py`，提供跨平台的 `.skill` 打包入口，并支持基于 `VERSION` 自动输出带版本号的产物
- 新增 `AGENTS.md`，记录本轮协作中补充的版本同步规则

### Changed

- `scripts/inkos_cli.py` 现在对 `init`、`package`、`smoke-test` 优先走 Python 路径，减少对 Bash 环境的依赖
- `scripts/update_story_state.py` 现在会在写入章节摘要的同时同步维护 `current_state.md`，记录最新接受章节位置与 compact accepted-update 区块
- `SKILL.md` 与 `README.md` 同步更新为 Python / CLI-first 入口叙事，并补充 `current_state.md` 新同步行为说明
- `VERSION` 已更新为 `0.4.3`

### Fixed

- 修复 Windows 环境下 `python scripts/inkos_cli.py init ...` 因缺少 `bash` 而直接失败的问题
- 修复 Windows 环境下 `python scripts/inkos_cli.py smoke-test` 无法启动 shell 回归脚本的问题
- 修复 Windows 环境下 `python scripts/inkos_cli.py package ...` 无法打包 `.skill` 的问题
- 修复 `state-update` 未将最新接受章节同步回 `current_state.md`，导致状态源逐渐分叉的问题

### Notes

- 这是一个以跨平台 CLI 可用性、skill 主契约一致性和状态同步完整性为重点的维护版本
- 当前推荐入口仍然是 `python3 scripts/inkos_cli.py ...`；shell 脚本入口保留为兼容路径

### Assets

- `inkos-like-novel-os-v0.4.3.skill`

## v0.4.2 — 2026-03-29

### Changed

- 进一步统一仓库入口叙事，明确以 `python3 scripts/inkos_cli.py ...` 作为推荐主入口
- README、docs、examples、`SKILL.md` 与关键 `references/` 文档现在都优先展示 CLI 工作流
- 新增 `docs/cli.md`，补充 CLI Quickstart 与 CLI / 底层脚本的使用边界说明

### Fixed

- 修复 `scripts/inkos_cli.py smoke-test` 调用链，使 CLI 入口可以正确传递 Python 解释器环境给 smoke test
- 修复 `snapshot_story_state.py` 中已弃用的 UTC 时间写法，消除 `datetime.utcnow()` deprecation warning
- 修正文档中的部分版本链接与入口表述不一致问题

### Notes

- 这是一个以入口一致性和使用体验为重点的维护版本
- 当前推荐工作流：先走 CLI，底层脚本作为 advanced / lower-level usage

### Assets

- `inkos-like-novel-os-v0.4.2.skill`

## v0.4.1 — 2026-03-28

### Added

- 新增最小 `docs/` 上手文档结构：`getting-started`、`installation`、`user-paths`、`project-template`、`faq`
- 新增 `examples/demo-novel/` 示例项目，包含 truth files 与两章演示内容，方便快速理解 `context / audit / extract-state / state-update` 的协作方式
- README 顶部新增 CI / License / Version 徽章，并补充 docs / example 导航入口
- 新增开源协作基础文件：`LICENSE`、`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`
- 新增 GitHub 协作模板与最小 CI 工作流

### Fixed

- 修复 `scripts/smoke_test.sh` 在 Windows / Git Bash 风格环境中的 Python 入口兼容问题
- 修复 smoke test 对中文 JSON 输出的脆弱匹配方式，改为更稳的 UTF-8 / Python 断言路径

### Notes

- 这是一个小版本维护发布，重点是提升开源协作体验、首次上手路径和环境兼容性

### Assets

- `inkos-like-novel-os-v0.4.1.skill`

## v0.4.0 — 2026-03-18

### Added

- 新增 `knowledge_check.py`，用于检测人物认知边界、POV 泄露、以及“角色提前知道真相”类问题
- 新增 `hook_report.py`，用于统计 hook 生命周期状态并标记 stale hooks
- 新增 `extract_state.py`，用于从章节正文中提取候选状态更新，默认只输出候选、不直接写盘
- `inkos_cli.py` 新增 `knowledge-check`、`hook-report`、`extract-state` 子命令
- 模板新增 `character_knowledge.md`，并补强 `pending_hooks.md` / `chapter_summaries.md` 结构

### Changed

- `build_next_chapter_context.py` 现在支持自动加载 `character_knowledge.md`
- `SKILL.md` 工作流升级为“knowledge-check → audit → extract-state → state-update”闭环
- `references/file-schemas.md`、`references/json-schemas.md`、`references/workflow-playbooks.md` 同步扩展新能力说明
- `smoke_test.sh` 新增对 knowledge-check / hook-report / extract-state 的回归覆盖

### Assets

- `inkos-like-novel-os-v0.4.0.skill`

## v0.3.4 — 2026-03-17

### Fixed

- 修复 `init_novel_project.sh` 在书名包含 `&`、`/`、反斜杠等字符时的占位符替换问题
- 修复 `build_next_chapter_context.py` 的边界行为：
  - 极小 `--max-chars-per-file` 下截断结果可能超长
  - `--recent-chapters 0` 之前会错误返回全部章节
  - 负数参数现在会明确报错
  - 中英文章节标题提取更一致
- 修复 `update_story_state.py` 的 `updated_files`，现在只返回实际写入的文件
- 修复 `audit_chapter.py` 在 chapter 文件缺失时的误导性“空章节”结果
- 修复 `build_next_chapter_context.py`、`update_story_state.py`、`snapshot_story_state.py`、`diff_story_state.py` 在 project 路径不存在或未初始化时的误导性成功返回

### Quality

- `inkos_cli.py` 同步增加 context 参数校验，避免 CLI 与底层脚本行为不一致
- `package_skill.sh` 支持从 `VERSION` 自动生成带版本号的 `.skill` 副本
- 补充 smoke test 回归覆盖：特殊书名转义、极小 `max-chars`、`recent-chapters=0`、负数参数、缺失 project / chapter、snapshot/diff 回归

### Assets

- `inkos-like-novel-os-v0.3.4.skill`

## Earlier GitHub releases

- [v0.3.1](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.3.1)
- [v0.3.0](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.3.0)
- [v0.2.0](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.2.0)
- [v0.1.3](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.1.3)
- [v0.1.2](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.1.2)
- [v0.1.1](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.1.1)
- [v0.1.0](https://github.com/qiyan233/inkos-like-novel-os/releases/tag/v0.1.0)
