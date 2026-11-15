# Audit Rules

当前 `audit_chapter.py` 使用的是“启发式但结构化”的规则集。

## 规则列表

- `AUD-101` repetition-fatigue
  - 重复转场词过多
- `AUD-102` report-speak
  - 解释腔 / 报告腔过强
- `AUD-103` crowd-cliche
  - 群体反应陈词滥调
- `AUD-104` paragraph-monotony
  - 段落长度过于平均
- `AUD-105` hook-overload
  - 开放 hook 过多但章节体量有限
- `AUD-106` hook-advancement
  - 章节似乎没有触碰当前开放 hook
- `AUD-107` outline-drift
  - 与当前大纲关键词联系太弱
- `AUD-108` state-cohesion
  - 与 `current_state.md` 的当前有效状态联系太弱
- `AUD-109` protagonist-lock
  - 可能触犯主角锁 / 禁区
- `AUD-110` information-boundary
  - POV / 角色认知边界可能泄漏
- `AUD-111` timeline-continuity
  - 紧凑章节内时间跳跃过多
- `AUD-112` dialogue-balance
  - 长章节没有对话，需确认是否故意
- `AUD-113` telling-vs-dramatizing
  - 直接情绪标签过多
- `AUD-114` state-update-pressure
  - 章节内状态转折很多，提醒接受后更新 truth files

## 设计意图

这些规则不是为了“自动判死刑”，而是为了：

- 先发现高风险问题
- 再优先修最小代价的问题
- 最后决定是否需要重写场景或章节

## 定位锚点

每条 finding 都带 `anchors`：命中问题的段落序号（`0` 起，最多 2 个；段落按空行切分，标题段不计入）。`auto-revise` 优先用它定位要改写的段落，只有锚点为空时才退回用 `evidence` 文本搜索；因此 `evidence` 为空但 `anchors` 有值的规则（如 `AUD-104`）也能被定向修订。

## 边界声明

报告里的 `coverage` 说明自动检查的边界：

- `automated_rules`：本次实际跑过的规则
- `human_only_dimensions`：没有被任何脚本检查的维度（角色行为一致性、世界规则违背、资源与道具连续性、支线停滞、承诺与兑现、情节逻辑漏洞）

也就是说 `overall=pass` 只代表上面这些自动规则没触发，不等于章节没有问题。这些维度仍需人工或 LLM 在 `audit` 之外复核。

## 使用建议

- `critical`：优先拦下
- `major`：默认需要修
- `minor`：默认 spot-fix
- `note`：作为提醒，不一定必须改

