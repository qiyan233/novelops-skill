# 安装与环境 / Installation

如果你只想先跑起来，按下面做就够了。

> 推荐入口 / Recommended entrypoint：`python scripts/novelops_cli.py ...`

## 方式一：直接使用仓库 / Use the repo directly

```bash
git clone https://github.com/qiyan233/novelops-skill.git
cd novelops-skill
python scripts/novelops_cli.py --help
python scripts/novelops_cli.py smoke-test
```

适合你想：

- 先理解这个 skill skeleton 的结构
- 直接改 `SKILL.md`、`scripts/`、`assets/project-template/`
- 把它当作自己的小说工作流底座

## 方式二：下载 `.skill` 发布包

如果你使用 OpenClaw 或其他支持 `.skill` 包的应用，可从 Releases 获取。

仓库内也可自行打包：

```bash
python scripts/novelops_cli.py package
```

（`bash scripts/package_skill.sh` 是遗留入口，功能等价。）

## 最小运行要求

- Python 3
- 一个可编辑 Markdown / JSON 的本地环境

本仓库当前不依赖复杂第三方 Python 包，默认使用标准库脚本。

> Bash 不是必需项。`scripts/*.sh` 是遗留的 shell 入口，仅在你确实使用 bash 时才需要；
> 所有功能都有等价的 `python scripts/novelops_cli.py ...` 命令，原生 Windows 用 Python 入口即可。

## 首次验证 / First verification

建议第一次 clone 后先做两步：

```bash
python -m py_compile scripts/*.py
python scripts/novelops_cli.py smoke-test
```

如果你更习惯直接调底层脚本，也可以继续使用：

```bash
bash scripts/smoke_test.sh
```

如果你正在评估真实使用方式，继续看：

- [快速上手](getting-started.md)
- [用户路径](user-paths.md)
- [CLI 入口](cli.md)
- [示例项目模板说明](project-template.md)

