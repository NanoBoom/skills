# 0001: The repository root is the plugin

Date: 2026-09-11
Status: Accepted

## Context

This repository started as a multi-plugin marketplace: `.claude-plugin/marketplace.json`
at the root, and each plugin under `skills/<plugin>/` with its own `skills/`,
`agents/`, and `hooks/`. The first real plugin to land, `prp-core`, made three
problems concrete.

Skill files ended up at `skills/prp-core/skills/prp-plan/SKILL.md`. The repeated
`skills/` segment carries no information and reads as a mistake.

The plugin was a fork of an existing one, and its 23 skills dispatch subagents by
scoped name (`prp-core:codebase-explorer` and 10 others, 36 call sites). Those
names resolve only when the plugin is named `prp-core`, which pins the name and
removes most of the reason to keep the extra nesting layer flexible.

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin root, not the repository root.
With plugins nested under `skills/`, every path built from it had a repository
layout baked into it that no longer matched the tree it was written against.

## Decision

The repository root is the plugin. `.claude-plugin/plugin.json` sits at the root,
`.claude-plugin/marketplace.json` declares a single plugin with `"source": "./"`,
and `agents/`, `hooks/`, and `skills/` are the plugin's own component
directories. Skills live at `skills/<bucket>/<name>/SKILL.md`, with `prp-core` as
the promoted bucket.

There is no `plugins/` directory and there will not be one. A second plugin gets
its own repository.

This follows [nano-claude-code-plugins](https://github.com/NanoBoom/nano-claude-code-plugins),
which reached the same conclusion for the `boom` plugin.

## Consequences

`${CLAUDE_PLUGIN_ROOT}` now resolves to the repository root, so a path written
against the working tree is valid inside the plugin cache. One tree serves three
consumers without translation: the Claude Code plugin, its own single-plugin
marketplace, and `npx skills`.

Claude Code does not scan bucket folders, so every skill must be listed
explicitly in `plugin.json`'s `skills` array. A skill missing from that array
does not load, and nothing else reports it. `scripts/check-skills.mjs` exists to
catch exactly this.

Adding a second plugin means a new repository rather than a new directory. That
is the cost, and it is accepted.
