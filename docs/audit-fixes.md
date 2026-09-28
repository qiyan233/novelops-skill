# 审计修复技术日志（2026-09）

本文件记录一轮针对「正确性与数据安全」的代码审计所发现的问题、根因与修复方式。
面向维护者；面向用户的变化摘要见 [`../CHANGELOG.md`](../CHANGELOG.md) 的 Unreleased 段。

## 审计范围与方法

`novelops-skill` v1.1.0，23 个脚本约 5200 行 Python（纯标准库）。该工具无服务端、
无网络暴露面（LLM 调用走用户自配的 OpenAI 兼容端点），因此不按 Web 渗透维度审计，
而是聚焦：代码正确性、数据一致性（不得损坏用户创作数据）、跨平台（Windows 为主）、
错误处理、文档与实现的契约一致性。

分四个分片并行审计（质量检查脚本 / 修订与起草链路 / 状态持久化链路 / CLI 与打包），
随后逐条**实际运行复现**再定级；无法复现的疑点一律撤回，见文末。

---

## 严重

### 1. 中文数字章节标题全线失效

**现象**：用「## 第一章」书写 `chapter_summaries.md` 的项目（中文网文常态）会连锁出错——
`chapter_sections()` 返回 0 节，`latest_sections()` 退化为返回整份文件（污染送给模型的
上下文），`latest_pov()` 返回空串，`infer_next_chapter_from_project()` 把已有 2 章的项目
判成第 1 章。

**根因**：`novelops_common.CHAPTER_HEADING_RE` 与 `parse_chapter_number` 只匹配
`第\s*\d+\s*章`（阿拉伯数字）。同模块的 `parse_chinese_numeral()` 早已实现并被
`draft_chapter` / `reverse_long_document` 使用，只是没接进这条路径。

**修复**：抽出共享常量 `CN_NUMERAL_CHARS`，两处正则统一支持中文数字；
`parse_chapter_number` 顺带支持 `ch-01` / `chapter_01` 等分隔写法。
`hook_report.latest_chapter_seen` 原先自带一套只认阿拉伯数字的正则，改为复用共享解析器。

**验证**：`## 第一章` / `## 第十二章` / `## 第三百二十一章` 均正确解析；
`latest_pov` 恢复取值；2 章项目推断出 3；`hook-report` 章号一致。

### 2. 单章契约守卫可被无空格中文标题绕过

**现象**：`## 第一章夜雨` 不被识别为章节标题。后果有二：模型一次输出两章时
`len(headings) > 1` 不成立，**草稿被接受并落盘**；单章时被判为「无标题」，额外插入
`## 第 N 章`，文件出现双标题。`docs/llm-drafting.md` 明确承诺「若模型仍输出多个章节
标题，草稿会被拒绝」——该承诺此前并不成立。

**根因**：`draft_chapter.LOOSE_HEADING_RE` 末尾的 `\b`。Python 3 的 `\w` 含中文，
「章」与紧随其后的标题汉字都是词字符，二者之间不构成词边界，正则整体失配。

**修复**：`\b` → `(?![0-9A-Za-z])`。同时补一条保守判定——**不带 `#` 且含句末标点**
（`。！？；`）的行不算标题，避免去掉 `\b` 后正文句子（如「第一章的故事就这样结束了。」）
被误判为标题而触发误拒。

**验证**：10 种标题写法（含无空格、中文数字、`#`/`##`）全部正确识别；
两章无空格输出被拒绝；单章不重复加标题；无标题时仍自动补齐；正文句不误判。

### 3. 打包泄露用户创作数据

**现象**：在仓库内执行 `init ./my-novel` 后运行 `package`，产出的 `.skill` 包含整本小说
正文与 `.novelops-state` 全部快照。

**根因**：`package_skill.IGNORE_NAMES` 只排除 `.git/.smoke-work/.package-work/node_modules`，
既漏了自己的状态目录，也不读 `.gitignore`；而 `copy_tree(ROOT, ...)` 递归整个仓库。
排除名单在原理上就无法识别「用户自己创建的任意命名目录」。

**修复**：顶层改为**白名单** `INCLUDE_TOP_LEVEL`，只有显式列出的条目会进包；
同时对被跳过的顶层项向 stderr 输出提示，避免维护者新增目录后静默漏打包。
`.novelops-state/.inkos-state/dist` 仍留在忽略名单里作为纵深防御。

**验证**：实测含私密正文与快照的 `_pkgtest` 项目不再进包；`SKILL.md`、
`scripts/`、`examples/`、`references/`、`assets/` 等发布内容完整。

### 4. 写回非原子

**现象**：全仓库 grep 无任何 `os.replace` / `NamedTemporaryFile` / `fsync`，正文与真值
文件全部直接 `write_text`（先截断再写）。进程被杀、磁盘写满、Windows 文件被占用时留下
半截文件。`update_story_state` 尤其糟：先追加 `chapter_summaries.md`、后写
`current_state.md`，后者失败会留下两文件互相不一致的半套状态，且无回滚。

**修复**：`novelops_common` 新增 `atomic_write_text`（同目录临时文件 + `fsync` +
`os.replace`，失败清理临时文件），`write_json` 一并改用；覆盖 `draft_chapter`、
`auto_revise`、`update_story_state`、`reverse_long_document`、`novelops_cli.init`。
`update_story_state` 另把 `sync_current_state` 拆成纯函数 `build_current_state_text`，
在**改动任何文件之前**先算完两个真值文件的新内容。

**验证**：模拟写入失败（`write()` 收到非字符串）——原文件完好、不留 `.tmp`；
成功路径也不留 `.tmp`。

### 5. 模型输出未净化，围栏与客套话进正文

**现象**：``` 包裹的返回、开头带「好的，以下是修订后的段落：」的返回，全部被判为
`rewritten` 并原样写回小说正文。一个号称「段落级最小化安全修订」的功能，会把整段
替换成带代码围栏的文本。

**根因**：`auto_revise.validate_rewrite` 只校验空/标题/长度比，且校验的是原始文本而
调用方写回的是 `result['content']` 原文；`draft_chapter.validate_draft` 同理。

**修复**：`novelops_common` 新增 `clean_model_output`（剥代码围栏 + 去开场白/创作说明行），
draft 与 auto-revise 在**校验之前**统一净化，且写回的是净化后的文本。
判定开场白用「短行（≤40 字）+ 冒号结尾 + 含引导词」的保守组合——正文段落几乎不会以
冒号结尾，而开场白几乎总是，因此不会误伤「可以想象，他当时并不知道真相。」这类句子。
`validate_rewrite` 改为返回 `(status, reason, cleaned)`。

**注意**：实现过程中一个迭代缺陷被测试抓出——单纯「先剥围栏、再剥开场白」在处理
「开场白 + 围栏」组合时，围栏因文本不以 ``` 开头而漏剥。改为两阶段交替剥离直到结果稳定。

**验证**：围栏、开场白、开场白+围栏、首尾创作说明行均被剥离；4 类正常句未被误伤；
端到端 draft 落盘无围栏无开场白；`validation.sanitized` 正确标记。

### 6. knowledge-check 误报与严重度掩盖

**现象 A（误报）**：belief `李明：不知道张三的身份` + 正文 `李明制定了一个计划。`
→ 报 `major / knowledge-leak`。调用方 `ok: false`。

**根因 A**：检测只要求「句子含角色名 + 任一 `FACT_CONFIDENCE_TOKENS`」，而该词表含
「计划」「身份」等泛词，从不校验该词是否对应该条 belief 的具体事实。

**现象 B（严重度掩盖）**：`没人知道的是，真相就是张三。` 同时命中
`premature-certainty`(minor) 与 `omniscient-leak`(major)，因循环命中首个 pattern 即
`break`，而模式表把 minor 排在前面，实际只报 minor。

**修复**：
- 新增 `belief_fact_keywords()`：从 belief 语句去掉否定词后按虚词切词，得到该条 belief
  真正约束的事实词，正文必须命中其中之一。**注意不能把与泛词表重合的事实词（如「真相」）
  排除掉**——belief 说「玉佩的真相」、正文写「看出了真相的全部内情」而不提玉佩，仍属越权
  （此处第一版实现过度修正，被既有 smoke test 用例抓出并修正）。
- 泄漏模式改为遍历全部 pattern 取最高严重度，不再首个即 break。
- `build_character_beliefs` 对缺少「角色：事实」分隔符的行不再把整行当角色名（会导致该条
  belief 永久失配且无人察觉），改为归入 `summary.malformed_beliefs` 显式报出。

**验证**：泛词误报消除；命中具体事实仍报；`omniscient-leak` 不再被 minor 掩盖；
malformed belief 被标出。

---

## 中等

| # | 问题 | 根因 | 修复 | 验证 |
|---|---|---|---|---|
| 7 | 半截快照污染 `diff` | `snapshot()` 先建目录、manifest 最后写；中途失败留下无 manifest 的目录，而 `resolve_snapshot` 只按 `is_dir()` 判定 | 失败自动 `rmtree`；快照解析要求 `manifest.json` 存在 | 手工造无 manifest 目录且名字排在最后，`diff --from latest` 正确跳过 |
| 8 | smoke test 无法并行 | 固定用 `<repo>/.smoke-work` 且启动即 `rmtree`，并行运行互相删除，表现为失败点各不相同的假故障 | 改用 `tempfile.mkdtemp(prefix='novelops-smoke-')` | 两个 smoke test 并发运行，双双通过（改前随机失败） |
| 9 | AUD-104 是死逻辑 | 段落只按空行 `\n\s*\n` 切分，单换行分段的中文稿恒为 1 段，`min_paragraphs >= 4` 永不成立 | 抽出 `split_paragraphs()`，单段结果回退按行切分；`chapter_metrics` 同步复用 | 单换行 6 段稿现在触发 AUD-104 |
| 10 | 关键词提取丢数字 | 字符类只含 CJK/拉丁字母，数字被当边界丢弃：`第1990年的约定` → `年的约定` | 改用 `[^\W_]`（单词字符去下划线 = 中日韩+字母+数字） | `1990` 保留，不再产生「年的约定」碎片 |
| 11 | belief 解析静默失配 | `raw.split('：')[0].split(':')[0]` 无分隔符时把整行当角色名 | 归入 `malformed_beliefs` 报出 | 无分隔符行被标出；正常 belief 正常载入 |
| 12 | 整文件回写翻转行尾 | `read_text` 归一化 CRLF→LF，`write_text` 默认转换行尾，把只改一段的编辑变成全文件 diff；且替换段落时未保留原段落首尾空白，**吞掉文件末尾换行** | 新增 `detect_newline()` 探测原风格，写回前还原；替换时保留原切片的首尾空白 | 端到端：CRLF 章节经 `--apply` 后仍是 CRLF、无裸 LF、末尾换行保留 |
| 13 | 证据过宽撑爆预算 | `token in para['text']` 对「突然」这类通用词会命中多段，一个 finding 就能吃满 `--max-paragraphs` | 新增 `MAX_PARAGRAPHS_PER_FINDING = 2`，超出时按靠前段落截取并记 `evidence-too-broad` | 6 段重复词稿：targets 受控，`skipped_findings` 出现 `evidence-too-broad` |
| 14 | critical 时仍可 `--apply` | 报告记录了 `based_on.audit_overall` 却不据此拦截 | 审计判定 `block` 时默认拒绝 `--apply`，新增 `--force` 逃生通道（含 CLI 透传） | 空章（AUD-000 critical）下 `--apply` 被拒且未改动文件；`--force` 放行 |
| 15 | 字段注入破坏文档结构 | `--state-change $'A\n## Timeline position'` 的换行落到行首，被当成新的 `##` 标题，破坏 `upsert_section` 定位 | 新增 `one_line()`，所有自由文本字段压成单行 | 注入不再产生标题行；内容被正确压平 |
| 16 | diff 无法区分「删除」与「空文件」 | `read_text` 对缺失文件返回 `''`，`added/removed` 判定失真 | `load_file` 返回 `(内容, 是否存在)`，并新增 `file_diffs[].present` | 缺失文件被正确识别 |
| 17 | 分句切断中文引号 | `split_sentences` 按 `。！？` 全局切分、不识别引号，`「你到底是谁？」` 被切成 `「你到底是谁` 与孤立的 `」` 两个片段，残片混进候选句/证据串/摘要 | 改为逐字符扫描并跟踪引号深度，成对引号/书名号内不切；**跨行重置深度**，避免一个未闭合的「把整章吞成一个句子 | 引号句保持完整；孤立残片消失；未闭合引号不跨行吞并 |

---

## 轻微

- `extract_state.pick_summary` 只在前 12 句打分 → 长章节摘要永远取自开头。改为全文打分。
- `draft_chapter` mock 文件为 `[]` 时 `[0]` 抛 `IndexError`（非 `SystemExit`，不被友好处理）。改为显式报错。
- `llm_client.resolve_llm_config` 中项目配置的 `llm` 节写 `null` 会覆盖默认值，请求体出现 `"temperature": null`。改为 `None` 一律视为未设置。
- `novelops_cli.sh()` 硬编码 `bash` 且无任何调用方。删除。
- 项目模板缺 `.gitignore`，用户把小说纳入版本控制时会把 `.novelops-state/` 快照一起提交。模板补 `.gitignore`，仓库根 `.gitignore` 同步补状态目录。
- `reverse_long_document` 分块按起止章号命名，源文档章号重复时节名相同、后写覆盖先写。文件名加块序号。
- `hook_report.parse_line` 只认半角括号，全角 `（opened：ch3）` 不解析。**未修**——模板与文档统一使用半角，影响面小。

---

## 复测后撤回的疑点

以下三点在审计中被提出，实际运行验证后**不成立**，未做改动：

1. **`section_meta.truncated` 误报**：outline 命中章节行时输出远小于原文却标记 `truncated: true`。核查后确认这是**正确行为**——内容确实被裁掉了。
2. **`--write-report` 给 JSON 输出加 `report_path` 字段**：`references/json-schemas.md` 已明确记载该字段「仅 `--write-report` 时出现」，非契约违规。
3. **Windows 无 bash 导致流程中断**：`docs/installation.md` 把 Bash 列为要求确有误导，但 `SKILL.md` 已写明跨平台优先使用 `python scripts/novelops_cli.py init ...`，且 CLI 全部子命令均为纯 Python，流程不会断。属文档表述问题。

---

## 验证方式

- 项目自带 `scripts/smoke_test.py`：通过；并已验证**并发运行两个实例**也通过。
- 针对每条修复编写临时验证脚本（共 70+ 断言），覆盖单元行为与 CLI 端到端；验证后已删除。
- 在仓库自带的 `examples/demo-novel` 副本上跑通
  `hook-report / context / write-next / audit / extract-state / snapshot / diff / state-update`。
- `python -m compileall scripts/` 全绿。
- 实现过程中由测试抓出并修正的两处自引入缺陷：净化顺序（开场白+围栏组合）、
  事实关键词过度排除（「真相」）导致的回归。

## 未处理

- `hook_report` 全角括号容忍（见上）。
- `inkos_cli.py` / `inkos_common.py` 兼容垫片无消费者，保留以兼容旧调用方。
- `docs/cli.md` 仅覆盖 18 个子命令中的 11 个（其余在 `SKILL.md` 有记录），属文档覆盖不全，非实现缺陷。
