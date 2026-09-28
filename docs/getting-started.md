# 快速上手 / Getting Started



本文给第一次接触 `NovelOps Skill` 的用户一个最小入口。



> 推荐入口 / Recommended entrypoint：`python scripts/novelops_cli.py ...`


## 这个仓库是什么

它不是“自动写完整小说”的黑盒工具，而是一个**面向智能体应用的长篇小说工作流 skeleton**：

- 用 truth files 保存世界状态
- 用脚本辅助上下文构建、审计、状态更新
- 用 smoke test 和 CI 保持基础可用性

## 第一步：理解核心文件

建议按这个顺序读：

1. `README.md`：看项目定位、能力边界、快速开始
2. `SKILL.md`：看工作流主逻辑
3. `references/`：按需看审计维度、文件结构、示例

## 第二步：初始化一个小说项目 / Initialize a project



```bash

python scripts/novelops_cli.py init /path/to/project "书名"

```

`init` 默认不会写入非空目录，避免误覆盖已有项目；确认覆盖模板文件时再加 `--force`。


初始化后，优先补这些文件：

- `story_bible.md`
- `book_rules.md`
- `outline.md`
- `current_state.md`
- `pending_hooks.md`

## 第三步：跑一个最小工作流 / Run a minimal workflow



```bash

python scripts/novelops_cli.py context --project /path/to/project

```

`context` 之后，先由你（或 agent）依据上下文起草一章正文（draft），保存为 `/path/to/project/chapters/ch01.md`——也可以用 `python scripts/novelops_cli.py draft ...` 交给本地 Hermes 模型自动起草（见 [llm-drafting.md](llm-drafting.md)），然后再对它跑审计：

```bash

python scripts/novelops_cli.py audit --project /path/to/project --chapter-file /path/to/project/chapters/ch01.md

```



如章节涉及悬疑、隐藏真相或严格 POV，可继续：



```bash

python scripts/novelops_cli.py knowledge-check --project /path/to/project --chapter-file /path/to/project/chapters/ch01.md --json

```



你也可以先提取候选状态：



```bash

python scripts/novelops_cli.py extract-state --project /path/to/project --chapter-file /path/to/project/chapters/ch01.md --json

```



接受章节后，再更新状态：



```bash

python scripts/novelops_cli.py state-update --project /path/to/project --chapter 1 --title "第一章" --summary "..."

```

完整推荐主线见 SKILL.md：`init -> write-next -> draft -> revise -> extract-state -> state-update`；本节的 `context` / `audit` 是其中 `write-next` / `revise` 的底层组成命令。



## 第四步：验证仓库基础能力 / Validate the baseline



```bash

python scripts/novelops_cli.py smoke-test

```


这能帮助你确认当前环境下 CLI 与底层脚本链路是否正常。



如果你要看 CLI 与底层脚本如何分工，可继续读 [`docs/cli.md`](cli.md)。


## 协作建议

- 提交前先看 `CONTRIBUTING.md`
- 讨论和反馈请遵守 `CODE_OF_CONDUCT.md`
- 遇到安全问题请参考 `SECURITY.md`

