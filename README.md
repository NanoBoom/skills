# PRP Core

Complete PRP (Product Requirement Prompt) workflow automation for Claude Code,
packaged as **Agent Skills**.

[中文文档](./README.zh-CN.md)

This repository is also the `nanoboom` marketplace, and it ships two plugins.
**`prp-core`** is the PRP workflow and everything below is about it.
**`github-project`** is a smaller, independent plugin for running requirements
as GitHub Issues; it has its own [README](./skills/github-project/README.md) and
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

> **Claude Code is the supported harness.** Most skills dispatch the
> `prp-core:<agent>` subagents in [`agents/`](./agents), and one uses the Stop
> hook in [`hooks/`](./hooks). Neither travels through `npx skills`, which copies
> `SKILL.md` files only. Install the plugin to get the whole thing.

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
| `/prp-core:prp-loop` | **Detached** cyclic pipeline: plan → implement → PR → review, looping review→fix until clean. `--until implement` stops after a green implementation and open PR |
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
in the [bucket README](./skills/github-project/README.md).

| Skill | Description |
|-------|-------------|
| `/github-project:github-project-setup` | Inspect, initialize, or repair the Project, its `Status` and `Priority` fields, the Board and Backlog views, the built-in automations, the Issue template, `.github/github-project.yml`, and the language its Issue text is written in |
| `/github-project:github-project-manage` | Run the Issue lifecycle across eleven modes, from drafting a requirement to closing it, keeping each Issue's Project item in step |
| `/github-project:github-project-audit` | Read-only audit of Issue quality and Issue-to-Project consistency against a 28-rule catalog with stable rule IDs |

## Agents

Specialized, advisory agents used by the review and planning skills. They are
report-only by design: they analyze and report findings but never modify files or
commit (enforced by their prompts, not by a `tools:` allowlist).

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
stage of `/prp-core:prp-issue`, or manually via the Task tool.

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

The plugin ships one Stop hook, `hooks/prp-research-team-stop.sh`, which
validates `prp-research-team` output. The skill writes its plan path to a
sentinel file in `~/.prp/<project-key>/state/prp-research-team.state`; on Stop,
the hook checks the plan for the six required sections and, if any are missing,
blocks completion once with the list of what is absent. It cleans up the sentinel
on success, ignores stale sentinels (older than 2 hours), and never blocks twice
in a row. Note: the hook ships only with the plugin. If you copy the skill into
`.claude/skills/` directly, this validation does not run.

## Workflows

### Large features: PRD → plan → implement

```
/prp-core:prp-prd "user authentication system"
    ↓  creates a PRD with an Implementation Phases table
/prp-core:prp-plan ~/.prp/<project-key>/prds/user-auth.prd.md
    ↓  auto-selects the next pending phase, creates a plan
/prp-core:prp-implement ~/.prp/<project-key>/plans/user-auth-phase-1.plan.md
    ↓  executes, validates, commits, opens the PR, and links delivery to the PRD
repeat /prp-core:prp-plan for the next phase
```

### Medium features: plan → implement

```
/prp-core:prp-plan "add pagination to the API"
/prp-core:prp-implement ~/.prp/<project-key>/plans/add-pagination.plan.md
```

### Hands-off: the autonomous loop

```
/prp-core:prp-loop "add pagination to the API"
    ↓  plan → implement (loop to green) → PR → review → fix → re-review → clean
```

### Input to a reviewed PR

```
/prp-core:prp-issue 123
    ↓  plan → implement → PR → review → correct → re-review → green CI
```

## Installation

There are two ways in, and they do not deliver the same thing.

| | Claude Code plugin | `npx skills add` |
|---|---|---|
| What lands | skills, the 11 agents, the Stop hook | `SKILL.md` files and their supporting directories |
| Invocation | `/prp-core:<name>`, `/github-project:<name>`, plus automatic loading | whatever your harness does with an Agent Skill |
| Unit of install | one plugin at a time, `prp-core` and `github-project` separately | one flat set of 26 skills, or the ones you name |
| Updates | `/plugin update` against the marketplace | `npx skills update` |
| Best for | the PRP workflow as a whole | one self-contained skill, or a harness that is not Claude Code |

If you use Claude Code, install the plugin. Reach for `npx skills` when you want
a single skill somewhere else.

### Claude Code plugin (recommended)

Register the marketplace once, then install either plugin from it. The two are
independent and neither requires the other.

```
/plugin marketplace add NanoBoom/skills
/plugin install prp-core@nanoboom
/plugin install github-project@nanoboom   # optional, independent
```

Restart Claude Code so the skills, agents, and hook load.

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

`details` prints the component inventory: 23 skills, 11 agents, 1 hook for
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

To load a tree for one session without installing anything, use
`claude --plugin-dir /absolute/path/to/skills`. For the `github-project` plugin
the directory is the bucket, `--plugin-dir /absolute/path/to/skills/skills/github-project`.

### `npx skills add` (any Agent Skills harness)

This copies skills into a harness that understands Agent Skills. No marketplace,
no Claude Code required.

```bash
npx skills@latest add NanoBoom/skills            # pick interactively
npx skills@latest add NanoBoom/skills --list     # see what is there first
npx skills@latest add NanoBoom/skills --all      # every skill, every agent, no prompts
```

Take a single skill, which is the case this path is actually good at:

```bash
npx skills@latest add NanoBoom/skills --skill github-project-manage
npx skills@latest add NanoBoom/skills --skill prp-technical-writing --global
```

Useful flags: `--global` installs at user level instead of into the current
project, `--agent '*'` targets every detected harness, `--copy` writes real files
instead of symlinks, and `-y` skips the prompts. Later, `npx skills list`,
`npx skills update`, and `npx skills remove` manage what you took.

#### What you get and what you do not

`npx skills` discovers skills by scanning `skills/`, so it finds all 26 across
both buckets and ignores the plugin manifests. It copies `SKILL.md` files and
their supporting directories, and nothing else in this repository. It does
**not** bring the `prp-core:<agent>` subagents in [`agents/`](./agents) or the
Stop hook in [`hooks/`](./hooks).

So:

- The three `github-project` skills are self-contained by design. They talk to
  GitHub through the `gh` CLI and read nothing outside their own directory, so
  they lose nothing here.
- Most `prp-core` skills dispatch subagents or read `${CLAUDE_PLUGIN_ROOT}`.
  Taken this way they degrade: the skill still loads, but the work it delegates
  has nowhere to go. Use this path for an individual skill, not for the workflow
  as a whole.

Skills arrive under a `General` heading rather than their bucket name. The
heading comes from the root `.claude-plugin/plugin.json` and is cosmetic.

#### Symlink a working tree

For maintainers, [`scripts/link-skills.sh`](./scripts/link-skills.sh) symlinks
every skill outside `deprecated/` into `~/.claude/skills` and `~/.agents/skills`,
so edits in the tree take effect immediately.

## Requirements

- Claude Code installed
- Git configured; GitHub CLI (`gh`) for PR/issue operations
- [`uv`](https://docs.astral.sh/uv/), which runs the bundled `prp-loop` orchestrator (`skills/prp-core/prp-loop/scripts/prp_loop.py`)

## Artifacts

Artifacts and runtime state are written outside the repository to the target project's shared PRP store:

```
~/.prp/<project-key>/
├── project.json       # canonical project path and name
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

`<project-key>` is `<slug>-<hash8>`, where the slug comes from the canonical main-checkout basename and `hash8` is the first eight characters of Git's blob hash of that checkout path. This makes every linked worktree resolve to the same store. Set `PRP_HOME` to override the default `~/.prp` root.

If a repository moves, its path-derived key changes. Move the old store to the newly derived key and update `path` in `project.json`; PRP never deletes or auto-adopts the old store.

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

[CLAUDE.md](./CLAUDE.md) is the contributor contract: the layout, the invariants,
how to add a skill, and how to verify a change.

## License

MIT. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE).

## Support

- Issues: https://github.com/NanoBoom/skills/issues
- Upstream project: https://github.com/Wirasm/PRPs-agentic-eng
