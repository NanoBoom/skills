# Harnesses

Every plugin has one source, `plugins/<plugin>/`, in the Claude Code plugin
format. Claude Code installs it unchanged. For Codex and Pi an adapter in
[`tools/adapters/`](../tools/adapters) writes what that harness reads into the
gitignored `build/<harness>/`, grouped by plugin, and `make install-<harness>`
installs it. Nothing generated is committed. Each adapter declares where it
generates and installs; this page describes the result.

## Components

Skills, agents, and commands are written once, in the Claude Code layout, and
each adapter converts them. Hooks and MCP servers are not converted: each
harness runs them differently, so the plugin author writes one version per
harness, in that harness's own format.

| Component | Claude Code (source) | Codex | Pi |
|---|---|---|---|
| Install route | marketplace | `make install-codex` | `make install-pi` |
| Skills | `skills/<name>/` | copy in a local Codex plugin, split over 8000 bytes | copy |
| Agents | `agents/<name>.md` | `~/.codex/agents/<plugin>__<agent>.toml` | `~/.pi/agent/agents/<plugin>__<agent>.md` |
| Model | `model:` alias | mapped to GPT | mapped to `anthropic/...` |
| Effort | `effort:` | `model_reasoning_effort` | dropped |
| Read-only agents | `disallowedTools` | `sandbox_mode = "read-only"` | `tools: read, grep, find, ls, bash` |
| Commands | `commands/<name>.md`, slash commands | skill `<name>` | prompt template `<name>` |
| Hooks and MCP servers | `hooks/hooks.json`, `.mcp.json` | `harness/codex/`, copied unread over the plugin root | `harness/pi/extensions/<name>`, copied unread as `<plugin>__<name>` |

`npx skills` works with any of them and installs skills only.

The adapters never read a file under `harness/`; `tools/validate.py` checks only
where those files sit and that their JSON parses. When a plugin has Claude Code
hooks or MCP servers but no `harness/<harness>/`, `make generate` prints a
`note` line for that harness. Notes are expected and never fail a check.

Codex has no slash commands, so a command becomes a skill of the same name.
That puts commands and skills in one namespace, and `make validate` rejects a
command named like any skill. Commands must sit directly in `commands/`.

[`tools/tests/fixtures/kitchen-sink`](../tools/tests/fixtures/kitchen-sink) is a
plugin with one of every component, including `harness/codex/` and
`harness/pi/`. `tools/tests/test_components.py` runs it through every adapter,
the validator, and the installer, and against the real Codex CLI when one is on
`PATH`. Load it in Claude Code with
`claude --plugin-dir tools/tests/fixtures/kitchen-sink`.

### `harness/codex/`

Everything in it is copied to the root of the generated Codex plugin, so it is
laid out as a Codex plugin root:

```
harness/codex/
  hooks/hooks.json    Codex hooks; the manifest's `hooks`
  .mcp.json           Codex MCP servers; the manifest's `mcpServers`
  hooks/<script>      anything the hooks or servers run
```

Inside those files `${CLAUDE_PLUGIN_ROOT}` is the installed Codex plugin, so
`"${CLAUDE_PLUGIN_ROOT}/hooks/<script>"` names a script from `harness/codex/`.
The plugin's Claude Code files are not in the Codex plugin, so a Codex hook
cannot run a script from the plugin's own `hooks/`; put a copy in
`harness/codex/`. `skills/` and `.codex-plugin/` are written by the adapter, and
`make validate` rejects them here.

Codex runs a plugin hook only after you trust it: the next interactive session
lists new or changed hooks for review, and `codex exec` skips untrusted ones.

### `harness/pi/`

It holds only `extensions/`. Each entry is one Pi extension, a `.ts` or `.js`
file or a directory with an `index.ts` or `index.js`, and Pi runs hooks and MCP
clients as extensions. The entry is copied to `build/pi/<plugin>/extensions/` as
`<plugin>__<name>` and installed into `~/.pi/agent/extensions/`, so it must not
import anything outside itself.

## Generated names

A generated agent is named `<plugin>__<agent>`, for example
`prp-core__code-reviewer`. Neither Codex nor Pi documents a colon in an agent
name, and the double underscore cannot appear in a plugin or agent name, so the
mapping is unambiguous.

In every generated skill copy, `prp-core:<agent>` becomes `prp-core__<agent>`.
Only names of agents that exist are rewritten, plus the documentation
placeholder `prp-core:<agent>`. Scoped skill names such as `/prp-core:prp-plan`
are left alone. `tools/validate.py` fails if a generated copy still names an
agent the Claude Code way.

Skills keep their bare names everywhere, which is why skill names must be unique
across plugins.

## Model mapping

`MODEL_ALIASES` in [`capabilities.py`](../tools/adapters/capabilities.py) is
authoritative; this table mirrors it.

| Source alias | Codex | Pi |
|---|---|---|
| `fable` | `gpt-6-astra` | `anthropic/claude-fable-5-1` |
| `opus` | `gpt-6.1-sol` | `anthropic/claude-opus-5-5` |
| `sonnet` | `gpt-6.1-sol` | `anthropic/claude-sonnet-5-5` |
| `haiku` | `gpt-6-luna` | `anthropic/claude-haiku-5-5` |
| `inherit` | field omitted | field omitted |

The Codex column follows the `agent-policy` skill's
[Codex reference](../plugins/prp-core/skills/agent-policy/references/codex.md).
To use another provider in Pi, change `MODEL_ALIASES` and rerun
`make install-pi`.

## Claude Code

The source format. `.claude-plugin/marketplace.json` points each entry at
`./plugins/<plugin>`, and `${CLAUDE_PLUGIN_ROOT}` resolves to that directory.
Claude Code does not read `harness/`.

## Codex

Codex keeps user-level hooks in one `~/.codex/hooks.json` and MCP servers in
`config.toml`, so they cannot be installed file by file. A Codex plugin can carry
skills, hooks, and MCP servers, but not custom agents. `make install-codex`
therefore installs in two halves:

- **plugins**: `build/codex/` is a local Codex marketplace named like the Claude
  Code one, `nanoboom`. `.agents/plugins/marketplace.json` lists every plugin
  with skills, commands, or a `harness/codex/`, and
  `plugins/<plugin>/.codex-plugin/plugin.json` sets `skills`, plus `hooks` and
  `mcpServers` when `harness/codex/` has those files. The installer runs
  `codex plugin marketplace add build/codex` and `codex plugin add
  <plugin>@nanoboom` for each, and removes any plugin it installed from that
  marketplace earlier that is no longer built. Codex copies each plugin into its
  cache, so rerun the install after `make generate`.
- **agents**: `build/codex/agents/<plugin>/<plugin>__<agent>.toml`, linked into
  `${CODEX_HOME:-~/.codex}/agents/`. Each sets `name`, `description`, `model`,
  `model_reasoning_effort`, `sandbox_mode`, and `developer_instructions`.

`ONLY=plugins` or `ONLY=agents` installs one half. `make uninstall-codex`
removes the agents, every plugin installed from this checkout's `build/codex/`,
and that marketplace once none of its plugins is left; plugins from other
marketplaces are left alone. If another marketplace named `nanoboom` is
registered, install stops and names the `codex plugin marketplace remove`
command to run.

With `PROJECT`, the kinds are `skills` and `agents`, Codex gets no plugin, and
the Codex CLI does not run: a Codex
plugin is enabled in the user configuration, for every project. The skills go to
`<project>/.codex/skills/`, the same rewritten and split copies the plugins
carry, and the agents to `<project>/.codex/agents/`. Codex hooks and MCP servers
from `harness/codex/` are not installed into a project, and the installer says
so for each plugin that has them. Merging them into the project's
`.codex/hooks.json` and `.codex/config.toml` is possible but not done.

Codex truncates a skill prompt at 8000 bytes (`MAX_SKILL_PROMPT_BYTES` in
`codex-rs`), so a copy longer than that keeps whole `## ` sections from the top
and moves the rest, in order, to `references/codex-overflow.md`, with a pointer
where the cut is.

Adding `NanoBoom/skills` as a Codex marketplace is not supported. Codex can read
`.claude-plugin/marketplace.json`, but it then installs the Claude Code plugin
unchanged: skills that name agents the Claude Code way, and Claude Code's
`hooks/hooks.json`, which Codex loads when a manifest names no hooks.

## Pi

`make install-pi` generates, for each plugin, `build/pi/<plugin>/skills/<skill>/`,
`agents/<plugin>__<agent>.md`, `prompts/<command>.md`, and
`extensions/<plugin>__<name>`, and installs them into `skills/`, `agents/`,
`prompts/`, and `extensions/` under `$PI_CODING_AGENT_DIR` or `~/.pi/agent`, or
under `<project>/.pi` with `PROJECT`. The agents use the format of Pi's
reference `subagent` extension, which must be installed for them to load; it
reads `<project>/.pi/agents/` only with `agentScope: "project"` or `"both"`.
`ONLY=skills|agents|commands|extensions` installs one kind. Pi also reads
`~/.agents/skills/`, so `npx skills` copies there show up in Pi a second time.

## Install options

`make install-codex` and `make install-pi` take the same variables, and
`make uninstall-<harness>` takes `PLUGINS` and `PROJECT`:

| Variable | Effect |
|---|---|
| `PLUGINS=a,b` | Only these plugins, by name; default every plugin in `.claude-plugin/marketplace.json`. Each plugin carries what it needs, so any subset works. |
| `PROJECT=/path` | Into `<path>/.codex/` or `<path>/.pi/` instead of the user configuration. Use an absolute path: `make` runs in this clone. A path inside this clone is refused. |
| `ONLY=kind` | One kind of artifact, as listed for each harness above. |
| `COPY=1` | Real copies instead of symlinks, for a project that commits them. |
| `FORCE=1` | Replace a symlink that points into another checkout. |

A symlink points into this clone's `build/`, so `make generate` updates it in
place, but it breaks on any other machine. A copy does not change until the
next install, and can be committed. The installer records each copy in
`.nanoboom-install.json` at the configuration root, `.codex/` or `.pi/` for a
project: a later install replaces only those copies and switches between copies
and symlinks freely, and uninstall removes only them and the file. Nothing that
was not installed from this clone is replaced. Every install also removes this
clone's entries whose source is no longer generated.

Both harnesses load a project's `.codex/` or `.pi/` only after you trust the
project: Codex asks when it starts in an untrusted project, and Pi needs `/trust`,
or `--approve` in print mode.

## Hooks

`prp-loop-stop.sh` and `prp-research-team-stop.sh` are Claude Code Stop hooks,
and the opt-in `prp-response-policy-prompt.sh` is a Claude Code
UserPromptSubmit hook, all in `plugins/prp-core/hooks/hooks.json`. `prp-core`
has no `harness/` directory, so neither Codex nor Pi runs them. `prp-loop-stop.sh`
would do nothing there anyway: the loop records its owner from
`CLAUDE_CODE_SESSION_ID`, so a loop started elsewhere has no owner for the hook
to hold. Without the prompt hook, `response-policy` still applies at every PRP
skill's report step, because each of those skills names it. A Codex or Pi
version of any of these hooks would go in `plugins/prp-core/harness/`.
