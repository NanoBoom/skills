# github-project

Three skills for running software requirements as GitHub Issues, with a GitHub
Project used only as the ordering, ownership, priority, and status view. They
talk to GitHub through the `gh` CLI and nothing else.

## This bucket is its own plugin

This directory is the root of the `github-project` plugin: it carries its own
[`.claude-plugin/plugin.json`](./.claude-plugin/plugin.json), and
[the marketplace](../../.claude-plugin/marketplace.json) points an entry at it
with `"source": "./skills/github-project"`. It installs and updates separately
from `prp-core`, and neither depends on the other. Inside Claude Code the skills
are scoped to this plugin, so they are invoked as
`/github-project:github-project-manage`.

## Every skill here is self-contained

No skill in this bucket dispatches a subagent, reads a plugin root path, or
reads a file outside its own directory. Unlike the `prp-core` skills, which lose
their subagents when taken through `npx skills`, a single `SKILL.md` copied out
of this repository still works.
[`scripts/check-skills.mjs`](../../scripts/check-skills.mjs) enforces this: a
`${CLAUDE_PLUGIN_ROOT}` reference or a cross-plugin `prp-core:<agent>` dispatch
in any skill here fails the check. The runtime source of truth for shared
parameters is a file in the target repository, `.github/github-project.yml`, not
a file in this one.

## Install

- In Claude Code:

  ```
  /plugin marketplace add NanoBoom/skills
  /plugin install github-project@nanoboom
  ```

- For any other Agent Skills harness: `npx skills add NanoBoom/skills`, which
  finds these three alongside the `prp-core` ones. To take a single skill:
  `npx skills add NanoBoom/skills --skill github-project-manage`.

  They are listed under the `General` heading rather than `GitHub Project`.
  `npx skills` discovers skills by scanning `skills/` and takes its headings
  from the repository's root `.claude-plugin/plugin.json`; it does not read the
  nested manifest here. The heading is cosmetic and the skills install either
  way.
- Or run [`scripts/link-skills.sh`](../../scripts/link-skills.sh), which
  symlinks every skill in this repository into `~/.claude/skills` and
  `~/.agents/skills`.

## Requirements

The `gh` CLI, authenticated against the target host with a token that carries
the Projects scope. If a Project call is rejected, run
`gh auth refresh -s project,read:project`. Classic Projects are not supported;
these skills target Projects v2 only.

## Skills

- **[github-project-setup](./github-project-setup/SKILL.md)**: inspects, initializes, or repairs the Project fields, views, built-in automations, Issue template, and config file.
- **[github-project-manage](./github-project-manage/SKILL.md)**: runs the Issue lifecycle from drafting a requirement to closing it, and keeps the Project item in step.
- **[github-project-audit](./github-project-audit/SKILL.md)**: read-only audit of Issue quality and Issue-to-Project consistency against a stable rule catalog.
