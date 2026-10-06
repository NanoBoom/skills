# PRP Core

Complete PRP (Product Requirement Prompt) workflow automation, packaged as
**Agent Skills** with specialist subagents, for Claude Code, Codex, and Pi.

[中文文档](./README.zh-CN.md)

This repository is also the `nanoboom` marketplace, and it ships two plugins.
**`prp-core`** is the PRP workflow and everything below is about it.
**`github-project`** is a smaller, independent plugin for running requirements
as GitHub Issues; it has its own [README](./plugins/github-project/README.md) and
installs separately. Neither depends on the other.

> **Forked from upstream.** This repository is a fork of the `prp-core` plugin
> from [Wirasm/PRPs-agentic-eng](https://github.com/Wirasm/PRPs-agentic-eng),
> taken at commit `2cced43` (2026-09-01), and maintained here with its own
> changes. All credit for the original work goes to Rasmus Widing. See
> [NOTICE](./NOTICE) for exactly what was changed at the fork point, and
> [LICENSE](./LICENSE) for the terms.

## Overview

This plugin provides a comprehensive workflow for creating, executing, and
shipping features using the PRP methodology, where **PRP = PRD + curated codebase
intelligence + agent/runbook**, designed to enable AI agents to ship
production-ready code on the first pass.

Everything here ships as **skills** (not slash commands). Most are both
**user-invocable** (type `/prp-core:<name>`) and **agent-invocable** (Claude
loads them automatically when a request matches their description). The
maintainer triage and worklist skills are user-invocable only.

> **Install the agents, not just the skills.** Most skills dispatch the
> `prp-core:<agent>` subagents in [`agents/`](./plugins/prp-core/agents), and two
> use the Stop hooks in [`hooks/`](./plugins/prp-core/hooks). `npx skills` copies
> `SKILL.md` files only. Use the [route for your harness](#installation) to get
> the agents too; [docs/harnesses.md](./docs/harnesses.md) says what each one
> keeps and loses.

## Skills

### Product and planning

| Skill | Description |
|-------|-------------|
| `/prp-core:prp-prd` | Interactive, problem-first PRD generator with an implementation-phases table |
| `/prp-core:prp-prd-update` | Maintains PRD phase status and artifact links as work lands |
| `/prp-core:prp-plan` | Create an implementation plan (from a PRD or free-form). Also wires bidirectional plan references via its `update-references` workflow |
| `/prp-core:prp-diagram` | Mermaid-only visual supplement for a plan: data model, architecture, and flow |
| `/prp-core:prp-spike` | Settle a feasibility question by building the smallest throwaway artifact that could falsify it |
| `/prp-core:prp-research-team` | Design a dynamic research team and plan using agent teams |
| `/prp-core:prp-codebase-question` | Research how the codebase works using parallel agents, documenting what exists |

### Build and ship

| Skill | Description |
|-------|-------------|
| `/prp-core:prp-issue` | Own an issue, PRD, document, plan, or idea in one context through a published `READY TO MERGE` review and green CI |
| `/prp-core:prp-implement` | Execute a plan through validated commit and PR; write the durable implementation report |
| `/prp-core:prp-commit` | Smart commit with natural-language file targeting |
| `/prp-core:prp-pr` | Push the branch and open a PR with template support |
| `/prp-core:prp-loop` | **Self-driving** cyclic pipeline: plan → implement → PR → review, looping review→fix until clean, each stage in a fresh visible subagent. `--until implement` stops after a green implementation and open PR |
| `/prp-core:prp-deliver` | Experimental. Only runs when invoked explicitly |

### Review and triage

| Skill | Description |
|-------|-------------|
| `/prp-core:prp-review` | Agent-based PR review using the skill's current default reviewer set; named specialist scopes are additive |
| `/prp-core:prp-debug` | Diagnose a root cause and publish the evidence to the matching GitHub issue |
| `/prp-core:prp-maintainer-triage` | Route a contributor PR or reported issue through its lightweight maintainer triage workflow. User-invocable only |
| `/prp-core:prp-issue-contract` | Create an issue or check its preconditions before agent automation |

### Orchestration and workspace

| Skill | Description |
|-------|-------------|
| `/prp-core:prp-orchestrate` | Turn the session into an **orchestrator**: coordinate autonomous delivery workstreams in git worktrees, with human-only and merge gates, a standing-decisions log, and merge sequencing |
| `/prp-core:prp-worktree` | Create, list, and safely tear down isolated checkouts under `.worktrees/` |
| `/prp-core:prp-worklist` | Render a repository's open work so the maintainer can see what to take next. User-invocable only |
| `/prp-core:agent-policy` | Pick the model and effort for every agent at launch by task type, to save tokens. Ships lookup tables for Claude Code and Codex |

### Authoring

| Skill | Description |
|-------|-------------|
| `/prp-core:prp-meta-skill` | Author new skills and refactor fat skills into a lean `SKILL.md` + `references/` (prescribes the craft, not your project's content) |
| `/prp-core:prp-technical-writing` | Write and edit developer documentation that is clear, concrete, and verified |
| `/prp-core:prp-bro` | Restate the previous response in plain language, with no jargon |

### GitHub Issue requirement management

The `github-project` plugin, installed separately with
`/plugin install github-project@nanoboom`. These three talk to GitHub through
the `gh` CLI and nothing else: no subagent, no plugin root path, no file outside
each skill's own directory. A single `SKILL.md` taken through `npx skills` still
works, which is not true of the `prp-core` skills above. Full documentation is
in the [plugin README](./plugins/github-project/README.md).

| Skill | Description |
|-------|-------------|
| `/github-project:github-project-setup` | Inspect, initialize, or repair the Project, its `Status` and `Priority` fields, the Board and Backlog views, the built-in automations, the Issue template, `.github/github-project.yml`, and the language its Issue text is written in |
| `/github-project:github-project-manage` | Run the Issue lifecycle across eleven modes, from drafting a requirement to closing it, keeping each Issue's Project item in step |
| `/github-project:github-project-audit` | Read-only audit of Issue quality and Issue-to-Project consistency against a 28-rule catalog with stable rule IDs |

## Agents

Specialized, advisory agents used by the review and planning skills. They are
report-only by design: they analyze and report findings but never modify files or
commit. Each one sets `disallowedTools: Write, Edit, NotebookEdit`, which Codex
gets as a read-only sandbox and Pi as a read-only tool list.

### Codebase analysis

| Agent | Description |
|-------|-------------|
| `codebase-analyst` | Documents HOW code works with file:line references |
| `codebase-explorer` | Finds WHERE code lives AND extracts patterns |
| `root-cause-analyzer` | Proves the causal chain, smallest fix boundary, and regression check for broken behavior |
| `web-researcher` | Researches the web for docs, APIs, best practices |

### Review

| Agent | Description |
|-------|-------------|
| `code-reviewer` | General correctness, sanity, scope, and repository fit |
| `comment-analyzer` | Materially false prose and concrete maintenance traps |
| `pr-test-analyzer` | Meaningful behavior without regression protection |
| `silent-failure-hunter` | Failure paths that become indistinguishable from success |
| `seam-analyzer` | Missing types and drift across system boundaries |
| `code-simplifier` | Removes avoidable machinery through proven smaller primitives |
| `docs-impact-agent` | False or missing documentation that changes reader behavior |

Review agents are invoked automatically by `/prp-core:prp-review` and the review
stage of `/prp-core:prp-issue`, or manually via the Agent tool. Outside Claude Code
each agent is named `prp-core__<agent>`, and the installed skills say so.

## Project sidecars

Two optional documents, if your project has them, are read by the skills that need them. Keep them
anywhere in your repository. Link them from your `AGENTS.md` or `CLAUDE.md` so agents reach them
immediately; otherwise the skills find them by name. Do not put them in the PRP store, which lives
outside the repository and holds generated artifacts: these are yours, and they belong in version
control beside the code they govern. Nothing creates them and nothing fails when they are absent.

| File | Holds | Read by |
|------|-------|---------|
| `direction.md` | Product direction and scope: what this project is for, and what it declines to become | `prp-plan`, `prp-review`, `prp-issue-contract`, `prp-maintainer-triage` |
| `engineering.md` | The standard work is checked against, in an engineering manager's voice: the objective function, the taste, the risk posture, what review is for | `prp-plan`, `prp-implement`, `prp-review` and its review agents, `prp-issue-contract`, `prp-maintainer-triage` |

They exist to keep judgment out of prompts. `AGENTS.md` carries durable, short guidance; product
direction changes and belongs in `direction.md`; the standard work is checked against belongs in
`engineering.md`, which holds what needs judgment and hands anything that becomes machine-checkable
to a lint rule, a type, or a CI check. A change that contradicts stated product
direction is a scope question for the operator, not a defect the author can fix in the diff.

## Hooks

The plugin ships two Stop hooks.

`hooks/prp-research-team-stop.sh` validates `prp-research-team` output. The skill writes its plan path to a
sentinel file in `.prp/state/prp-research-team.state`; on Stop,
the hook checks the plan for the six required sections and, if any are missing,
blocks completion once with the list of what is absent. It cleans up the sentinel
on success, ignores stale sentinels (older than 2 hours), and never blocks twice
in a row.

`hooks/prp-loop-stop.sh` keeps the session driving a `prp-loop` working until the
loop is done or halted, which is what lets one `/prp-core:prp-loop` invocation run
every stage. It reads only `.prp/state/prp-loop.state.json`: it holds the session
recorded as the loop's owner while the loop is running, releases it while a
dispatched stage subagent runs, and lets it stop after three continuations with no
state change. Every other session stops normally.

Both hooks ship only with the plugin and are written for Claude Code. If you copy
the skills into `.claude/skills/` directly, neither runs. See
[docs/harnesses.md](./docs/harnesses.md#stop-hooks) for other harnesses.

## Workflows

### Large features: PRD → plan → implement

```
/prp-core:prp-prd "user authentication system"
    ↓  creates a PRD with an Implementation Phases table
/prp-core:prp-plan .prp/prds/user-auth.prd.md
    ↓  auto-selects the next pending phase, creates a plan
/prp-core:prp-implement .prp/plans/user-auth-phase-1.plan.md
    ↓  executes, validates, commits, opens the PR, and links delivery to the PRD
repeat /prp-core:prp-plan for the next phase
```

### Medium features: plan → implement

```
/prp-core:prp-plan "add pagination to the API"
/prp-core:prp-implement .prp/plans/add-pagination.plan.md
```

### Hands-off: the autonomous loop

```
/prp-core:prp-loop "add pagination to the API"
    ↓  plan → implement (loop to green) → PR → review → fix → re-review → clean
       one fresh subagent per stage, driven from this session
```

### Input to a reviewed PR

```
/prp-core:prp-issue 123
    ↓  plan → implement → PR → review → correct → re-review → green CI
```

## Installation

Every harness installs from the same source, `plugins/<plugin>/`, but not every
harness can take every part of it. [docs/harnesses.md](./docs/harnesses.md) has
the details.

| Harness | Route | Skills | The 11 agents | Stop hooks |
|---|---|---|---|---|
| Claude Code | plugin marketplace | yes | yes | yes |
| Codex | a clone, `make install-codex` | yes | yes | no |
| Pi | a clone, `make install-pi` | yes | with Pi's `subagent` extension | no |
| any Agent Skills harness | `npx skills add` | yes | no | no |

The clone routes need [`uv`](https://docs.astral.sh/uv/) and `make`. After
`git pull`, rerun the same `make` target to update, and `make uninstall-<harness>`
removes exactly what it installed.

### Claude Code (recommended)

Register the marketplace once, then install either plugin from it. The two are
independent and neither requires the other.

```
/plugin marketplace add NanoBoom/skills
/plugin install prp-core@nanoboom
/plugin install github-project@nanoboom   # optional, independent
```

Restart Claude Code so the skills, agents, and hooks load.

The same thing works outside the REPL, which is what you want in a script or a
Dockerfile:

```bash
claude plugin marketplace add NanoBoom/skills
claude plugin install prp-core@nanoboom --scope user
claude plugin install github-project@nanoboom --scope user
```

`--scope` takes `user` (default, all your projects), `project` (checked into the
repository's `.claude/settings.json`, so it is shared with everyone who clones
it), or `local` (this repository, your machine only).

#### Verify

```bash
claude plugin list
claude plugin details prp-core@nanoboom
```

`details` prints the component inventory: 24 skills, 11 agents, 2 hooks for
`prp-core`, and 3 skills for `github-project`. In-session, `/plugin` shows both
under the `nanoboom` marketplace, and typing `/prp-core:` completes against the
installed skills.

#### Update and uninstall

```bash
claude plugin marketplace update nanoboom
claude plugin update prp-core@nanoboom      # restart to apply
claude plugin uninstall prp-core@nanoboom
```

#### Install for the whole team

Commit this to your project's `.claude/settings.json`. Everyone who opens the
repository is offered both plugins, with no manual marketplace step:

```json
{
  "extraKnownMarketplaces": {
    "nanoboom": {
      "source": {
        "source": "github",
        "repo": "NanoBoom/skills"
      }
    }
  },
  "enabledPlugins": {
    "prp-core@nanoboom": true,
    "github-project@nanoboom": true
  }
}
```

#### Run from a working tree

To try a local checkout, point the marketplace at the directory instead of at
GitHub. This rewrites the `nanoboom` entry in your settings, so restore it when
you are done:

```
/plugin marketplace add /absolute/path/to/skills
/plugin install prp-core@nanoboom
# Restart Claude Code
```

To load one plugin for one session without installing anything, use
`claude --plugin-dir /absolute/path/to/skills/plugins/prp-core`, or
`.../plugins/github-project`.

### Codex

```bash
git clone https://github.com/NanoBoom/skills && cd skills
make install-codex
```

This needs the Codex CLI on your `PATH`. It generates `build/codex/`, a local
Codex marketplace, registers it as `nanoboom` with `codex plugin marketplace add`,
and installs each plugin from it with `codex plugin add`. The skills arrive with
dispatch names rewritten to `prp-core__<agent>`, and any skill over Codex's
8000-byte prompt limit is split so nothing is cut off. A Codex plugin cannot
carry custom agents, so the 11 agents are linked into
`${CODEX_HOME:-~/.codex}/agents/` as `prp-core__<agent>.toml`, each with its
model, reasoning effort, and a read-only sandbox. `ONLY=agents` or
`ONLY=plugins` installs one half (`ONLY=skills|agents` with `PROJECT`).

Codex copies an installed plugin into its own cache, so rerun `make install-codex`
after `git pull`. If you added `NanoBoom/skills` as a Codex marketplace before,
remove it first (`codex plugin marketplace remove nanoboom`): that route is not
supported, because Codex then reads the Claude Code plugin unchanged. Do not mix
in copies from `npx skills` either, or Codex lists those skills twice.

### Pi

```bash
git clone https://github.com/NanoBoom/skills && cd skills
make install-pi
```

This links skills, agents, prompt templates, and extensions into `~/.pi/agent/`
(or `$PI_CODING_AGENT_DIR`). Pi core has no subagents; the agents load with Pi's
reference `subagent` extension or a compatible one. Agents run on Anthropic
models mapped from their Claude aliases; edit `MODEL_ALIASES` in
[`tools/adapters/capabilities.py`](./tools/adapters/capabilities.py) and rerun
for another provider.

### Choose plugins, or install into a project

Both `make install-codex` and `make install-pi` take these variables, and
`make uninstall-<harness>` takes `PLUGINS` and `PROJECT`:

```bash
make install-pi PLUGINS=github-project               # only some plugins (default: all)
make install-pi PROJECT=/abs/path/to/app             # into the project's .pi/, not ~/.pi/agent
make install-codex PROJECT=/abs/path/to/app COPY=1   # real copies the project can commit
make uninstall-pi PROJECT=/abs/path/to/app
```

Into a project, Codex gets skills and agents in `<project>/.codex/`, but no
plugin, so no Codex hooks or MCP servers. Both tools load a project's files
only after you trust the project. Without `COPY=1` the project gets symlinks
into your clone, which work only on your machine.
[docs/harnesses.md](./docs/harnesses.md#install-options) has the details.

### `npx skills add` (any Agent Skills harness)

This copies skills into any harness that understands Agent Skills, with no
marketplace and no clone:

```bash
npx skills@latest add NanoBoom/skills            # pick interactively
npx skills@latest add NanoBoom/skills --list     # see what is there first
npx skills@latest add NanoBoom/skills --skill github-project-manage
npx skills@latest add NanoBoom/skills --skill prp-technical-writing --global
```

Useful flags: `--global` installs at user level instead of into the current
project, `--agent '*'` targets every detected harness, `--copy` writes real files
instead of symlinks, and `-y` skips the prompts. Later, `npx skills list`,
`npx skills update`, and `npx skills remove` manage what you took.

It copies `SKILL.md` files and their directories and nothing else, so it does
**not** bring the agents or the Stop hooks. The three `github-project` skills are
self-contained by design and lose nothing. Most `prp-core` skills dispatch
subagents and degrade: the skill loads, but the work it delegates has nowhere to
go. Use this route for a single skill; for the workflow, use your harness's
route above.

## Requirements

- One of the harnesses above
- Git configured; GitHub CLI (`gh`) for PR/issue operations
- [`uv`](https://docs.astral.sh/uv/), which runs the bundled `prp-loop` state machine (`plugins/prp-core/skills/prp-loop/scripts/prp_loop.py`), the `prp-worktree` script, and the `make` install targets

## Artifacts

Artifacts and runtime state are written to the target project's PRP store, `.prp/` in the checkout root:

```
<checkout-root>/.prp/
├── .gitignore         # holds `*`, so the store ignores itself and its contents
├── prds/              # product requirement documents
├── plans/             # implementation plans
├── research/          # codebase research
├── research-plans/    # multi-agent research plans
├── reports/           # implementation reports
├── reviews/           # human-readable PR reviews
├── debug/             # root-cause analysis reports
├── orchestration/     # parallel-workstream run files
└── state/             # loop state, logs, and hook sentinels
```

The root is resolved with `git rev-parse --show-toplevel`, so every worktree gets its own store next to the code it is working on. Outside a repository the store lands in the current directory. A worktree therefore does not see the main checkout's PRDs, plans, or reports; copy the ones you need into it, or point both at one store with `PRP_DIR`.

The store is never committed: it creates a `.gitignore` containing `*`, which ignores its contents and the file itself, so nothing appears in `git status` and no `git add -A` can sweep it in. The store moves with the repository and needs no re-keying, but a deleted checkout takes its artifacts with it, and removing a worktree is the common way that happens. Copy `.prp/` out first if you want them to survive.

Set `PRP_DIR` to put the store somewhere else: back under `$HOME` on a machine where the repository must stay pristine, or at the main checkout's `.prp/` so several worktrees share one store. `/prp-orchestrate` does exactly that, pinning every workstream owner to the orchestrator's store so its artifacts outlive the worktree.

## PRP methodology

**PRP = PRD + curated codebase intelligence + agent/runbook.** Core principles:

1. **Context is King**: include (or reference) all the context the agent needs
2. **Validation loops**: executable gates the AI runs and fixes until green
3. **Information dense**: real patterns, file:line, commands; no filler
4. **Progressive success**: start small, validate, then enhance

Plans are durable implementation contracts. Implementation results, validation, deviations, commits, and PR delivery live in the matching report so later contexts can recover the current truth without mutating or archiving the plan.

## Troubleshooting

**Plugin not loading**: `/plugin uninstall prp-core@nanoboom` then re-install and restart.

**Skills not found**: ensure Claude Code restarted after install; check `/help` and `/plugin`.

**Two copies of every skill**: you have both this plugin and the upstream
`prp-core@prp-marketplace` installed. Uninstall one.

## Contributing

[AGENTS.md](./AGENTS.md) is the contributor contract: the layout, the invariants,
how to add a skill, an agent, a plugin, or a harness, and how to verify a change.
`make help` lists the maintainer targets.

## License

MIT. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE).

## Support

- Issues: https://github.com/NanoBoom/skills/issues
- Upstream project: https://github.com/Wirasm/PRPs-agentic-eng
