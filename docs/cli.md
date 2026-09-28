# CLI 入口 / CLI Entrypoint

`python scripts/novelops_cli.py ...` 是这个仓库当前推荐的**统一主入口 / unified entrypoint**。

旧入口 `python scripts/inkos_cli.py ...` 仍作为兼容 wrapper 保留，但新文档和示例统一使用 `novelops_cli.py`。

它不会改变底层脚本的职责，而是把常见工作流命令集中到一个地方，方便你在 README、docs、demo 和日常使用里走同一条路径。

从 `0.5.0` 开始，CLI 也开始提供更完整的**工作流级入口**：

- `write-next`：把下一章写作准备整理成结构化 packet
- `revise`：把 `knowledge-check + audit + revision-plan + spot-fixes` 串成单次修订闭环

## 什么时候优先用 CLI / When to prefer CLI

优先用 CLI：

- 你是第一次上手这个仓库
- 你想跑完整工作流，而不是记住很多脚本名
- 你希望 README / docs / demo 用一致命令
- 你想把 `init -> context -> audit -> extract-state -> state-update -> smoke-test` 作为主线

> 说明：上面是按底层命令展开的教学主线。日常推荐主线是 `init -> write-next -> draft -> revise -> extract-state -> state-update`（见 SKILL.md / README）；其中 `context` 是 `write-next` 的组成部分，`audit` 是 `revise` 的组成环节，`draft` 由人或 agent 完成。

## 什么时候直接调底层脚本 / When to call scripts directly

直接调底层脚本更合适：

- 你在调试某个单独脚本
- 你在 shell / CI / 外部工具里只复用一个能力
- 你需要更明确地区分 Bash 脚本和 Python 脚本

## 常用命令 / Common commands

### 初始化项目 / Initialize

```bash
python scripts/novelops_cli.py init /path/to/project "书名"
```

安全规则：`init` 默认只允许写入不存在或空目录；如果目标目录已经非空，会拒绝执行。确认要覆盖模板文件时，显式使用：

```bash
python scripts/novelops_cli.py init /path/to/project "书名" --force
```

### 生成上下文 / Build context

```bash
python scripts/novelops_cli.py context --project /path/to/project
```

### 生成下一章工作包 / Build write-next packet

```bash
python scripts/novelops_cli.py write-next --project /path/to/project --json
```

这个命令会在 `context` 的基础上补齐：

- 目标章节编号
- 建议章节文件路径
- chapter function
- active hooks / constraints / state targets
- suggested scene beats
- 可直接复用的 `plan_template`
- 单章输出约束（避免一口气写出多个章节）

如果你想把结果落到 `reviews/` 里供后续自动化或人工 review 使用：

```bash
python scripts/novelops_cli.py write-next --project /path/to/project --json --write-report
```

### 审计章节 / Audit chapter

```bash
python scripts/novelops_cli.py audit \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch01.md
```

### 提取候选状态 / Extract candidate state

```bash
python scripts/novelops_cli.py extract-state \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch01.md \
  --json
```

### 更新 truth files / Update truth files

```bash
python scripts/novelops_cli.py state-update \
  --project /path/to/project \
  --chapter 1 \
  --title "第一章" \
  --summary "..."
```

### 跑修订闭环 / Run revision cycle

```bash
python scripts/novelops_cli.py revise \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch01.md \
  --json
```

这个命令会统一输出：

- knowledge-check 结果
- audit 报告
- revision plan
- spot-fix suggestions
- hook pressure / stale hooks 概览

如果你要把完整修订闭环结果存档到 `reviews/`：

```bash
python scripts/novelops_cli.py revise \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch01.md \
  --json \
  --write-report
```

### LLM 起草章节 / Draft with an LLM

```bash
python scripts/novelops_cli.py draft \
  --project /path/to/project \
  --chapter 3 \
  --json
```

把 write-next 工作包交给 OpenAI 兼容模型（默认本地 Ollama 上的 Hermes）生成单章草稿并写入 `chapters/ch03.md`。已存在的章节需要 `--force` 才会覆盖。

离线调试：

```bash
# 只输出请求 payload，不联网
python scripts/novelops_cli.py draft --project /path/to/project --chapter 3 --dry-run --json

# 用文件内容充当模型响应，走完整校验与落盘链路
python scripts/novelops_cli.py draft --project /path/to/project --chapter 3 --mock-response mock.txt --json
```

接入方式与排错见 [llm-drafting.md](llm-drafting.md)。

### LLM 自动修订 / Auto revise with an LLM

```bash
# 缺省：只输出整章 diff，不写盘
python scripts/novelops_cli.py auto-revise \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch03.md \
  --json

# 确认 diff 后写回（先自动 snapshot + 章节备份）
python scripts/novelops_cli.py auto-revise \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch03.md \
  --apply --json
```

跑完修订闭环后，把可局部修补（local-dimension）的问题段落交 LLM 做最小化重写；同样支持 `--dry-run` 与 `--mock-response`。

`--apply` 前会重跑知识边界检查与审计：若审计判定 `overall: block`（存在 critical 问题），局部重写修不了结构性问题，命令会拒绝写入并提示先处理 critical 项；确认仍要继续时加 `--force`。

```bash
python scripts/novelops_cli.py auto-revise \
  --project /path/to/project \
  --chapter-file /path/to/project/chapters/ch03.md \
  --apply --force --json
```

### 项目级配置 / Project config

`init` 会在项目根生成 `novelops.config.json`，三个节都可省略：

- `llm`：模型接入（默认本地 Ollama `http://localhost:11434/v1`；接 Nous Portal 云端改 `base_url` 为 `https://inference-api.nousresearch.com/v1` 并设环境变量 `NOVELOPS_LLM_API_KEY`）
- `audit`：审计规则定制——关键词表 extend/replace/disable、逐规则阈值覆盖、`rules_disabled` 禁用规则
- `knowledge`：知识边界检查定制——token 表、自定义泄漏正则、`kinds_disabled`

字段清单见 [references/json-schemas.md](../references/json-schemas.md) 第 14 节；无配置时所有行为与 1.0.0 一致。

### 长文档拆解 / Reverse long document

```bash
python scripts/novelops_cli.py reverse-longdoc \
  --source /path/to/long-document.md \
  --workspace /path/to/reverse-workspace \
  --chapters-per-file 10 \
  --json
```

这个命令适合超长文本拆解场景，会产出：

- `index/chapter_list.json`
- `chunks/*.json`
- `reverse_analysis/chunk_analysis/*.json`
- `reverse_analysis/summary/summary.json`
- `reverse_analysis/summary/summary.md`

### 跑回归 / Run smoke tests

```bash
python scripts/novelops_cli.py smoke-test
```

## 补充说明 / Notes

- 这次调整**不要求**把 CLI 做成 pip 包。
- 当前目标是把 CLI 提升为更正式、可被自然引用的**工作流入口**。
- 底层脚本仍然是实际能力实现层，CLI 负责组织更完整的使用路径。

