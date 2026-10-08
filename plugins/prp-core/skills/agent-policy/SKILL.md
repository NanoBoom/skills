---
name: agent-policy
description: Picks the model and reasoning effort for every agent at launch, by task type, to save tokens. Use before starting any subagent, fork, workflow agent, or Codex delegation, when deciding which model or effort an agent should run on, when an agent failed and the retry needs a different model or effort, when the user asks about model routing or effort, or invokes /agent-policy.
argument-hint: "[task description] (blank = apply to the current task)"
---

# Agent Policy

Launch every agent on the cheapest model and effort that finishes its task in
one round. An agent left to inherit runs on the main session's model and
effort, which is usually the most expensive pair available. Judge cost per
finished task, not per token: a cheap agent that needs a second round is not
cheap.

## Step 1: Read the tool reference

Read the reference for the tool that will run the agent. Each one holds the
lookup table (task type, model, effort, development scenarios) and the
tool-specific facts: how to pass model and effort, what each model defaults
to, and what cannot be routed.

| Tool | Reference |
| --- | --- |
| Claude Code: Agent tool, forks, Workflow scripts | `references/claude-code.md` |
| Codex: Codex CLI, `codex exec`, Codex subagents, the Codex plugin for Claude Code | `references/codex.md` |

For any other tool, map its cheapest fast model to the search rows and its
flagship to the hard rows, and say which mapping you used. Do not guess a
model name the tool has not shown you.

## Step 2: Classify the task

Classify each agent's own task, not the whole user request. One request often
launches agents of several types.

| Task type | What defines it |
| --- | --- |
| Search | Locate files, symbols, callers, or config; the answer is a list of paths |
| Summarize | Condense or extract from material already in hand: logs, docs, a diff |
| Web research | Gather current external facts, APIs, or platform behavior from primary sources |
| Mechanical edit | A change you can specify exactly: rename, reformat, bump a version, apply a given diff |
| Code tracing | Explain how existing code behaves: control flow, data flow, state, side effects |
| Test and verify | Run builds and tests, reproduce a reported bug, check a page in a browser |
| Bounded implementation | One module, an existing pattern to copy, a test that proves it |
| Routine review | Review an ordinary diff for correctness and fit |
| High-risk review | Review a diff that touches security, permissions, data, concurrency, migration, or a public contract |
| Feature implementation | Several files, real design choices, behavior that must not regress |
| Planning and design | An implementation plan, or a decision that crosses module boundaries |
| Hard debugging | A subtle, intermittent, or cross-module bug, or an unfamiliar domain |
| High-stakes second opinion | Re-review a diff whose ordinary review stayed uncertain |
| Critical change | Security, permissions, privacy, transactions, irreversible migration, high-impact release |

When a task sits between two types, take the cheaper one and escalate on
evidence. A review's type follows the risk of the diff, not its size.

## Step 3: Launch with both set

- Pass the model and the effort from the table on every launch. Where the
  tool cannot set one of them per launch, the reference says how to get it.
- Do not launch an agent for work you can finish from the current context.
- Keep the premium model for the last two task types. Never use it for
  search, fan-out, routine implementation, builds, or documentation.
- Route the agent, not the session. Do not change the user's session model or
  effort to suit one agent.

## Step 4: Name the agent

Name every agent `agent_type:model:effort`, so the routing shows wherever
the agent is listed:

- `agent_type`: for an agent defined in this plugin's `agents/` directory, its
  name without the plugin scope: `codebase-analyst` for
  `prp-core:codebase-analyst`. For every other launch, including built-in
  types such as `Plan`, `Explore`, and `general-purpose`, forks, and Codex,
  a task name instead: what the agent does, in two to five lowercase words
  joined by hyphens. No colons.
- `model`: the model it runs on, written as the reference's lookup table
  writes it.
- `effort`: the level it runs at, which is not always the table's; the
  reference says when the two differ. Always a level such as `low` or
  `high`, never where it came from: when the agent inherits the session
  effort, write the session's level, not `session`, `inherit`, or `default`.
  Write `n/a` for a model without effort levels.

Examples: `codebase-analyst:sonnet:high`, `root-cause-analyzer:opus:xhigh`,
`write-auth-plan:opus:high`, `find-config-callers:haiku:low`.

The reference says which field of each launch carries the name.

## Escalation

Name why the agent failed before you retry.

1. **It did not try hard enough.** It skipped a file, did not run the tests,
   or stopped before double-checking. Retry on the same model, one effort step
   higher or with a sharper prompt.
2. **It did not know enough.** It missed a subtle bug, misread the domain, or
   made the wrong design call. Retry one model step up at the same effort.
3. Change one knob per retry, so the result shows which one mattered.
4. Rename the retry to match, so its name shows the knob that changed.
