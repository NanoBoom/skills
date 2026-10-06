# 0002: Plugins live under plugins/, and adapters serve other harnesses

Date: 2026-10-05
Status: Accepted. Supersedes [0001](./0001-repository-root-is-the-plugin.md).

## Context

[0001](./0001-repository-root-is-the-plugin.md) made the repository root the
`prp-core` plugin and ruled out a `plugins/` directory. Two things changed.

A second plugin, `github-project`, arrived anyway. It became a plugin rooted
at its own bucket, `skills/github-project/`, so the repository ended up with
two plugin layouts and a checker that had to know which was which.

Users also run Codex and Pi. `npx skills` copies `SKILL.md` directories only,
so in those harnesses the `prp-core` skills lost their subagents. Codex reads
custom agents from TOML files, Pi from Markdown files with different
frontmatter, and neither resolves the scoped name `prp-core:<agent>` the skills
dispatch. Hooks and MCP servers differ more: Codex takes hooks in a file shaped
like Claude Code's but runs them under its own events and trust rules, and Pi
runs both as TypeScript extensions.

[wshobson/agents](https://github.com/wshobson/agents) solves the same problem
for about ninety plugins. It keeps one source tree in the Claude Code plugin
format under `plugins/<name>/`, and per-harness adapters generate what each
other harness needs.

## Decision

Every plugin lives at `plugins/<name>/` in the Claude Code plugin format,
with `skills/`, `agents/`, and `hooks/` at the plugin root.
`.claude-plugin/marketplace.json` points each entry at `./plugins/<name>`.
Plugin manifests carry no `skills` array; Claude Code discovers `skills/`.

Python adapters under `tools/adapters/` read that source and write each other
harness's format. `tools/generate.py`, `tools/validate.py`, and
`tools/install.py` drive them, through `make`. Generated agent names are
`<plugin>__<agent>`, and adapters rewrite `<plugin>:<agent>` in generated
skills to match.

Hooks and MCP servers are not translated. A plugin that wants them in another
harness writes that harness's version under `plugins/<name>/harness/<harness>/`,
and the adapters copy it without reading it: `harness/codex/` over the root of
the generated Codex plugin, `harness/pi/extensions/` into Pi's extensions.

Claude Code installs from the marketplace. Codex and Pi install from a clone
through `make install-<harness>`; nothing generated is committed. Codex keeps
user hooks and MCP servers in single files, so `make install-codex` registers
the generated `build/codex/` as a local Codex marketplace and installs each
plugin from it with the Codex CLI, and links the agents, which a Codex plugin
cannot carry. `make install-pi` links everything. Either installs all plugins or
some, for the user or into one project. A Codex plugin cannot be enabled for one
project, so a project install gives Codex skills and agents only, without its
hooks or MCP servers. Cursor and OpenCode are not supported.

## Consequences

`${CLAUDE_PLUGIN_ROOT}` now resolves to `plugins/<name>/`, so paths built from
it lose the bucket segment. Skills no longer use it at all: no other harness
resolves it, so a skill names "this skill's directory" instead. Only the
hooks keep it.

The plugin cache no longer carries the repository's README, tooling, and
other plugins, because the install root is the plugin directory.

Contributors need uv to run the checks. The Node checker is gone.

Codex and Pi users need a clone, `uv`, and `make`, and Codex users the Codex
CLI. In exchange every skill they get has its dispatch names rewritten, and
Codex skills are split to fit its prompt limit. A plugin author who wants hooks
or MCP servers outside Claude Code maintains one version per harness.

Codex can still read `.claude-plugin/marketplace.json` if someone adds this
repository as a Codex marketplace. That route installs the Claude Code plugin
unchanged and is documented as unsupported.
