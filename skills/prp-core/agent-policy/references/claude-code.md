# Claude Code

Checked against the Claude Code docs on 2026-09-30. Pass aliases, which
resolve to the current generation. Do not pin model versions.

Sources: [model configuration](https://code.claude.com/docs/en/model-config),
[subagents](https://code.claude.com/docs/en/sub-agents),
[skills](https://code.claude.com/docs/en/skills),
[pricing](https://platform.claude.com/docs/en/about-claude/pricing).

## Lookup table

| Task type | Model | Effort | Development scenarios |
| --- | --- | --- | --- |
| Search | `haiku` | n/a | Find where a function is defined, list every caller of an API, locate the config that sets a flag |
| Summarize | `haiku` | n/a | Condense a CI log to the failing step, extract endpoints from an OpenAPI file, summarize a long issue thread |
| Web research | `sonnet` | `low` | Check a library's current API, confirm platform behavior, find how others solved a problem |
| Mechanical edit | `sonnet` | `low` | Rename a symbol across files, bump dependency versions, apply a diff the brief spells out |
| Code tracing | `sonnet` | `medium` | Trace a request from handler to database, map what a config flag changes, explain a module before editing it |
| Test and verify | `sonnet` | `medium` | Run the test suite and report failures, reproduce a bug from its steps, click through a page and screenshot it |
| Bounded implementation | `sonnet` | `medium` | Add an endpoint that mirrors an existing one, write tests for one function, fix a bug whose cause is known |
| Routine review | `sonnet` | `high` | Review a PR for correctness, missing tests, and repository fit |
| High-risk review | `opus` | `high` | Review a diff to auth, billing, a schema migration, a lock, or a public API |
| Feature implementation | `opus` | `high` | Build a feature across several modules, refactor a subsystem without changing behavior |
| Planning and design | `opus` | `high` | Write an implementation plan, choose between two architectures, design a data model |
| Hard debugging | `opus` | `xhigh` | Find a race condition, a memory leak, or a regression with no obvious cause |
| High-stakes second opinion | `fable` | `low` | Re-review an auth or payment diff after a `sonnet` review stayed uncertain |
| Critical change | `fable` | `high` | Change a permission model, write an irreversible migration, audit a security boundary |

A `fable` agent at `low` searches less on its own. Tell it to read the code
before concluding.

## Models

| Alias | Resolves to | Input / output per MTok | Cost vs `opus` |
| --- | --- | --- | --: |
| `haiku` | Haiku 4.5 | $1 / $5 | 0.25 |
| `sonnet` | Sonnet 5.5 | $2 / $10 | 0.5 |
| `opus` | Opus 5.5 | $4 / $20 | 1 |
| `fable` | Fable 5.1 | $10 / $50 | 2.5 |

On Bedrock, Google Cloud, Foundry, and Claude Platform on AWS, `sonnet` and
`opus` can resolve to older models. Read the resolved model from the Agent
tool result.

## Effort

Levels: `low`, `medium`, `high`, `xhigh`, `max`. Use `max` only after an
`xhigh` run stopped short.

| Model | Levels | Default when unset |
| --- | --- | --- |
| Opus 5.5, Sonnet 5.5 | all five | `medium` |
| Fable 5.1 | all five | `high` |
| Haiku 4.5 | not listed as supporting effort | n/a |

A `sonnet` or `opus` row that says `high` runs one step lower unless something
sets `high` explicitly.

## Passing model and effort

Model precedence, highest first:

1. `model` on the Agent tool call, or on a Workflow `agent()` call.
2. `model` in the agent type's definition frontmatter.
3. `CLAUDE_CODE_SUBAGENT_MODEL`.
4. The main conversation's model.

| Launch | Model | Effort |
| --- | --- | --- |
| Agent tool | `model` parameter | no per-call parameter: the agent type's `effort` frontmatter, or the session effort |
| Workflow `agent()` | `model` option | `effort` option |
| Fork (`subagent_type: "fork"`) | main session's model, cannot change | session effort |
| Skill | `model` frontmatter, for the rest of the turn | `effort` frontmatter, while the skill is active |

- Always pass `model` on the Agent tool, built-in types included
  (`general-purpose`, `Explore`, `Plan`). Omitting it hands the choice to the
  definition or the main session.
- The Agent tool cannot set effort per call. When the table's effort matters,
  launch an agent type whose definition sets that `effort`, or use a Workflow
  `agent()` call, which takes `effort` directly.
- A `prp-core:<agent>` launched through the Agent tool runs at the `effort` in
  its own definition under the plugin's `agents/` directory. Pass the table's
  `model` and accept that effort. A Workflow `agent()` call with
  `agentType: "prp-core:<agent>"` can set both.
- A fork cannot be routed down. Use one only when the agent needs the full
  conversation.
- Keep `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` unset. It overrides every per-call
  and definition model, so no routing survives it.

## Session settings

These set the main session, which every inheriting agent and every fork
follows. Leave them to the user.

- `/model <alias>` and `/effort <level>` save a default. `/effort auto` clears the saved effort.
- `claude --model <alias> --effort <level>` applies to one session.
- `CLAUDE_CODE_EFFORT_LEVEL` overrides every other effort source while set.
- `modelSettings.<model-id>.effort` in settings sets effort per model. The
  older `effortLevel` key does not apply to Opus 5.5 or later.
