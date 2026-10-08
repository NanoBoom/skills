# Contributor contract

This repository is the `nanoboom` marketplace. It publishes two plugins,
`prp-core` and `github-project`, to Claude Code, Codex, and Pi, and it is an
Agent Skills repository for `npx skills`. `CLAUDE.md` is a
symlink to this file.

`prp-core` is a fork of the plugin of the same name in
[Wirasm/PRPs-agentic-eng](https://github.com/Wirasm/PRPs-agentic-eng). The
harness adapters follow [wshobson/agents](https://github.com/wshobson/agents).
See [NOTICE](./NOTICE) for both, and [ADR 0002](./.agents/adr/0002-plugins-directory-and-harness-adapters.md)
for why the tree looks like this.

## Layout

```
plugins/<plugin>/              source of truth, Claude Code plugin format
  .claude-plugin/plugin.json   hand-written manifest
  skills/<skill>/SKILL.md      plus references/, templates/, workflows/, scripts/
  agents/<agent>.md            prp-core only
  commands/<command>.md        none yet
  hooks/hooks.json             Claude Code hooks; prp-core's Stop and prompt hooks
  .mcp.json                    Claude Code MCP servers; none yet
  harness/codex/               Codex hooks and MCP servers, Codex format; none yet
  harness/pi/extensions/       Pi extensions; none yet
  README.md
.claude-plugin/marketplace.json   hand-written; one entry per plugin
tools/                            Python adapters, generate, validate, install
docs/harnesses.md                 what each harness gets, and what it loses
```

Codex and Pi install from a clone. `make generate` writes their trees into the
gitignored `build/codex/` and `build/pi/`, outside `.codex/` and `.pi/`, so
running those tools in this checkout does not load them as project
configuration. Nothing generated is committed. Never edit a generated file;
change the source and run `make generate`.

## Invariants

- **Plugin names do not change.** The plugin name equals its directory name,
  and skills dispatch agents by the scoped name `prp-core:<agent>`. Renaming
  `prp-core` silently breaks every dispatch.
- **No `skills` array in a `plugin.json`.** Claude Code discovers `skills/`.
- **Skill names are unique across plugins.** `npx skills` and the generated
  trees install by bare name.
- **No `${CLAUDE_PLUGIN_ROOT}/` in a skill.** Only Claude Code resolves it.
  Name "this skill's directory" instead, as `prp-loop` and `prp-worktree` do.
  Hooks may use it.
- **`github-project` stays self-contained:** no agents, no hooks, no
  dispatch into another plugin. Its README promises that a single copied
  `SKILL.md` works. The list is `SELF_CONTAINED` in `tools/validate.py`.
- **Every promoted skill** has a line in its plugin `README.md`, a row in the
  top-level [README.md](./README.md), and a place in a group in
  [skills.sh.json](./skills.sh.json).
- **Versions agree.** Each `plugin.json` `version` equals its entry in
  `.claude-plugin/marketplace.json`. The top-level marketplace `version` is
  the repository release.
- **`harness/` is copied, never read.** Adapters convert skills, agents, and
  commands, but not hooks or MCP servers. `harness/<harness>/` holds a
  harness's own version of those, and only `codex` and `pi` exist.

`tools/validate.py` enforces all of these, and checks every generated artifact
in a temporary directory.

## Adding a skill

1. `cd plugins/<plugin>/skills && npx skills init <name>`. `name` equals the
   directory name; `description` says what the skill does and when to use it. Frontmatter is
   YAML, parsed with PyYAML: quote a value that holds `: ` or starts with a
   YAML indicator, or `make validate` reports the line that does not parse.
2. Keep `SKILL.md` under 500 lines. Codex truncates a skill prompt at 8000
   bytes; the Codex adapter moves the tail of a longer one into
   `references/codex-overflow.md` in the generated copy, so put what the
   model must read first near the top.
3. In `prp-core`, dispatch agents as `prp-core:<agent>`. The adapters rewrite
   the name for each harness. `npx skills` users get the skill without that
   rewrite, so say what to do when the agent is missing. A `prp-core` skill
   that reports to the user names the `response-policy` skill at its report
   step, as the existing skills do.
4. Promote it: plugin `README.md`, top-level `README.md`, `skills.sh.json`.
5. Bump `version` in the plugin's `plugin.json` and its marketplace entry.
6. `make generate && make check`.

## Adding an agent

`plugins/prp-core/agents/<name>.md` with `name`, `description`, `model`
(`fable`, `opus`, `sonnet`, `haiku`, or `inherit`), and optionally `effort` and
`disallowedTools`. The adapters map the model alias per harness in
`tools/adapters/capabilities.py`, and treat an agent that cannot use `Write`
and `Edit` as read-only. Then `make generate && make check`.

## Adding a command, hooks, or MCP servers

A command goes where Claude Code expects it, `commands/<name>.md` with a
`description`, and every adapter converts it. Its name must not match any skill
name, because Codex installs commands as skills.

Hooks and MCP servers are written once per harness, in that harness's format,
and copied unread:

- Claude Code: `hooks/hooks.json` and `.mcp.json` at the plugin root.
- Codex: `harness/codex/hooks/hooks.json` and `harness/codex/.mcp.json`, plus
  any script they run. `harness/codex/` becomes the Codex plugin root, so
  `${CLAUDE_PLUGIN_ROOT}/hooks/<script>` names `harness/codex/hooks/<script>`.
- Pi: one extension per hook or MCP client in `harness/pi/extensions/`, a
  `.ts` file or a directory with `index.ts`, importing nothing outside itself.

[docs/harnesses.md](./docs/harnesses.md#components) has the details. A harness
without its directory gets none of them, and `make generate` prints a `note`
line saying so. Then `make generate && make check`.

## Adding a plugin

A plugin carries every component it needs. `make install-<harness> PLUGINS=...`
installs any subset, so a plugin must not rely on another one being installed.

1. Create `plugins/<name>/.claude-plugin/plugin.json`, `skills/`, and
   `README.md`.
2. Add an entry to `.claude-plugin/marketplace.json` with
   `"source": "./plugins/<name>"` and a matching `version`.
3. If it must stay self-contained, add it to `SELF_CONTAINED`.
4. Promote its skills, then `make generate && make check`.

## Adding a harness

Write `tools/adapters/<harness>.py`, a `HarnessAdapter` that declares its
names, its user and project configuration directories, `install_kinds`, and
`check_native` for its `harness/<harness>/` rules, and add it to `ADAPTERS` in
`tools/adapters/__init__.py`; generate, validate, and install read everything
from there. Add its model IDs to `MODEL_ALIASES` in `capabilities.py` and a
section to `docs/harnesses.md`. Cover it in `tools/tests/test_components.py`, which runs
the `kitchen-sink` fixture plugin, one of every component, through every
adapter and the installer.

## Verification

```bash
make check                     # validate + pytest + ruff, as CI runs them
npx skills add . --list        # Found 28 skills
claude plugin validate .
claude plugin validate plugins/prp-core/.claude-plugin/plugin.json
claude plugin validate plugins/github-project/.claude-plugin/plugin.json
claude -p "hi" --plugin-dir plugins/prp-core --debug-file /tmp/dbg.log
grep -E "Loaded [0-9]+ (agents|skills) from plugin prp-core" /tmp/dbg.log
```

`make validate` reports `OK 28 skill(s) and 11 agent(s) in 2 plugin(s), 2 generated
harness(es), 1 warning(s)`; the warning is the length of `prp-research-team`. The
debug log shows 11 agents and 25 skills for `prp-core`; `--plugin-dir
plugins/github-project` shows 3 skills. Run `npx skills add . --list` from a
clean tree or straight from GitHub.

To exercise an install end to end without pushing, point a marketplace at the
working tree. For Claude Code this rewrites the `nanoboom` entry in user
settings, so restore it afterwards. The Codex and Pi lines use throwaway
directories and touch nothing of yours.

```bash
claude plugin marketplace add "$PWD"
claude plugin install prp-core@nanoboom --scope local -y
claude plugin uninstall prp-core@nanoboom --scope local
claude plugin marketplace add NanoBoom/skills

mkdir -p /tmp/cx && CODEX_HOME=/tmp/cx make install-codex
CODEX_HOME=/tmp/cx codex plugin list
PI_CODING_AGENT_DIR=/tmp/pi make install-pi
mkdir -p /tmp/app && make install-pi PROJECT=/tmp/app COPY=1 PLUGINS=github-project
```

`make test` also installs the `kitchen-sink` fixture into a throwaway
`CODEX_HOME` with the real Codex CLI when `codex` is on `PATH`. Every other test
fails if it reaches the real CLI, and runs with `CODEX_HOME` and
`PI_CODING_AGENT_DIR` pointing into a temporary directory; a test that needs the
CLI takes the `real_codex` fixture and sets its own `CODEX_HOME`.

## Upstream

`plugins/prp-core/.claude-plugin/plugin.json`'s `metadata.upstreamCommit`
records the commit this fork is based on. To pull upstream changes, diff that
commit against upstream `main` under `plugins/prp-core/`, which now has the
same layout as this repository, apply what you want, and update
`metadata.upstreamCommit`.

## Prose

All text in this repository is English, except `README.zh-CN.md`. No em
dashes in new prose; text carried over from upstream stays as written.
