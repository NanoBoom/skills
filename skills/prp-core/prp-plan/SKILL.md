---
name: prp-plan
description: Creates an implementation-ready plan for a feature, bug fix, refactor, or chore from a PRD, issue, document, or description using codebase evidence, first-principles reasoning, and conditional root-cause analysis, research, or spikes. Publishes issue-derived plans back to their source issue. Use when the user asks to "plan this feature", "plan this bug fix", "plan issue X", "create an implementation plan", "turn this PRD into a plan", investigate how a change should be built, link related plans, or invokes /prp-plan.
argument-hint: <feature description | path/to/prd.md> | update-references <plan-path> <related-plan-path> [back|forward]
---

# PRP Plan

Produce a plan a human can scan and an implementation agent can execute without rediscovering the
design. Identify the invariant, find the existing primitives, and choose the smallest solution the
evidence supports.

Plan only. Do not implement, commit, or open a PR. A spike is allowed only to settle an architectural
hinge; its code stays throwaway under the `prp-spike` contract.

**Input**: $ARGUMENTS (if absent, use the conversation.)

## Mode

- Linking two existing plans → `workflows/update-references.md`, then stop.
- `publish <existing .plan.md>` → publish or refresh that plan on its recorded source issue, update
  `Plan Publication`, verify the shared comment, stop. Do not redesign it unless asked to revise it.
- A bug, stack trace, regression, or unexplained current behavior → establish the cause before
  designing the fix (step 3).
- Everything else → an implementation plan.

## 1. Resolve the request

Accept a PRD path, an issue reference or URL, another document, free-form text, or the conversation.

**From a PRD**: select the first pending phase whose dependencies are complete, preserve its problem,
user, hypothesis, scope, and success signal, plan only that phase, and tell the user which one you
picked.

**From a tracker issue** (GitHub, Jira, Linear, or whatever access the environment already has;
this skill does not configure a client): the body is the starting point, not the brief. Follow the
comments, linked issues, blocking relations, duplicates, PRs, specs, and attachments that can still
change scope, intent, constraints, or decisions, including earlier published PRP plans and the
corrections after them, and stop once more material stops changing the plan. Separate current
decisions from superseded discussion, note unresolved disagreements, and keep the required outcome
separate from any implementation the issue merely suggests. Curate; do not dump the tracker graph. If
decision-relevant context cannot be retrieved, say what is missing and ask; never infer it.

From any input, establish the problem and user outcome, who is affected, the observable invariant
that must hold, the success signal that would show the outcome improved, the genuinely fixed
constraints, and whether a proposed implementation is required or only suggested.

Do not invent personas, business value, or vanity metrics. When the affected user, problem, outcome,
or any meaningful success signal is materially uncertain, stop and settle product intent before
architecture turns the assumption into code. Otherwise ask only when the ambiguity would produce
materially different plans.

## 2. Gather codebase evidence

Read repository guidance and discover the actual project structure. Do not assume `src/`, a
framework, or a validation stack.

Read the project's sidecars when they exist: `direction.md` for product direction and scope,
`engineering.md` for the standard work is checked against. They live wherever repository guidance
says, or find them by name with `git ls-files`. Absence is normal; never create them. Product
direction bounds what this plan may propose, and a proposal that contradicts it needs the user's
decision before it becomes tasks.

For a non-trivial code change, launch these in parallel, adapting the prompts in
`references/agent-prompts.md`:

- `prp-core:codebase-explorer` — where the concern lives: files, analogous behavior, tests,
  configuration, existing primitives, and the repository's real validation commands.
- `prp-core:codebase-analyst` — how the current behavior actually works: control flow, data flow,
  state ownership, contracts, observable effects.
- `prp-core:root-cause-analyzer` — for broken behavior only; see step 3.

Subagent dispatch needs the installed `prp-core` plugin; without it, gather the same evidence
inline. For a small documentation, configuration, or narrowly localized change, skip the agents and
inspect directly. Either way the planner owns synthesis and reads the decisive files itself.

Keep the evidence that decides something: precise `file:line` references, the primitives and
extension points available, the closest useful precedent and where it varies, the authoritative
validation commands, the conventions worth preserving, and the awkward seams or missing primitives
this feature would otherwise work around. A known-poor local convention is not a reason to repeat it.

## 3. Establish the cause for broken behavior

For a bug, error, regression, stack trace, or unexplained behavior, do not plan from the report's
assumed cause. Give the root-cause agent the original symptom and tracker context without a preferred
fix, and consume its evidence alongside the explorer and analyst results.

The plan needs a reproducible observation where one is reasonably possible, the causal chain, the
rejected alternatives, the smallest responsible fix boundary, and a regression check. If the
diagnosis stays conditional, surface the missing evidence at the design gate rather than disguising
an unproven cause as an implementation task.

The planner does not create issues, edit issue bodies, or publish diagnosis through `/prp-debug`. Its
only tracker write is step 7.

## 4. Choose the smallest supported design

Challenge the first plausible design. Which existing primitive comes closest to the required
outcome, and can configuration, composition, or a small extension get there? Name the assumption
that forces new state, lifecycle, abstraction, or subsystem, and justify it by the invariant it
protects rather than by future need. Get the data shape and its owner right before the logic around
them. Prefer the smallest valuable vertical slice: it must deliver or directly unlock the user
outcome, not just leave behind an elegant primitive.

Read `references/planning-craft.md` when the design is contested, a primitive looks missing, or
ownership of state is unclear.

Research or spike only when it can change the plan. Use `prp-core:web-researcher` for a narrow
question about current documentation, dependency versions, platform behavior, or security guidance
that decides the design, preferring primary sources. Delegate `/prp-spike` to a separate agent, using
the prompt in `references/planning-craft.md` → **Decide when to spike**, when an uncertain,
falsifiable claim materially changes the architecture; wait for its verdict, then consume it. Never
build the spike in this context or copy spike code into the plan as production code.

## 5. Hold the design gate

Before writing the plan, state the recommended approach and its evidence. Stop and ask the user when
a missing primitive should probably be built first, when product intent or the success signal is too
uncertain to justify implementation, when the evidence contradicts the requested implementation, when
the simpler solution changes the intended product contract, or when an unresolved decision would
produce a substantially different plan.

Explain the invariant, the discovery, the recommendation, and what the alternatives cost. Do not bury
a load-bearing decision in the artifact. A minor uncertainty may stay in the plan only with a
recommendation, its evidence, and the consequence of choosing differently.

## 6. Write the plan

```bash
# --- PRP store resolver (canonical; keep byte-identical across skills) ---
# Store is `.prp/` in the checkout root. --show-toplevel gives every worktree its
# own store; the store gitignores itself. PRP_DIR relocates it.
_root="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_root" ] || _root="$PWD"
_root="$(cd "$_root" && pwd -P)"
PRP_DIR="${PRP_DIR:-$_root/.prp}"
mkdir -p "$PRP_DIR"; [ -f "$PRP_DIR/.gitignore" ] || printf '*\n' > "$PRP_DIR/.gitignore"
mkdir -p "$PRP_DIR/plans"
```

Read `templates/plan-template.md` and `references/task-format.md`, then save to
`$PRP_DIR/plans/<kebab-case-name>.plan.md`. Keep the template's required spine, assign a stable plan
ID and reuse it when revising the same plan, and set the source metadata when planning from a PRD or
tracker; that metadata is how downstream skills find the plan, so there is no separate index to
drift. Include conditional sections only when they add information.

Write in plain, concrete language using the repository's exact terms, one name per concept. State
each fact once: this plan is re-read in full on every implementation and correction pass and
published verbatim to the source issue, so a sentence repeated across sections is paid for many
times. The template scopes the sections that would otherwise overlap; follow those scopes.

Add a diagram from `references/visuals.md` when it makes the change easier to verify: before/after
for an interaction or user-flow change, architecture for a change in structure, ownership, state, or
data flow.

When existing users, behavior, or stored data can be affected, add one compact Delivery
Considerations section covering only what applies.

Tasks describe outcomes in dependency order, each naming its files and integration points, the
applicable precedent, the implementation detail, the tests, and its focused validation. Acceptance
criteria state the observable completed behavior once; the validation gates prove them with commands
verified in this repository. Every requested outcome must be covered and every validation owned. If
something cannot be completed in this implementation, resolve the scope with the user before
presenting the plan as ready.

## 7. Publish, verify, hand off

If the input came from an issue, or `publish` mode supplied an issue-derived plan, publish the
complete rendered plan to that issue. Prefix the body with `<!-- prp-plan-id: <plan-id> -->`, record
its stable comment URL as `Plan Publication` in the local plan, and read the issue back to verify the
complete final plan is there. Refreshing the same plan ID updates that marked comment rather than
adding a duplicate. If publication or verification fails, keep the local plan and report the blocker;
do not claim the shared handoff is complete.

Before reporting, confirm the plan holds up:

- the invariant, recommendation, and evidence are explicit, with real paths and line numbers, and
  implementation acceptance is distinct from the product success signal;
- a bug-fix plan states the proven causal chain, fix boundary, and regression proof, or surfaces the
  evidence still missing;
- tasks cover the agreed scope, execute top to bottom, and own every applicable delivery concern;
- validation commands exist in this project and prove the integrated outcome, not just syntax;
- open decisions carry recommendations and none silently changes the architecture;
- no placeholders, generic examples, confidence scores, or coverage targets remain.

If the input came from a PRD, invoke `/prp-prd-update planned` with the PRD path, selected phase, and
absolute plan path, then verify the phase is `in-progress` and links to the plan.

Report using `templates/report-format.md`.

## Resources

- `references/planning-craft.md` — invariant, primitive, simplicity, spike, and decision-gate reasoning
- `references/agent-prompts.md` — prompts for the planner's evidence-gathering agents
- `references/task-format.md` — implementation task content and sizing
- `references/visuals.md` — conditional UX and architecture diagrams
- `templates/plan-template.md` — the plan artifact
- `templates/report-format.md` — concise user handoff
- `workflows/update-references.md` — bidirectional plan linking mode
