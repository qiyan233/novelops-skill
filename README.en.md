# NovelOps Skill

[![CI](https://img.shields.io/github/actions/workflow/status/qiyan233/novelops-skill/ci.yml?branch=main&label=CI)](https://github.com/qiyan233/novelops-skill/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Version](https://img.shields.io/badge/version-v1.1.0-blue)](CHANGELOG.md)

Current version: **1.1.0**

An **agent-oriented** workflow skill for long-form fiction. It runs novels, serials,
web fiction, and fan fiction as a **long-term maintainable process** — the point is not
"generate one chapter", but keeping the world consistent and the state traceable by
chapter 50.

Under the hood it is a plain Python 3 CLI over plain-text state files with no host lock-in,
so OpenClaw, Claude Code, and IDE- or terminal-embedded agents can all drive it — see
[using it with different agents](docs/agent-integration.md).

Inspired by **InkOS**: <https://github.com/Narcooo/inkos>. This project is a skill skeleton
inspired by it, not an official port.

[中文](README.md) | English

---

## The problem it solves

The hard part of long-form writing is not "what happens next" — it is **remembering who
knew what, back in chapter 3, by the time you reach chapter 50**. This repo turns that into
an executable process:

- **Truth files** hold world rules, current situation, and each character's knowledge boundary
- **`write-next`** assembles a structured packet of what the next chapter should do — and avoid
- **`draft`** hands that packet to an LLM (Hermes-first, local Ollama by default)
- **`revise` / `auto-revise`** run the audit and revision loop
- **`extract-state` / `state-update`** write newly established facts back into the state
- **`snapshot` / `diff`** let you roll back and compare at any time

It is not just about *writing*. It is about organizing **multi-chapter writing**.

## Who it is for

Good fit if you:

- Write long fiction across many chapters and need chapter summaries, character state,
  hooks, and the current situation kept in order
- Want to build a fiction-writing skill similar to InkOS
- Want audit, revision, state update, and snapshotting alongside the writing itself

Poor fit if you just want a one-off short piece — this repo is deliberately heavyweight.

## Quick start

Requires Python 3. No third-party dependencies.

```bash
git clone https://github.com/qiyan233/novelops-skill.git
cd novelops-skill

python scripts/novelops_cli.py smoke-test                       # self-check; prints "Smoke test passed."

python scripts/novelops_cli.py init ./my-novel "My Novel"       # scaffold a project
python scripts/novelops_cli.py write-next --project ./my-novel  # prepare the next chapter
```

> **On Windows or any environment without bash**, always use
> `python scripts/novelops_cli.py ...`. The `scripts/*.sh` files are legacy entrypoints
> that need bash; every feature has an equivalent Python command.

More detail: [installation](docs/installation.md) · [getting started](docs/getting-started.md).

## The core pipeline

```text
init -> write-next -> draft -> revise -> extract-state -> state-update
```

`draft` can be done by a human, an agent, or an LLM. `revise` chains
knowledge-check / audit / revision-plan / spot-fixes internally.
See [CLI reference](docs/cli.md) for command details.

## What it does today

Covered:

- Next-chapter preparation (`write-next`, with a single-chapter contract and scene beats)
- LLM drafting (`draft`, Hermes-first, local Ollama by default, switchable to Nous Portal)
- Revision loop (`revise`) and paragraph-level LLM auto revision (`auto-revise` — diff by
  default, automatic snapshot before `--apply`)
- Knowledge-boundary checking (`knowledge-check` — catches a character knowing too early)
- Configurable rule engine (`novelops.config.json` for audit keyword tables, thresholds,
  and disabled rules)
- State extraction and truth-file updates (`extract-state` / `state-update`)
- Snapshot, diff, and packaging (`snapshot` / `diff` / `package`)
- Regression tests (`smoke-test`)

Not yet:

- More complete example projects
- Multi-model comparison and automatic retry strategies
- Finer-grained style-learning automation

## What is in the repo

| Path | Purpose |
| --- | --- |
| [`SKILL.md`](SKILL.md) | The main skill document — the real entrypoint for agents |
| [`scripts/`](scripts/) | CLI entrypoint and underlying scripts |
| [`assets/project-template/`](assets/project-template/) | Novel project template (copied by `init`) |
| [`examples/demo-novel/`](examples/demo-novel/) | A complete example project |
| [`docs/`](docs/) | User documentation |
| [`references/`](references/) | Rules, schemas, and JSON contracts |

## Documentation map

**New here? Read in this order:**

1. [`SKILL.md`](SKILL.md) — positioning; closest to "how the skill actually works"
2. [`examples/demo-novel/README.md`](examples/demo-novel/README.md) — a full worked example,
   far more intuitive than reading internals first
3. [`docs/cli.md`](docs/cli.md) — when you are ready to run commands

**By topic:**

| Document | Contents |
| --- | --- |
| [docs/agent-integration.md](docs/agent-integration.md) | Wiring it into Claude Code / OpenClaw / other agent apps |
| [docs/installation.md](docs/installation.md) | Installation and minimum requirements |
| [docs/getting-started.md](docs/getting-started.md) | From zero to chapter one |
| [docs/cli.md](docs/cli.md) | All commands and flags |
| [docs/user-paths.md](docs/user-paths.md) | Which path fits your scenario |
| [docs/project-template.md](docs/project-template.md) | What each template file is for |
| [docs/llm-drafting.md](docs/llm-drafting.md) | LLM drafting / auto-revise config and offline channels |
| [docs/faq.md](docs/faq.md) | Frequently asked questions |
| [references/json-schemas.md](references/json-schemas.md) | Every JSON output contract |
| [references/audit-rules.md](references/audit-rules.md) | The audit rule list |
| [references/workflow-playbooks.md](references/workflow-playbooks.md) | Workflow playbooks |

**Project:** [CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md) ·
[SECURITY.md](SECURITY.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) ·
[docs/audit-fixes.md](docs/audit-fixes.md) (maintainers: audit fix log)

> The user-facing documentation is written in Chinese. This file mirrors the README
> for English readers; for the full docs, start from [docs/getting-started.md](docs/getting-started.md).

---

This project is a skill skeleton inspired by [InkOS](https://github.com/Narcooo/inkos),
not an official port.
