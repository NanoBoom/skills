# prp-core

The promoted bucket. Every skill here ships in the `prp-core` plugin and is
listed in [`.claude-plugin/plugin.json`](../../.claude-plugin/plugin.json)'s
`skills` array.

Most of these skills dispatch the `prp-core:<agent>` subagents in
[`agents/`](../../agents). Those agents exist only when the plugin is installed,
so a skill taken through `npx skills` alone will not have them.

## Product and planning

- **[prp-prd](./prp-prd/SKILL.md)**: interactive PRD generator, problem-first and hypothesis-driven.
- **[prp-prd-update](./prp-prd-update/SKILL.md)**: maintains PRD phase status and artifact links as work lands.
- **[prp-plan](./prp-plan/SKILL.md)**: turns a PRD, issue, or description into an implementation-ready plan backed by codebase evidence.
- **[prp-diagram](./prp-diagram/SKILL.md)**: mermaid-only visual supplement for a plan: data model, architecture, and flow.
- **[prp-spike](./prp-spike/SKILL.md)**: settles a feasibility question by building the smallest throwaway artifact that could falsify it.
- **[prp-research-team](./prp-research-team/SKILL.md)**: composes a dynamic research team and an executable research plan.
- **[prp-codebase-question](./prp-codebase-question/SKILL.md)**: answers how the codebase works today, using parallel agents. Documents what exists, not what should change.

## Delivery

- **[prp-issue](./prp-issue/SKILL.md)**: owns one workstream end to end, from issue to reviewed PR with green CI.
- **[prp-implement](./prp-implement/SKILL.md)**: executes an existing plan and corrects reviewed or failing-CI pull requests.
- **[prp-commit](./prp-commit/SKILL.md)**: creates Git commits for completed work.
- **[prp-pr](./prp-pr/SKILL.md)**: creates and opens GitHub pull requests.
- **[prp-loop](./prp-loop/SKILL.md)**: runs the detached, resumable pipeline in fresh headless CLI sessions.
- **[prp-deliver](./prp-deliver/SKILL.md)**: experimental. Only runs when invoked explicitly.

## Review and triage

- **[prp-review](./prp-review/SKILL.md)**: reviews a PR through specialist agents, verifies corrections, and posts the result.
- **[prp-debug](./prp-debug/SKILL.md)**: diagnoses a bug or regression and publishes the evidence-backed root cause to GitHub.
- **[prp-maintainer-triage](./prp-maintainer-triage/SKILL.md)**: user-invoked. Fast disposition on a contributor PR or reported issue.
- **[prp-issue-contract](./prp-issue-contract/SKILL.md)**: creates GitHub issues from a conversation and checks an issue is agent-ready before automation starts.

## Orchestration and workspace

- **[prp-orchestrate](./prp-orchestrate/SKILL.md)**: runs parallel workstreams in isolated worktrees, holding human and merge gates.
- **[prp-worktree](./prp-worktree/SKILL.md)**: create, list, and tear down worktrees under `.worktrees/` via a bundled CLI.
- **[prp-worklist](./prp-worklist/SKILL.md)**: user-invoked. Renders a repository's open work so the maintainer can pick what is next.

## Authoring

- **[prp-meta-skill](./prp-meta-skill/SKILL.md)**: authors, refactors, and consolidates Agent Skills PRP-style.
- **[prp-technical-writing](./prp-technical-writing/SKILL.md)**: writes and edits developer documentation that is easy to act on and hard to misread.
- **[prp-bro](./prp-bro/SKILL.md)**: restates the previous response in plain language, with no jargon.
