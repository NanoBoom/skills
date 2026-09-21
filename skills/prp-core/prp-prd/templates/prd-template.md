# PRD Template

Keep every **required** section. Include a **conditional** section only when it carries information.
Remove instructional comments and unused placeholders from the saved PRD.

**Each fact appears once.** `/prp-plan` re-reads this PRD in full for every phase it plans, so a
claim repeated across sections is paid for once per phase. Two rules keep it single-source:

- The hypothesis owns the success measure. Add a metrics table only when more than one measure
  matters, and never restate the hypothesis line inside it.
- Evidence and research findings live next to the claim they decided, with their source. There is no
  separate research dump at the end.

The `Implementation Phases` table is a machine contract: `/prp-plan` selects the next actionable
phase from it and `/prp-prd-update` writes `Status`, `Plan`, `Report`, and `PR` back into it. Keep the
columns and their spelling.

---

# {Product/Feature Name}

## Problem

{2-3 sentences: who has what problem, and what it costs to leave it unsolved.}

**Evidence**

- {User quote, data point, or observation that proves the problem exists}
- {If none: `Assumption - needs validation through {method}`}

## Users

**Primary user**: {Who they are, what they do today, and the moment the need appears.}

**Job to be done**: When {situation}, I want to {motivation}, so I can {outcome}.

**Not the target**: {Who this is explicitly not for, and why.}

## Hypothesis

We believe {capability} will {solve problem} for {users}.
We'll know we're right when {observable, measurable outcome}.

<!-- CONDITIONAL: add this table only when more than one measure matters. -->

| Metric | Target | How Measured |
|--------|--------|--------------|
| {Secondary metric} | {Specific number or observable state} | {Method} |

## Scope

{One paragraph: what is being built and why this approach beats the alternatives.}

**MVP**: {The minimum that tests the hypothesis.}

**Critical path**: {The shortest journey to value.}

### Capabilities

<!-- CONDITIONAL: use this table only when priority is genuinely contested or the list is long enough
     that prose loses it. Otherwise state the must-haves in the MVP line above. -->

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | {Capability} | {Why essential to the hypothesis} |
| Should | {Capability} | {Important, not blocking} |

### Not building

- {Excluded capability} — {why, and what would have to change to reconsider}

## Technical Approach

**Feasibility**: {HIGH/MEDIUM/LOW} — {the reason}

**Architecture notes**
- {Key decision or existing primitive to build on, with the evidence or source that decided it}

**Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| {Risk} | {H/M/L} | {How to handle} |

## Implementation Phases

<!--
  STATUS: pending | in-progress | complete
  PARALLEL: phases that can run concurrently (e.g. "with 3" or "-")
  DEPENDS: phases that must complete first (e.g. "1, 2" or "-")
  PLAN / REPORT / PR: links written back by /prp-prd-update as work lands
-->

| # | Phase | Description | Status | Parallel | Depends | Plan | Report | PR |
|---|-------|-------------|--------|----------|---------|------|--------|----|
| 1 | {Phase name} | {What this phase delivers} | pending | - | - | - | - | - |
| 2 | {Phase name} | {What this phase delivers} | pending | - | 1 | - | - | - |

Each phase must be independently planable and deliver or directly unlock user-visible value. A phase
that ends at infrastructure needs the follow-up phase that delivers the outcome.

### Phase details

<!-- One block per phase, only where the table row is not self-explanatory. -->

**Phase 1: {Name}** — **Goal**: {what this achieves}. **Scope**: {bounded deliverables}.
**Success signal**: {how we know it is done}.

<!-- CONDITIONAL: add a parallelism note only when phases can run concurrently and it is not obvious
     from the table why they do not collide. -->

## Open Questions

- [ ] {Unresolved question, and what would settle it}

## Decisions Log

<!-- CONDITIONAL: only decisions whose rationale would otherwise be re-litigated. -->

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| {Decision} | {Choice} | {Options considered} | {Why this one} |

---

*Generated: {timestamp}*
*Status: DRAFT - needs validation*
