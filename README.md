# NovelOps Skill

[![CI](https://img.shields.io/github/actions/workflow/status/qiyan233/novelops-skill/ci.yml?branch=main&label=CI)](https://github.com/qiyan233/novelops-skill/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Version](https://img.shields.io/badge/version-v1.1.0-blue)](CHANGELOG.md)

当前版本：**1.1.0**

一个**面向智能体应用**的长篇小说工作流 skill。它把长篇 / 连载 / 网文 / 同人写作
跑成一个**长期可维护的流程**——重点不是“单次写一章”，而是写到第 50 章时设定不崩、状态可回溯。

底层是纯 Python 3 CLI 加纯文本状态文件，不绑定具体宿主：OpenClaw、Claude Code、
IDE 内与终端里的智能体都能驱动它，详见[在不同智能体应用中使用](docs/agent-integration.md)。

灵感参考 **InkOS**：<https://github.com/Narcooo/inkos>。本项目是受其启发的 skill skeleton，
不是原项目的官方移植版。

中文 | [English](README.en.md)

---

## 它解决什么问题

长篇写作真正的难点不是“写不出下一章”，而是**写到第 50 章时还记得谁在第 3 章知道了什么**。
这个仓库把这件事拆成可执行的流程：

- **truth files** 维护世界观、当前局势、角色认知边界
- **`write-next`** 把“下一章该写什么、该避开什么”整理成结构化工作包
- **`draft`** 交给 LLM 起草（Hermes 优先，默认本地 Ollama）
- **`revise` / `auto-revise`** 审计与修订闭环
- **`extract-state` / `state-update`** 把新发生的事实写回状态
- **`snapshot` / `diff`** 随时回退与对比

它不是只负责“写”，而是负责把**多章写作**组织起来。

## 适合谁

适合：

- 想长期、多章、可回溯地写小说，需要维护章节摘要、角色状态、伏笔与当前局势
- 想搭一个类似 InkOS 的小说写作 skill
- 希望写作之外还有审计、修订、状态更新、快照这些环节

不太适合：只想临时生成一篇短文。这个仓库会明显偏重。

## 快速开始

需要 Python 3，无第三方依赖。

```bash
git clone https://github.com/qiyan233/novelops-skill.git
cd novelops-skill

python scripts/novelops_cli.py smoke-test                      # 自检，应输出 Smoke test passed.

python scripts/novelops_cli.py init ./my-novel "我的小说"       # 初始化项目
python scripts/novelops_cli.py write-next --project ./my-novel # 准备下一章
```

> **Windows / 无 bash 环境**请统一使用 `python scripts/novelops_cli.py ...`；
> `scripts/*.sh` 是遗留入口，需要 bash。所有功能都有等价的 Python 命令。

更细的步骤见 [安装与环境](docs/installation.md) 和 [快速上手](docs/getting-started.md)。

## 核心主线

```text
init -> write-next -> draft -> revise -> extract-state -> state-update
```

`draft` 由人或 agent 执笔都可以，也可以直接交给 LLM；`revise` 内部串起
knowledge-check / audit / revision-plan / spot-fixes。命令细节见 [CLI 入口](docs/cli.md)。

## 当前能力

已经能覆盖：

- 下一章准备（`write-next`，含单章契约与场景节拍）
- LLM 写作执行器（`draft`，Hermes 优先，默认本地 Ollama，云端 Nous Portal 可切换）
- 修订闭环（`revise`）与 LLM 段落级自动修订（`auto-revise`，默认只出 diff，`--apply` 前自动快照）
- 知识边界检查（`knowledge-check`，检测角色提前知道不该知道的事）
- 可配置规则引擎（`novelops.config.json` 定制审计词表 / 阈值 / 禁用规则）
- 状态提取与 truth files 更新（`extract-state` / `state-update`）
- 快照、diff 与打包（`snapshot` / `diff` / `package`）
- 基础回归测试（`smoke-test`）

还没做到的：

- 更多完整示例项目
- 多模型对比与自动重试策略
- 更细粒度的风格学习自动化

## 仓库里主要有什么

| 路径 | 用途 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | skill 主说明——这个仓库最核心的文件，智能体的真正使用入口 |
| [`scripts/`](scripts/) | CLI 入口与底层脚本 |
| [`assets/project-template/`](assets/project-template/) | 小说项目模板（`init` 时复制） |
| [`examples/demo-novel/`](examples/demo-novel/) | 完整示例项目 |
| [`docs/`](docs/) | 使用说明 |
| [`references/`](references/) | 规则、结构与 JSON 契约参考 |

## 文档导航

**第一次看这个仓库**，建议按这个顺序：

1. [`SKILL.md`](SKILL.md) —— 先看定位，这里才更接近“skill 真正怎么工作”
2. [`examples/demo-novel/README.md`](examples/demo-novel/README.md) —— 看一个完整例子，
   比先读实现细节直观得多
3. [`docs/cli.md`](docs/cli.md) —— 需要敲命令时再看

**按主题查阅：**

| 文档 | 内容 |
| --- | --- |
| [docs/agent-integration.md](docs/agent-integration.md) | 在各类智能体应用里怎么接入（Claude Code / OpenClaw / IDE / 终端） |
| [docs/installation.md](docs/installation.md) | 安装与最小运行要求 |
| [docs/getting-started.md](docs/getting-started.md) | 从零跑到第一章 |
| [docs/cli.md](docs/cli.md) | 全部命令与参数 |
| [docs/user-paths.md](docs/user-paths.md) | 不同使用场景的路径选择 |
| [docs/project-template.md](docs/project-template.md) | 项目模板里每个文件的作用 |
| [docs/llm-drafting.md](docs/llm-drafting.md) | LLM 起草 / 自动修订的配置与离线通道 |
| [docs/faq.md](docs/faq.md) | 常见问题 |
| [references/json-schemas.md](references/json-schemas.md) | 所有 JSON 输出契约 |
| [references/audit-rules.md](references/audit-rules.md) | 审计规则清单 |
| [references/workflow-playbooks.md](references/workflow-playbooks.md) | 工作流剧本 |

**项目相关：** [CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md) ·
[SECURITY.md](SECURITY.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) ·
[docs/audit-fixes.md](docs/audit-fixes.md)（维护者：审计修复技术日志）

---

本项目是受 [InkOS](https://github.com/Narcooo/inkos) 启发的 skill skeleton，不是官方移植版。
