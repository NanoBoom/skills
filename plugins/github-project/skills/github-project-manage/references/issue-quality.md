# Issue quality: the executability check and the split criteria

Read this before creating an Issue, before refining one, and before deciding
whether to split one.

## The executability check

An Issue passes when a competent person who was not in the conversation can pick
it up, deliver it, and prove it is done, without asking the author a question.
Check all six.

### 1. One outcome

The Issue describes a single thing that becomes true. Signals that it is really
two or more:

- The title contains `and`, a comma joining two verbs, or a slash.
- The acceptance criteria cover two surfaces that ship at different times.
- Two different people would naturally own different parts.
- Part of it is blocked and part of it is not.

Failing this is `issue.multiple-outcomes`. If the parts are each schedulable,
it is also `issue.should-be-split`.

### 2. Background and goal

A reader learns what is wrong or missing today and why fixing it matters. Not a
restatement of the title. Not a design. If the goal is only inferable from the
title, that is `issue.missing-background`.

### 3. Scope that makes the boundary decidable

What is included, named concretely enough that a reviewer can tell whether a
change belongs. Missing scope is `issue.missing-scope`.

### 4. Verifiable acceptance criteria

A checkbox list. Each line states an observable condition, not an activity.

Verifiable:

- `[ ] A user with no assigned issues sees the empty state, not a spinner.`
- `[ ] POST /orders with a missing customer_id returns 422 and an error body.`
- `[ ] The nightly export completes for a 500k row account in under 10 minutes.`

Not verifiable:

- `[ ] Improve performance.`
- `[ ] Refactor the order module.`
- `[ ] Make the UI better.`
- `[ ] Investigate the problem.`

A criterion is verifiable when you can name the observation that settles it:
what you run or look at, and what result counts as pass. Criteria that fail
this are `issue.unverifiable-acceptance-criteria`. No criteria at all is
`issue.missing-acceptance-criteria`.

An activity is acceptable as a criterion only when the activity itself is the
deliverable, for example a written decision record, and the criterion names the
artifact.

### 5. Non-goals

The near misses a reader would otherwise assume are included. Absent non-goals
are only `issue.missing-non-goals`, which is advisory, but they are the cheapest
way to prevent scope drift and are worth adding whenever the boundary is not
obvious.

### 6. A title that names the outcome

Good: `Export orders CSV completes for accounts over 500k rows`.
Weak: `Export improvements`, `Fix the exporter`, `Orders`, `Bug`.

A title naming only an area or a verb with no object is
`issue.uninformative-title`.

## The split criteria

Split when any one of these is true.

| Signal | Why it forces a split |
|---|---|
| Two or more parts can be scheduled independently | Each needs its own position in the order |
| Two or more parts would be assigned to different people | One assignee field cannot hold both |
| One part is blocked and another can start now | One status cannot describe both |
| Parts would be accepted at different times | Closing the Issue would misreport the rest |
| The acceptance criteria split cleanly into disjoint groups by surface or actor | The groups are already separate units |
| Delivering all of it in one review would be unreviewable | Review size is a real scheduling constraint |

Do not split when:

- the parts only make sense delivered together and would be accepted together;
- the split would produce a child with no independent acceptance criteria;
- the only motivation is that the body is long.

## Shaping a split

1. The parent keeps the outcome, the background, and the acceptance criteria
   that only the whole delivers. It is not a container with an empty body.
2. Each child gets its own background, scope, acceptance criteria, and
   non-goals. A child whose body is one line is not a child, it is a task.
3. Order the children with `blocked-by` only where the order is real. Invented
   ordering removes parallelism.
4. Every child goes into the Project with its own `Priority`. A child inherits
   nothing automatically.
5. The parent stays open until every child is closed and the parent's own
   acceptance criteria are met.

## Duplicates and staleness

Before creating, search open and recently closed Issues for the same outcome.
Match on the outcome, not on wording. A near match is
`issue.suspected-duplicate`: report it and let the user decide, do not close or
merge anything.

An Issue with no update for longer than the configured threshold is
`issue.stale`. It is advisory and never a reason to close on its own.

## Undeclared dependencies

When the body says the work waits on something, needs another team, or follows
another change, and no `blocked-by` relation exists, that is
`issue.undeclared-dependency`. When what it waits on is another Issue, create
the relation rather than leaving the dependency as prose. When it has no Issue
to relate to, keep the prose and move the item to `Blocked` with the `move`
transaction, which writes the `Waiting on:` line.
