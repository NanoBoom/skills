# prp-core

The PRP workflow plugin. Its skills are in [`skills/`](./skills), its 11
specialist agents in [`agents/`](./agents), and its two Claude Code Stop hooks
in [`hooks/`](./hooks).

Most of these skills dispatch the `prp-core:<agent>` subagents in
[`agents/`](./agents). Those agents exist only when the plugin is installed,
so a skill taken through `npx skills` alone will not have them.

## Product and planning

- **[prp-prd](./skills/prp-prd/SKILL.md)**: interactive PRD generator, problem-first and hypothesis-driven.
- **[prp-prd-update](./skills/prp-prd-update/SKILL.md)**: maintains PRD phase status and artifact links as work lands.
- **[prp-plan](./skills/prp-plan/SKILL.md)**: turns a PRD, issue, or description into an implementation-ready plan backed by codebase evidence.
- **[prp-diagram](./skills/prp-diagram/SKILL.md)**: mermaid-only visual supplement for a plan: data model, architecture, and flow.
- **[prp-spike](./skills/prp-spike/SKILL.md)**: settles a feasibility question by building the smallest throwaway artifact that could falsify it.
- **[prp-research-team](./skills/prp-research-team/SKILL.md)**: composes a dynamic research team and an executable research plan.
- **[prp-codebase-question](./skills/prp-codebase-question/SKILL.md)**: answers how the codebase works today, using parallel agents. Documents what exists, not what should change.

## Delivery

- **[prp-issue](./skills/prp-issue/SKILL.md)**: owns one workstream end to end, from issue to reviewed PR with green CI.
- **[prp-implement](./skills/prp-implement/SKILL.md)**: executes an existing plan and corrects reviewed or failing-CI pull requests.
- **[prp-commit](./skills/prp-commit/SKILL.md)**: creates Git commits for completed work.
- **[prp-pr](./skills/prp-pr/SKILL.md)**: creates and opens GitHub pull requests.
- **[prp-loop](./skills/prp-loop/SKILL.md)**: drives the resumable pipeline from this session, one fresh subagent per stage.
- **[prp-deliver](./skills/prp-deliver/SKILL.md)**: experimental. Only runs when invoked explicitly.

## Review and triage

- **[prp-review](./skills/prp-review/SKILL.md)**: reviews a PR through specialist agents, verifies corrections, and posts the result.
- **[prp-debug](./skills/prp-debug/SKILL.md)**: diagnoses a bug or regression and publishes the evidence-backed root cause to GitHub.
- **[prp-maintainer-triage](./skills/prp-maintainer-triage/SKILL.md)**: user-invoked. Fast disposition on a contributor PR or reported issue.
- **[prp-issue-contract](./skills/prp-issue-contract/SKILL.md)**: creates GitHub issues from a conversation and checks an issue is agent-ready before automation starts.

## Orchestration and workspace

- **[prp-orchestrate](./skills/prp-orchestrate/SKILL.md)**: runs parallel workstreams in isolated worktrees, holding human and merge gates.
- **[prp-worktree](./skills/prp-worktree/SKILL.md)**: create, list, and tear down worktrees under `.worktrees/` via a bundled CLI.
- **[prp-worklist](./skills/prp-worklist/SKILL.md)**: user-invoked. Renders a repository's open work so the maintainer can pick what is next.
- **[agent-policy](./skills/agent-policy/SKILL.md)**: picks the model and effort for every agent at launch by task type, to save tokens, with lookup tables for Claude Code and Codex.

## Authoring

- **[prp-meta-skill](./skills/prp-meta-skill/SKILL.md)**: authors, refactors, and consolidates Agent Skills PRP-style.
- **[prp-technical-writing](./skills/prp-technical-writing/SKILL.md)**: writes and edits developer documentation that is easy to act on and hard to misread.
- **[prp-bro](./skills/prp-bro/SKILL.md)**: restates the previous response in plain language, with no jargon.
