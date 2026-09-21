# Implementation Report

This report is the handoff that crosses context windows: reviewers, correction passes, and PR
authoring read it instead of the conversation that produced it. Record what a fresh context cannot
recover from the diff, the plan, and the PR. Do not restate the plan, re-describe the code, or
narrate the work.

Keep every **required** section. Include a **conditional** section only when it applies.

---

**Plan:** `{absolute plan path}`
**Branch:** `{branch name}`
**Status:** `{COMPLETE | BLOCKED}`

## Outcome

{What now works, in two or three sentences. Not a task-by-task recap.}

## Validation

<!-- Commands actually run, with the evidence that makes the result checkable. -->

| Command or check | Result | Evidence |
| --- | --- | --- |
| `{actual command}` | `{passed | failed}` | {concise factual output} |

**Acceptance:** `{All satisfied | AC<n> unsatisfied: <what is missing>}`

## Deviations and Decisions

{Only deviations from the plan and decisions a downstream context must preserve, or `None.`}

## Review Dispositions

<!-- CONDITIONAL: omit entirely when this delivery has no review or CI findings. When it has them,
     every finding appears here. Never leave one deferred. -->

| ID | Disposition | Reason and evidence | Tracking |
| --- | --- | --- | --- |
| `R1` | `{FIXED | NOT A FINDING | TRACKED FOLLOW-UP | DECLINED}` | {why, with decisive evidence} | `{issue URL | Not applicable}` |

## Blocker

<!-- CONDITIONAL: required when Status is BLOCKED, omitted when COMPLETE. -->

- **Blocked on:** {The exact blocker and the evidence for it.}
- **Recovery:** {Why it cannot be completed now and the concrete next action.}
- **Ready to commit:** {The coherent change that should be committed once the blocker clears.}

## Delivery

- **Commits:** `{SHA and message for each delivery commit | Not created}`
- **Pull Request:** `{URL | Not opened}`
- **Base / Head:** `{base <- head | Not applicable}`
- **Source PRD:** `{absolute path and phase update | None}`
- **Tracked follow-ups:** `{None | verified issue links for valuable, distinct outcomes outside this delivery}`
