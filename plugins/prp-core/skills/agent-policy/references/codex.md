# Codex

Checked on 2026-09-30 against the Codex docs and Codex CLI 0.159.2. Model
availability depends on the plan and the workspace. Confirm a model in
`/model` before relying on it.

Sources: [models](https://learn.chatgpt.com/docs/models),
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[config reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[pricing](https://learn.chatgpt.com/docs/pricing),
[Codex plugin for Claude Code](https://github.com/openai/codex-plugin-cc).

## Lookup table

| Task type | Model | Effort | Development scenarios |
| --- | --- | --- | --- |
| Search | `gpt-6-luna` | `low` | Find where a function is defined, list every caller of an API, locate the config that sets a flag |
| Summarize | `gpt-6-luna` | `low` | Condense a CI log to the failing step, extract endpoints from an OpenAPI file, summarize a long issue thread |
| Web research | `gpt-6-luna` | `medium` | Check a library's current API, confirm platform behavior, find how others solved a problem |
| Mechanical edit | `gpt-6-luna` | `medium` | Rename a symbol across files, bump dependency versions, apply a diff the brief spells out |
| Code tracing | `gpt-6.1-sol` | `low` | Trace a request from handler to database, map what a config flag changes, explain a module before editing it |
| Test and verify | `gpt-6-luna` | `high` | Run the test suite and report failures, reproduce a bug from its steps |
| Bounded implementation | `gpt-6-luna` | `high` | Add an endpoint that mirrors an existing one, write tests for one function, fix a bug whose cause is known |
| Routine review | `gpt-6.1-sol` | `medium` | Review a PR for correctness, missing tests, and repository fit |
| High-risk review | `gpt-6.1-sol` | `high` | Review a diff to auth, billing, a schema migration, a lock, or a public API |
| Feature implementation | `gpt-6.1-sol` | `high` | Build a feature across several modules, refactor a subsystem without changing behavior |
| Planning and design | `gpt-6.1-sol` | `high` | Write an implementation plan, choose between two architectures, design a data model |
| Hard debugging | `gpt-6.1-sol` | `xhigh` | Find a race condition, a memory leak, or a regression with no obvious cause |
| High-stakes second opinion | `gpt-6-astra` | `low` | Re-review an auth or payment diff after a Sol review stayed uncertain |
| Critical change | `gpt-6-astra` | `high` | Change a permission model, write an irreversible migration, audit a security boundary |

Luna costs one twentieth of Sol, so the table leans on it further than the
Claude Code table leans on `haiku`. When a Luna agent misses on a test,
reproduction, or bounded implementation task, retry on `gpt-6.1-sol` at
`medium`.

## Models

| Model | Docs' description | Credits per 1M tokens, input / output | Cost vs Sol |
| --- | --- | --- | --: |
| `gpt-6-luna` | Most efficient, for focused high-volume work: summarization, extraction, focused coding | 2.5 / 12.5 | 0.05 |
| `gpt-6.1-sol` | Near-Astra performance at lower cost; the recommended start for most tasks | 50 / 250 | 1 |
| `gpt-6-astra` | Most capable, for the most demanding work | 250 / 1,250 | 5 |

`gpt-6-sol` and the GPT-5.6 models are still listed, but older. GPT-5.5
retires from Codex on 2026-10-14.

## Effort

`model_reasoning_effort` takes `low`, `medium`, `high`, `xhigh`, `max`, and
`ultra`, limited to what the model supports.

| Model | Levels | Default when unset |
| --- | --- | --- |
| `gpt-6.1-sol` | `low` to `ultra` | `low` |
| `gpt-6-astra` | `low` to `ultra` | `medium` |
| `gpt-6-luna` | `low` to `max`, no `ultra` | `medium` |

- `gpt-6.1-sol` defaults to `low`, so every Sol row above `low` needs effort
  set explicitly.
- Use `max` only after an `xhigh` run stopped short.
- Do not use `ultra` unless the user asks for it. It runs at maximum reasoning
  and launches subagents on its own, on a model and effort you did not pick.

## Passing model and effort

| Launch | Model | Effort |
| --- | --- | --- |
| `codex` or `codex exec` | `-m <model>` | `-c model_reasoning_effort="<level>"` |
| Profile | `-p <name>` layers `$CODEX_HOME/<name>.config.toml` over the base config | same file |
| Base config | `model` in `~/.codex/config.toml` | `model_reasoning_effort` in the same file |
| In a session | `/model` | `/model` |
| Codex subagent | name it in the spawn request, or `model` in the agent's TOML | name it in the spawn request, or `model_reasoning_effort` in the agent's TOML |
| Claude Code, Codex plugin | `/codex:rescue --model <model>` | `--effort <level>` |

Example: `codex exec -m gpt-6-luna -c model_reasoning_effort="low" "list every caller of parseConfig"`.

Codex subagents:

- A subagent resolves each setting from an explicit spawn value, then the
  `[agents]` default in `config.toml`, then the parent's value. A custom agent
  file (`~/.codex/agents/` or `.codex/agents/`) that sets `model` or
  `model_reasoning_effort` overrides the result.
- With nothing set, a subagent inherits the parent's model and effort. Name
  both in every spawn request: "spawn an agent on gpt-6-luna at low effort to
  list every caller of parseConfig".
- A spawn that names a model but no effort runs at that model's default. A
  custom agent file that sets only `model` keeps the effort resolved before
  it, which the new model may not support. Set both.
- `agents.default_subagent_model` and
  `agents.default_subagent_reasoning_effort` in `config.toml` set the fallback
  for every spawn.

The Codex plugin for Claude Code:

- `/codex:rescue` leaves model and effort unset unless you pass them, so the
  delegation runs the machine's Codex defaults. Pass both.
- Its `--effort` accepts `none`, `minimal`, `low`, `medium`, `high`, and
  `xhigh`. It does not accept `max` or `ultra`.

## Naming

The `prp-core` agents do not run in Codex, so `agent_type` is always a task
name. Put the name in the spawn request of a Codex subagent: "spawn
`find-config-callers:gpt-6-luna:low` to list every caller of parseConfig".
`codex exec` and `/codex:rescue` take no name, so give it in the message
that announces the launch: `fix-login-redirect:gpt-6.1-sol:high`.

The effort field is the level the agent resolves to, never where it came
from: not `parent`, `config`, `inherit`, or `default`. A custom agent file
that sets `model_reasoning_effort` wins over the spawn value, so name the
file's level. A launch that passes no effort runs at the value resolved under
Passing model and effort: the profile or base config, then for a subagent the
`[agents]` default and the parent's level, then the model's default from the
Effort table. A `codex exec -m gpt-6.1-sol` with no effort set anywhere is
`fix-login-redirect:gpt-6.1-sol:low`.
