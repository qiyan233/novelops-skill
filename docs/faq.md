# FAQ / 常见问题

## 这是自动写小说的黑盒吗？

不是。

它更像一个面向智能体应用的长篇小说工作流 skeleton：用 truth files、审计脚本和状态更新，把多章写作变成可维护流程。只要智能体能读写文件、执行命令就能驱动它。

## 它和 InkOS 是什么关系？

本项目受 InkOS 启发，但不是原项目官方移植版。定位是一个不绑定具体 agent 应用、可长期继续改造的 skill skeleton。

## 我一定要维护所有 truth files 吗？

不一定。

但至少建议认真维护：

- `current_state.md`
- `chapter_summaries.md`
- `pending_hooks.md`

如果是悬疑、宫斗、权谋、严格 POV，建议再维护：

- `character_knowledge.md`
- `character_matrix.md`

## extract-state 会直接改文件吗？

不会。

`python scripts/novelops_cli.py extract-state ...` 默认只输出候选结果，方便你人工确认；真正写回 truth files 的是 `python scripts/novelops_cli.py state-update ...`（底层分别对应 `extract_state.py` 与 `update_story_state.py`）。

## 这个仓库适合拿来做什么？

适合：

- 小说写作 skill 原型
- NovelOps Skill 长篇工作流底座
- 连载 / 网文 / 同人 / 正典衍生项目
- 需要多章一致性和可追踪状态的写作流程

## 我该先看哪个文档？ / Where should I start?

第一次上手：

1. [README](../README.md)
2. [快速上手](getting-started.md)
3. [CLI 入口](cli.md)
4. [用户路径](user-paths.md)
5. [demo-novel 示例](../examples/demo-novel/README.md)

## 为什么还要 examples/demo-novel？

因为很多人能看懂脚本，却看不出“这些 truth files 实际怎么协同工作”。

`examples/demo-novel` 的价值在于：给出一个可以被脚本读取、又能说明 `context / audit / extract-state / state-update` 的最小完整项目。

