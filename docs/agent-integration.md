# 在不同智能体应用中使用 / Agent integration

NovelOps 面向智能体应用，但不绑定具体宿主。它底层只有两样东西：

- **纯 Python 3 CLI**（`scripts/novelops_cli.py`），只用标准库，无第三方依赖
- **纯文本状态文件**（Markdown / JSON），存放在小说项目目录里，可用任何编辑器打开

因此只要一个 agent 能**读写文件**并**执行命令**，就能驱动整套流程。
其中 [`SKILL.md`](../SKILL.md) 是给 agent 读的指令，`references/` 是它按需查阅的规则与契约，
`docs/` 是给人看的说明。

## 支持矩阵

| 智能体应用 | 接入方式 | 说明 |
| --- | --- | --- |
| Claude Code / 任何支持 Agent Skills 的应用 | 把仓库放进 skills 目录 | `SKILL.md` 的 YAML frontmatter 已是标准格式，智能体可自动发现 |
| OpenClaw | `.skill` 发布包 | 从 Releases 获取，或用 `package` 自行打包 |
| IDE 内智能体（Cursor / Windsurf / Cline 等） | 让它读 `SKILL.md` | 这类应用没有统一的 skill 格式，把 `SKILL.md` 当作规则/指令文件即可 |
| 终端智能体（Codex、Gemini CLI 等） | 指向 `SKILL.md` + 命令行 | 同上 |
| 不使用智能体 | 直接用 CLI | 所有功能都可手工执行，没有只对智能体开放的路径 |

## Claude Code / Agent Skills

本仓库的 `SKILL.md` 顶部就是标准的 frontmatter：

```yaml
---
name: novelops-skill
description: Novel-production operating system skill for long-form fiction, ...
---
```

只要它位于某个 skill 目录的根部即可被识别。用发布包安装：

```bash
# 用户级（所有项目可用）
unzip novelops-skill.skill -d ~/.claude/skills/

# 或项目级（只在该项目可用）
unzip novelops-skill.skill -d .claude/skills/
```

> `.skill` 包本质是 zip。若你的解压工具不认这个扩展名，改名为 `.zip` 再解压。
> 解压后应得到 `<skills 目录>/novelops-skill/SKILL.md`。

也可以直接把 clone 下来的仓库放进 skills 目录，或用符号链接指向它——改脚本后立即生效，
适合边改边用。

## OpenClaw

从 Releases 下载 `.skill` 包安装，或在仓库内自行打包：

```bash
python scripts/novelops_cli.py package
```

## 其他智能体应用

这些应用没有统一的 skill 装载约定，接入方式一样：

1. 把仓库放到智能体能访问的位置
2. 让它先读 [`SKILL.md`](../SKILL.md)——那是完整的工作流指令
3. 按需读 [`references/`](../references/) 里的规则与契约
4. 通过 `python scripts/novelops_cli.py <command>` 执行
5. 小说项目的状态文件让它直接用文件读写修改即可

如果应用支持自定义指令文件（`.cursorrules`、`AGENTS.md`、系统提示词等），
在里面写一句「本仓库是一个小说工作流 skill，先读 `SKILL.md`」通常就够了。

## 最小接口要求

一个智能体应用只要能做这两件事，就能完整使用本 skill：

| 能力 | 用途 |
| --- | --- |
| 读 / 写文件 | 维护 truth files、章节正文、`novelops.config.json` |
| 执行命令 | 跑 `python scripts/novelops_cli.py ...` |

**不需要**：网络访问（LLM 起草功能除外，且可选）、数据库、特定运行时、特定宿主 API。

## 让 `draft` / `auto-revise` 工作

这两个命令要调用 LLM，走 OpenAI 兼容接口，与智能体应用无关：

- 默认连本地 Ollama（`http://localhost:11434/v1`）
- 云端服务改 `novelops.config.json` 的 `llm.base_url` 与 `api_key_env`
- 离线调试用 `--dry-run`（只出请求体）或 `--mock-response`（用文件充当模型响应）

配置细节见 [LLM 起草与自动修订](llm-drafting.md)。
如果你用的 agent 自己就能写文本，也完全可以跳过这两个命令，由 agent 或人来执笔。

## 相关文档

- [安装与环境](installation.md)
- [快速上手](getting-started.md)
- [CLI 入口](cli.md)
- [用户路径](user-paths.md)
