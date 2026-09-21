# Adaptive Implementation Plan Template

Keep every **required** section. Include a **conditional** section only when it adds decision or
implementation value. Remove instructional comments and unused placeholders from the saved plan.

**Each fact appears once.** This plan is re-read in full on every implementation and correction pass
and published verbatim to the source issue, so a sentence repeated across sections is paid for many
times. The sections below are already scoped to avoid overlap:

- `Recommendation → Evidence` carries the `file:line` that decided the *design*. Tasks carry the
  `file:line` that will be *changed*. A file needed for both is cited in Evidence and referenced by
  name in the task, not re-described.
- `Mandatory reading` lists only what the implementer must read before editing and that no task
  already names.
- Task-level `Validation` proves one task. The `Validation` table lists only the integrated gates no
  task already runs.
- `Acceptance` states the completed behavioral contract once. Tasks and validation refer to `AC<n>`
  instead of restating it.

---

# {Outcome-oriented plan title}

**Plan ID:** `{stable kebab-case identifier}`
**Source PRD:** `{absolute path | None}`
**PRD Phase:** `{phase number and name | None}`
**Source Issue:** `{tracker reference or URL | None}`
**Plan Publication:** `{verified issue comment URL | None}`

## Outcome

**Problem:** {The specific problem and who experiences it: user, operator, team, or system.}

**User outcome:** {What becomes possible or reliably different.}

**Invariant:** {Observable property every acceptable solution must preserve.}

**Success signal:** {Quantitative or qualitative evidence that the delivered change improved the
outcome; or `Not measured separately — <why acceptance fully captures this internal outcome>`. Do not
invent a metric.}

## Recommendation

{The chosen solution and why it is the simplest coherent shape the codebase supports. Name the
existing primitives it reuses, the machinery it removes or avoids, and the evidence that justifies
any new state, scaffold, abstraction, or cross-layer signal.}

### Evidence

- `{file:line}` — {the existing behavior, primitive, or convention that decided the design}
- {Decision-relevant issue comment, linked issue, PR, or specification, when the plan came from a tracker}
- {Official source and version, when external behavior matters}
- {Spike verdict and absolute report path, when a spike was run}

### Alternatives considered

<!-- CONDITIONAL: only alternatives a reviewer would otherwise propose. -->

- **{Alternative}:** {Why it loses against the invariant, evidence, or ownership cost.}

## Root Cause

<!-- CONDITIONAL: for a bug, regression, error, stack trace, or unexplained current behavior. -->

- **Observed failure:** {Reproduced symptom and decisive observation.}
- **Causal chain:** {Shortest evidence-backed chain from symptom to cause.}
- **Fix boundary:** `{path:line}` — {smallest responsible behavior to change.}
- **Regression proof:** {Test or procedure that fails before the fix and passes after.}
- **Remaining uncertainty:** {Named condition and resolution step, or `None`.}

## Visuals

<!-- CONDITIONAL: a UX diagram for interaction changes, an architecture diagram for structural ones.
     Follow references/visuals.md. Omit when prose is clearer. -->

## Mandatory reading

<!-- Only what the implementer must understand before editing and that no task below already names. -->

| File | Why it matters |
|---|---|
| `{path:lines}` | {The primitive, contract, or test precedent it carries} |

## Not building

- {Explicit exclusion and why it is outside the invariant or belongs later}

## Delivery Considerations

<!-- CONDITIONAL: only when existing users, behavior, or stored data may be affected. Keep only
     applicable rows; each row names work a task owns, not a concern to think about later. -->

| Concern | Decision and owned work |
|---|---|
| Discoverability / adoption | {How affected users learn or adopt the change} |
| Compatibility / migration | {Existing behavior or data transition} |
| Rollout / reversibility | {Release posture and safe rollback} |
| Observability | {How product or operational surprises become visible} |
| Documentation / communication | {Required user-facing or operator material} |

## Implementation

<!-- Follow references/task-format.md. Repeat in dependency order. -->

### 1. {Outcome}

**Files and integration points**
- `{path:line}` — {CREATE / UPDATE and ownership rationale}

**Implementation**
- {Concrete behavior, and the existing primitive or precedent to use.}
- {Boundary, failure behavior, migration, or compatibility detail when relevant.}

**Tests**
- {Behavior to prove, at the appropriate test surface.}

**Validation**
- `{focused command}` — {Expected observable result.}

## Acceptance

1. **AC1 — {Observable outcome}:** {Given/when/then behavior or externally verifiable result.}
2. **AC2 — {Preserved invariant}:** {Behavior that must remain true across the change.}

## Validation

<!-- Integrated gates only, in execution order. Omit anything a task's own Validation already runs. -->

| Gate | Command or procedure | Proves |
|---|---|---|
| {Project gate} | `{command}` | {AC<n>, types, lint, suite, build, or equivalent} |
| {Runtime / manual} | {Concrete procedure, when automation cannot prove it} | {AC<n> not otherwise observable} |

## Risks and Decisions

<!-- CONDITIONAL: omit when none remain. Minor decisions only; resolve architectural forks with the
     user before finalizing. -->

| Decision or risk | Recommendation | Evidence / mitigation | Consequence if different |
|---|---|---|---|
| {Question or risk} | {Planner's recommendation} | {Why} | {What changes} |

## Related Plans

<!-- CONDITIONAL: maintained by the update-references workflow. Omit until links exist. -->

- **Depends on:** {absolute plan path + label, or None}
- **Followed by:** {absolute plan path + label, or None}

## Agent Notes

<!-- CONDITIONAL free-form canvas for material that fits nowhere above. Not a place to hide blockers,
     scope, or decisions the user needs to see. -->
