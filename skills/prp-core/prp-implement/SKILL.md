---
name: prp-implement
description: Implements and validates existing PRP plans and corrects reviewed or failing-CI pull requests. Always use when executing an implementation plan, implementing an issue that already has a local or published plan, correcting a PR from a PRP review report or CI failure, when another PRP workflow reaches its implementation or correction step, or when the user invokes /prp-implement.
argument-hint: "<plan path|planned issue> [--base <branch>] | review <review-report|PR> [finding decisions] | ci <PR> [failing-check evidence]"
---

# Implement Plan

Execute the supplied plan through a validated commit and pull request, or apply review and CI
findings to that pull request. Implementation, commit, and PR delivery stay in this context; review
judgment belongs to its own.

**Input**: $ARGUMENTS

## Mode

- **A plan path or planned issue** — initial implementation.
- **`review` + a review report, PR, or finding decisions** — correction pass. Read the original plan,
  implementation report, live PR diff and comments, and the complete canonical review report before
  editing. Human dispositions, when supplied, are binding.
- **`ci` + a PR and failing-check evidence** — correction pass. Read the original plan, implementation
  report, live PR diff, and full check logs, and reproduce the failure before editing. Correct only
  PR-caused failures; preserve the evidence when the failure is external or pre-existing.

Resume the original implementation context for corrections when it is available. In a fresh context,
rebuild the contract from the durable artifacts, not from an abbreviated findings summary.

```bash
# --- PRP store resolver (canonical; keep byte-identical across skills) ---
# Store is `.prp/` in the project root. --git-common-dir makes every worktree of
# a project share one store; the store gitignores itself. PRP_DIR relocates it.
_gd="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
case "$_gd" in */.git) _root="${_gd%/.git}" ;; "") _root="$PWD" ;; *) _root="$_gd" ;; esac
_root="$(cd "$_root" && pwd -P)"
PRP_DIR="${PRP_DIR:-$_root/.prp}"
mkdir -p "$PRP_DIR"; [ -f "$PRP_DIR/.gitignore" ] || printf '*\n' > "$PRP_DIR/.gitignore"
```

## 1. Establish context

Resolve the plan path from the arguments, the linked implementation report, or the conversation, and
read the whole file. When the input is an issue rather than a path, normalize number and URL forms to
the same tracker item and search `$PRP_DIR/plans/` for a matching `Source Issue`. If several match,
present the newest viable candidates and ask; never guess. If no local plan exists, retrieve the
latest complete issue comment marked `<!-- prp-plan-id: ... -->`, persist it under `$PRP_DIR/plans/`,
and use that. Never substitute the issue body for a missing plan.

Two gates for an issue-derived plan:

- Comments added after `Plan Publication` that materially change the implementation contract mean the
  plan is stale: invoke `/prp-plan` to revise and republish before implementing.
- `Source Issue` set but `Plan Publication` empty or unverifiable means the shared handoff is missing:
  invoke `/prp-plan publish <absolute plan path>`, re-read the plan, and stop if it stays unverified.

Read the repository instructions, the plan references the work needs, the relevant call sites, and
the existing tests before editing. Read `engineering.md` when the project has one, wherever it lives:
it carries the standard this repository checks work against and should steer the choices the plan
left open, not reopen the ones it already made. Absence is normal; never create it.

Live source code is the truth when it conflicts with the plan's assumptions, but the plan's goal,
acceptance criteria, and scope still hold. Stop and ask if reality makes the intended outcome
ambiguous or changes the product shape. Stop and explain if the work would require routing around a
missing foundational primitive that should exist first. Otherwise record the deviation and continue.

Work on the current feature branch or assigned worktree. If on the resolved base branch with a clean
tree, create a focused feature branch. Never overwrite unrelated changes, silently rebase, or swallow
a Git failure.

## 2. Implement

**Initial implementation**: execute tasks in dependency order, reading each referenced pattern before
changing the code it describes.

**Correction pass**: preserve the plan's outcome and invariant, and give every finding a terminal
disposition: `FIXED`, `NOT A FINDING` with decisive evidence, `TRACKED FOLLOW-UP` with a verified
issue link, or `DECLINED` with a reason. Never leave a bare deferred state. When a finding enumerates
the members of one invariant, cover every member; a member left unfixed gets its own recorded
disposition rather than silence. Decline speculative defense-in-depth, unnecessary generalization,
preferences presented as defects, and findings pointing in an unclear direction. Record why; do not
convert them into backlog noise.

Let the plan and the repository's own guidance settle craft. Three things they usually do not say:
reproduce a bug before fixing it whenever possible, and record the concrete evidence you used instead
when reproduction is impossible; write tests that prove the changed behavior and the acceptance
criteria (for a bug fix, one that fails before the fix and passes after) rather than adding volume;
and if the path keeps getting more complicated, stop and reconsider the approach instead of
absorbing the complexity.

Never defer work the plan, acceptance criteria, or agreed invariant require: complete it now or mark
the implementation `BLOCKED`. Prefer fixing a valid Suggestion now when the correction is narrow,
low-risk, aligned, and cheaper than recovering this context in another delivery cycle.

Track work separately only when it is clearly valuable, is a distinct outcome, needs a product or
architectural decision, or would materially widen this delivery. Search for an existing issue first
and group findings that share one outcome or primitive; create at most one human-visible GitHub issue
when none fits. Carry verified links into the report and the PR description.

Record deviations and implementation-only decisions in the implementation report. Keep a legacy
plan's maintained Agent Notes, Amendments, or `[wip]`/`[x]` task markers current when it has them.
Do not move or archive the plan.

## 3. Prove the outcome

After each coherent task, ask how you would prove it actually works, then run that proof. Before
reporting, run every applicable command in the plan's Validation section and map every acceptance
criterion to a direct observation. A correction pass also reruns the focused proof for each corrected
finding or CI failure.

Verify at the cheapest authoritative boundary. Build, lint, and type-check are necessary but prove
nothing about runtime, so exercise the real feature path when behavior changed, walk the full
input-to-output path when integration is the claim, read actual state rather than a cached or derived
view of it, and inspect the diff, files, and runtime behavior of delegated work rather than its summary.

Prefer existing deterministic tests and scripts. When none can establish the outcome, create the
smallest repeatable check that can, and commit it only if it carries lasting regression, migration, or
operational value; otherwise record the command and its output in the report. For an evidence-backed
disagreement needing no repository change, run the smallest decisive check and record its output.
Do not manufacture an edit just to create a correction commit.

When verification fails, treat the observation method as a competing hypothesis rather than assuming
the system is wrong. Never report completion with a known failing required check.

## 4. Write the implementation report

Read `templates/implementation-report.md` and write `$PRP_DIR/reports/{plan-name}-report.md` in that
structure. A correction pass updates this same report to the current delivered truth, including review or
CI decisions and new validation and commit evidence, rather than creating a parallel artifact.

This report is the durable handoff across context windows. Record only what a fresh context cannot
recover from the diff, the plan, and the PR: the outcome, the validation evidence, the deviations and
decisions downstream agents must preserve, the finding dispositions, any blocker, and the delivery
links. Do not restate the plan or narrate the work. Keep the plan-based filename and include the
branch; downstream skills discover it themselves.

If implementation or required validation is blocked, mark the report `BLOCKED`, do not commit or open
a PR, and return the concrete blocker.

## 5. Commit, open the PR, update linked context

When initial implementation is green, or a correction changed repository files, invoke `/prp-commit`
for only the work from this plan or correction pass. Record the commit SHA in the report.

- **Initial implementation**: invoke `/prp-pr`, passing any explicit `--base`, the plan's source issue
  and verified `Plan Publication` URL when present, and any tracked follow-up issue links. Let that
  skill resolve the base otherwise.
- **Correction with repository changes**: push without force and verify the existing PR now contains
  the commit. Do not wait for or check CI here; the caller gates CI once on the final head.
- **Evidence-only disagreement**: skip commit and push, verify the PR head SHA is unchanged, and
  record that SHA with the decisive evidence.

Record the PR URL, base, head, and every delivery commit in the report.

If the plan has non-empty `Source PRD` and `PRD Phase`, invoke `/prp-prd-update implemented` with the
PRD path, phase number, plan path, report path, and PR URL. Do not edit the PRD directly.

If committing, pushing, PR creation, or a required PRD update fails, leave the recoverable state
intact, mark the report `BLOCKED`, and return the concrete failure.

## 6. Verify and hand off

Re-read the branch diff, the plan, the report, and the correction input. Confirm the intended work is
complete, unrelated work is untouched, every reported validation result is factual, the commit holds
the intended scope, the PR targets the correct base, and the report exists at the stated absolute path.

Return the implemented outcome, absolute plan path, validation summary, deviations or blocker plus
recovery action, commit, PR URL, tracked follow-ups, conditional PRD update, and absolute report
path. Do not review, merge, move, or archive the plan.

When every required validation and acceptance criterion passes and every required delivery step
succeeds, end the response with exactly `VALIDATION: GREEN`. Otherwise end with `VALIDATION: FAILED`
followed by the concrete blocker or failing output.

## Resources

- `templates/implementation-report.md` — mandatory format for the cross-context implementation handoff
