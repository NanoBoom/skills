# github-project

Three skills for running software requirements as GitHub Issues, with a GitHub
Project used only as the ordering, ownership, priority, and status view. They
talk to GitHub through the `gh` CLI and nothing else.

## This bucket does not ship in the plugin

It appears in none of [`.claude-plugin/plugin.json`](../../.claude-plugin/plugin.json),
the [top-level `README.md`](../../README.md), or
[`skills.sh.json`](../../skills.sh.json), and that absence is deliberate.
[`scripts/check-skills.mjs`](../../scripts/check-skills.mjs) treats `prp-core` as
the single promoted bucket and fails on any registration outside it. Registering
these three skills would turn a green checker red. See the Layout section of
[CLAUDE.md](../../CLAUDE.md).

## Every skill here is self-contained

No skill in this bucket dispatches a plugin subagent, reads a plugin root path,
or reads a file outside its own directory. Unlike the `prp-core` skills, which
lose their subagents when taken through `npx skills`, a single `SKILL.md` copied
out of this repository still works. The runtime source of truth for shared
parameters is a file in the target repository, `.github/github-project.yml`, not
a file in this one.

## Install

- `npx skills add NanoBoom/skills`. These three appear under the `General`
  heading rather than `Prp Core`, because that heading is the plugin name and
  these skills are not in the plugin. To install one directly:
  `npx skills add NanoBoom/skills --skill github-project-manage`.
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
