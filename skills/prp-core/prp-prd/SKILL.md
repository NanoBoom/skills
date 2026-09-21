---
name: prp-prd
description: Interactive PRD generator - problem-first, hypothesis-driven product spec with an implementation-phases table that /prp-plan consumes. Use when the user wants to create a PRD, write a product or feature spec, scope a new product or feature before planning, or invokes /prp-prd.
argument-hint: "[feature/product idea] (blank = start with questions)"
---

# PRD Generator

**Input**: $ARGUMENTS (if absent, use the conversation.)

Produce the product contract a planner can implement from and a skeptic can argue with: who has the
problem, what evidence says it is real, the testable hypothesis, what is explicitly not being built,
and phases that can each be delivered on their own.

Write what is known and mark what is not. `TBD - needs <method>` is a finding. A plausible-sounding
invented requirement is a defect.

## 1. Interview

Establish these before generating. Use `AskUserQuestion`, batching related questions into one round
with concrete options drawn from the request, the conversation, and the codebase, so the user can
usually pick rather than compose. Skip whatever the input already answers; do not re-ask for
completeness.

- **Problem** — who specifically has it, the observable pain, why today's alternatives fail, why now.
- **Evidence** — what proves it exists. If nothing does, name the assumption and how to validate it.
- **User** — the primary user and their trigger, the job to be done, and who is explicitly not the target.
- **Scope** — the MVP that tests the hypothesis, the must-haves, the non-goals, the fixed constraints.
- **Success** — the observable outcome that would show it worked.

Stop when another answer would not change the PRD. Before generating, restate the problem and scope
in one short paragraph so a wrong premise is cheap to correct.

## 2. Ground it

Research only where a finding could change the problem, the scope, the phases, or the feasibility
verdict. Skip it for a small feature in a codebase already read in this session.

When it is worth it, dispatch in parallel and give each agent the problem and the decision its
evidence should settle:

- `prp-core:codebase-explorer` — existing functionality, primitives, and constraints the PRD can build on.
- `prp-core:codebase-analyst` — how the closest existing feature actually works end to end, when phase
  sizing or feasibility depends on it.
- `prp-core:web-researcher` — how this is solved elsewhere, known pitfalls, or platform facts that
  decide an approach. Prefer primary sources.

Subagent dispatch needs the installed `prp-core` plugin; without it, do the same research inline.

Report only the findings that changed your thinking, and say what they changed. If feasibility is now
LOW or a finding contradicts the user's premise, raise it before writing the PRD rather than burying
it in a risk table.

## 3. Generate

Resolve the canonical store:

```bash
# --- PRP store resolver (canonical; keep byte-identical across skills) ---
# Store is `.prp/` in the project root. --git-common-dir makes every worktree of
# a project share one store; the store gitignores itself. PRP_DIR relocates it.
_gd="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
case "$_gd" in */.git) _root="${_gd%/.git}" ;; "") _root="$PWD" ;; *) _root="$_gd" ;; esac
_root="$(cd "$_root" && pwd -P)"
PRP_DIR="${PRP_DIR:-$_root/.prp}"
mkdir -p "$PRP_DIR"; [ -f "$PRP_DIR/.gitignore" ] || printf '*\n' > "$PRP_DIR/.gitignore"
mkdir -p "$PRP_DIR/prds"
```

Read `templates/prd-template.md` and write the PRD to `$PRP_DIR/prds/{kebab-case-name}.prd.md`.

Use the product's own terms and plain, specific language. Cut filler, invented jargon, generic claims,
and formulaic phrasing. One name per concept throughout.

Phases are the part downstream automation depends on. Each must be independently planable, ordered by
real dependency, and sized so one implementation cycle can finish it. Keep the table's columns and
spelling: `/prp-plan` selects the next actionable phase from it, and `/prp-prd-update` writes
`Status`, `Plan`, `Report`, and `PR` back into it.

## 4. Hand off

Report:

```markdown
## PRD Created

**File**: `{absolute path}`

**Problem**: {one line}
**Solution**: {one line}
**Key metric**: {primary success metric}

### Where the evidence is thin

{Sections resting on assumption rather than evidence, and what would validate each, or "None".}

### Open questions ({count})

{The questions that still need answers.}

### Phases

| # | Phase | Status | Parallel |
|---|-------|--------|----------|
{rows from the PRD}

**Next**: `/prp-plan {absolute path}` — plans the next pending phase.
{When the PRD rests on an untested assumption, recommend the research, spike, or prototype that would
settle it first, and name the section it would change.}
```

Before reporting, check the PRD against the bar that makes it worth planning from: the problem is
specific and either evidenced or marked as an assumption, the primary user is concrete rather than
"users", the hypothesis is testable with a measurable outcome, the non-goals are explicit, the
uncertainties are listed rather than hidden, and each phase is independently deliverable.

## Resources

- `templates/prd-template.md` — the PRD artifact, including the machine-read phases table
