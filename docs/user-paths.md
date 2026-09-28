# 用户路径 / User Paths

这里不讲大而空的理念，只给你三条最常见的上手路径。

## 路径 A：我是第一次看这个仓库 / First-time path

建议顺序：

1. 读 [README](../README.md)
2. 读 [快速上手](getting-started.md)
3. 跑 `python scripts/novelops_cli.py smoke-test`
4. 打开 [examples/demo-novel](../examples/demo-novel/README.md)
5. 按需补看 [CLI 入口](cli.md)

这条路径的目标是：先知道这个仓库能做什么，再看一个最小但完整的小说项目长什么样。

## 路径 B：我想直接做自己的小说项目 / Start your own project

建议顺序：

1. 看 [安装与环境](installation.md)
2. 用 `python scripts/novelops_cli.py init /path/to/project "书名"` 初始化
3. 参考 [project-template.md](project-template.md) 补 truth files
4. 用 `context -> draft -> audit -> extract-state -> state-update` 跑第一章（对应主线 `write-next -> draft -> revise -> ...` 的底层展开，`draft` 由人或 agent 完成）
5. 需要逐脚本调试时，再回到底层脚本路径

这条路径适合已经理解 InkOS 的工作流思路、只是想快速落地的人。

## 路径 C：我想先看一个可讲清流程的 demo / Demo-first path

建议顺序：

1. 打开 [examples/demo-novel](../examples/demo-novel/README.md)
2. 先读 `current_state.md`、`chapter_summaries.md`、`pending_hooks.md`
3. 再读 `chapters/ch01.md` 和 `chapters/ch02.md`
4. 跟着 README 中的命令跑最小链路

这条路径最能说明这个仓库的核心：

- `context` 读取哪些 truth files
- `audit` 会检查什么
- `extract-state` 会提取什么候选项
- `state-update` 最终会把哪些内容写回 truth files

## 你应该什么时候用它

适合：

- 长篇 / 连载 / 网文 / 同人
- 你希望章节写作可持续推进，而不是靠一次性 prompt
- 你需要维护角色认知边界、伏笔状态、章节摘要

不适合：

- 只想一句话生成完整小说
- 不打算维护 truth files
- 不关心章节间连续性

相关文档：

- [安装与环境](installation.md)
- [快速上手](getting-started.md)
- [CLI 入口](cli.md)
- [常见问题](faq.md)

