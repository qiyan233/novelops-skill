# 贡献指南

感谢你关注 `NovelOps Skill`。

这个仓库的定位是：**面向智能体应用的长篇小说工作流 skill skeleton**（不绑定具体宿主，
OpenClaw / Claude Code / IDE 内与终端里的智能体都可以驱动）。
欢迎围绕这一定位提交改进，但请尽量保持变更聚焦，不把它扩张成完全不同的产品。

## 适合贡献的方向

- 修复脚本 bug、边界条件和回归问题
- 补充或改进 smoke test / CI 基础检查
- 完善 `SKILL.md`、`references/`、README、上手文档
- 优化项目模板与 truth files 结构
- 增加更稳的 JSON 契约、CLI 子命令或审计维度
- 提供与小说写作工作流强相关的示例

## 提交前建议

1. 先阅读：
   - `README.md`
   - `SKILL.md`
   - `references/` 中与你修改相关的文档
2. 尽量做**最小、明确、可解释**的修改。
3. 不要顺手重写大量无关内容。
4. 文档优先中文，可适度保留英文术语。
5. 保持脚本无额外复杂依赖；如必须新增依赖，请先说明必要性与替代方案。

## 本地验证

如果环境允许，优先执行：

```bash
python scripts/novelops_cli.py smoke-test
```

（`bash scripts/smoke_test.sh` 是遗留入口，需要 bash，功能与上面等价。）

如无法完整跑 smoke test，至少建议检查：

```bash
python -m py_compile scripts/*.py
```

并确认以下文件仍然存在且链接正常：

- `README.md`
- `README.en.md`
- `SKILL.md`
- `scripts/`
- `assets/project-template/`

## Pull Request 建议

请在 PR 描述中尽量写清：

- 变更背景 / 解决的问题
- 主要改动点
- 是否影响现有工作流或 JSON 输出
- 本地验证方式与结果
- 是否涉及文档、脚本、模板或 CI

## Issue 建议

提交 Issue 时，请尽量附上：

- 使用场景
- 复现步骤
- 预期结果 / 实际结果
- 相关章节样例、状态文件样例或命令行输出

## 行为期望

参与讨论与协作时，请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 安全问题

如果你发现安全问题、敏感文件处理问题或供应链风险，请不要先公开开 Issue，优先参考 [SECURITY.md](SECURITY.md) 进行私下报告。

