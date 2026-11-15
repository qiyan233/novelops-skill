# Revision Workflow

> CLI-first / CLI 优先：推荐优先使用 `python scripts/novelops_cli.py ...` 组织审计、修订计划和 spot-fix 流程。

这一层工作流解决的不是“怎么生成一章”，而是“写完之后如何稳地修”。

## 推荐顺序

1. 跑审计：`audit_chapter.py`
2. 产出修订计划：`build_revision_plan.py`
3. 生成低风险 spot-fix 建议：`suggest_spot_fixes.py`
4. 若章节接受，更新 truth files
5. 在关键节点做状态快照：`snapshot_story_state.py`
6. 如有争议，比较快照差异：`diff_story_state.py`

## 角色分工

### 审计器
负责发现问题，不负责改正文。

### 修订计划器
负责决定：
- 是 spot-fix 还是 scene-level rewrite
- 哪些问题必须先修
- 哪些问题需要人类确认

### Spot-fix 建议器
只做低风险、局部性的改动建议，不碰高风险剧情判断。

### 状态快照器
负责在章节接受或重大调整前后留下 truth files 的可回溯版本。

快照存放在 `<project>/.novelops-state/snapshots/` 下；旧项目遗留在 `.inkos-state/` 中的历史快照仍可被 `diff_story_state.py` 读取（`latest` 与快照 ID 解析都会自动回退到旧目录）。

### 复检
`auto-revise` 改写后会用同一套审计复检修订稿，输出 `verification`：`verdict`（`improved` / `unchanged` / `regressed`）、`resolved_rules` 与 `introduced_rules`。`regressed` 或出现 `introduced_rules` 时应回退这次改写，而不是直接接受 diff——局部重写很容易修掉一处重复、又改出新的节奏问题。

`verification` 只看自动规则；`audit` 报告里的 `human_only_dimensions` 仍需人工过一遍。

## 核心原则

- 先定修订策略，再动正文
- 优先修 high-severity 问题
- 优先局部修，不轻易整章推倒
- 每次接受关键章节后都值得做 snapshot

