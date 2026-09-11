# The audit rule catalog

Twenty-seven rules with stable IDs. Read all of them before evaluating. Every
rule is reported as findings, passed, or not evaluated with a reason. A rule
you skipped and a rule that passed look identical in a report, which is exactly
the failure this catalog exists to prevent.

Each entry carries: severity, what it detects, how to find it, the expected
state, the suggested action, the owning skill, and whether it is auto-fixable.
`Auto-fixable: yes` means the owning skill can apply the change without a
product decision. It never means this skill applies it (rule 10).

## Collect the data once

```bash
# Every Issue in scope, with the fields the content rules need. This is the
# authority for Issue state; the item list below does not carry it.
gh issue list --repo <owner>/<repo> --state all --limit 500 \
  --json number,title,url,body,state,stateReason,assignees,labels,createdAt,updatedAt,projectItems

# Every item in the Project, with its field values. Includes pull requests and
# draft items, which several rules need. Archived items are excluded: they are
# not live board state, and counting them reports a false
# project.duplicate-item on any Issue that was archived and later re-added,
# and feeds their stale status values to the state rules.
gh project item-list <project> --owner <owner> --format json --limit 500 \
  --jq '.items[] | select(.archive == null)
        | {id, itemType: .content.type, number: .content.number,
           title: .content.title, status, priority, assignees}'

# Project item creation dates, which item-list does not report. Needed only by
# project.long-lived-draft, so run it only when that rule is gated on. Join it to
# the list above on `id`, and take the item type from that list: this query's
# `type` is a GraphQL enum (`DRAFT_ISSUE`), not the `DraftIssue` spelling the
# rules compare against.
gh api graphql -f query='
  query($owner: String!, $number: Int!) {
    organization(login: $owner) {
      projectV2(number: $number) {
        items(first: 100) { nodes { id createdAt } }
      }
    }
  }' -F owner=<owner> -F number=<project>

# The Project's own configuration.
gh project field-list <project> --owner <owner> --format json \
  --jq '.fields[] | {name, type, options: (.options // [] | map(.name))}'

gh api graphql -f query='
  query($owner: String!, $number: Int!) {
    organization(login: $owner) {
      projectV2(number: $number) { workflows(first: 20) { nodes { name enabled } } }
    }
  }' -F owner=<owner> -F number=<project>
```

For a user owned Project, replace `organization(login:)` with `user(login:)`.
If the workflows query fails on the host, the two automation rules are not
evaluated, with that as the reason.

Every collection call above is paged, including the GraphQL `items(first: 100)`.
A result that comes back at exactly its limit is a page, not the collection.
Raise the limit or page through before evaluating anything, and report the number
of objects actually covered. An audit over a truncated collection is clean only
because it never looked.

## Issue state comes from the Issue list, never from the item list

`gh project item-list` emits only `body`, `number`, `repository`, `title`,
`type`, and `url` under `.content`. There is no `.content.state` and no
`.content.createdAt`, so projecting either yields `null` on every item and every
comparison against it silently passes. Never project a `.content` key that is
not one of those six.

Join the two collections on `number` instead. The Issue list carries `state` and
`stateReason`, and each entry's `projectItems[]` carries the `status` value for
every Project the Issue belongs to, identified by the Project `title`. Match on
that title, which is the `title` key under `project` in the config file. Both
state rules read Issue state from this join.

## Body section detection

Detection is heading based. A section counts as present when the body has a level
two heading whose text matches the section, in the repository's own template
wording when one exists, and it has non-empty content under it.

**Strip HTML comments before testing a section for content.** The Issue template
`github-project-setup` writes carries its guidance in an HTML comment under every
heading, so an Issue submitted from that template with nothing filled in has
non-empty bytes under every heading. Remove every `<!-- ... -->` span, including
multi-line ones, then test what is left. Without this step an empty Issue passes
all four rules that look for a missing section, which is the opposite of what
those rules are for.

A heading followed by nothing, by whitespace only, or by `TBD` counts as absent.
`None` also counts as absent, except under `## Non-goals` and
`## Additional context`: both templates this bucket ships instruct the author to
write `None` rather than delete a section, so there `None` is a real answer and
the section counts as present.

---

## Issue content rules

### `issue.missing-background`

- **Severity**: warning
- **Detects**: no background or goal section, or a section that only restates
  the title.
- **Find it**: body has no `## Background and goal` equivalent, or its content
  is under one sentence and shares most of its words with the title.
- **Expected**: a reader learns what is wrong or missing today and why it
  matters.
- **Action**: add the section with the real motivation.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no. The motivation is not recoverable from the Issue.

### `issue.missing-scope`

- **Severity**: warning
- **Detects**: no scope section, so the boundary is not decidable.
- **Find it**: body has no `## Scope` equivalent with content.
- **Expected**: what is included, concrete enough to judge whether a change
  belongs.
- **Action**: add the scope section.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `issue.missing-acceptance-criteria`

- **Severity**: warning
- **Detects**: no acceptance criteria at all.
- **Find it**: body has no `## Acceptance criteria` equivalent, or the section
  contains no `- [ ]` or `- [x]` line.
- **Expected**: a checkbox list of observable conditions.
- **Action**: add criteria a third party can verify without asking the author.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `issue.unverifiable-acceptance-criteria`

- **Severity**: warning
- **Detects**: criteria exist but name activities rather than observable
  outcomes, so nobody can tell when the Issue is done.
- **Find it**: checkbox lines that are an imperative with no observable result,
  for example `Improve performance`, `Refactor the order module`,
  `Investigate the problem`, `Make the UI better`. The test: can you name what
  you would run or look at, and what result counts as a pass?
- **Expected**: every criterion states a condition, not a task.
- **Action**: rewrite each failing criterion as an observable condition.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `issue.missing-non-goals`

- **Severity**: info
- **Detects**: no non-goals section.
- **Find it**: body has no `## Non-goals` equivalent with content.
- **Expected**: the near misses a reader would otherwise assume are included.
- **Action**: add non-goals when the boundary is not obvious from the scope.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `issue.multiple-outcomes`

- **Severity**: warning
- **Detects**: one Issue carrying two or more distinct outcomes, which breaks
  rule 4.
- **Find it**: a title joining two verbs with `and`, a comma, or a slash;
  acceptance criteria covering two surfaces that ship at different times; a
  body where two different people would own different parts.
- **Expected**: one Issue equals one unit of work.
- **Action**: narrow the Issue, or split it when the parts are each
  schedulable.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `issue.should-be-split`

- **Severity**: warning
- **Detects**: an Issue whose parts can be scheduled, assigned, or accepted
  independently.
- **Find it**: any one of: parts assignable to different people; one part
  blocked while another can start; acceptance criteria splitting cleanly into
  disjoint groups by surface or actor; a body listing work items that each
  deserve their own position in the order.
- **Expected**: real parent and child Issues, not a task list in one body.
- **Action**: run the `split` mode of the owning skill.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no. Where to cut is a product decision.

### `issue.undeclared-dependency`

- **Severity**: warning
- **Detects**: the body says the work waits on something, and no `blocked-by`
  relation exists.
- **Find it**: body text matching `blocked by`, `depends on`, `waiting on`,
  `after #`, `once #`, or `needs <team>`, with an empty `blocked_by` list on
  the dependencies endpoint.
- **Expected**: the dependency exists as a relation, not only as prose.
- **Action**: create the `blocked-by` relation. Keep the prose too.
- **Owner**: `github-project-manage`
- **Auto-fixable**: yes, when the referenced Issue number is unambiguous.

### `issue.uninformative-title`

- **Severity**: info
- **Detects**: a title naming an area or a bare verb rather than the outcome.
- **Find it**: titles under about four words, titles that are a single noun, or
  titles like `Bug`, `Fix`, `Improvements`, `Orders`, `Cleanup`.
- **Expected**: the title names what becomes true.
- **Action**: retitle.
- **Owner**: `github-project-manage`
- **Auto-fixable**: yes, when the body makes the outcome unambiguous.

### `issue.suspected-duplicate`

- **Severity**: warning
- **Detects**: two Issues describing the same outcome.
- **Find it**: compare outcomes, not wording, across open and recently closed
  Issues. Strong signals: near identical acceptance criteria, the same affected
  surface with the same goal, or the same linked escalation.
- **Expected**: one Issue per outcome.
- **Action**: report both and let the user decide which to close as
  `not planned` with a link to the survivor. Never merge or close on your own.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `issue.stale`

- **Severity**: info
- **Detects**: an open Issue with no update for longer than the configured
  threshold.
- **Find it**: `updatedAt` older than `audit.stale_days` days.
- **Gate**: evaluated only when `audit.stale_days` is configured or the user
  supplies a threshold. With neither, report the rule as not evaluated and
  suggest setting one. Never invent a default period.
- **Expected**: open work is either moving or deliberately parked.
- **Action**: confirm it is still wanted, or close it as `not planned`. Being
  stale is never on its own a reason to close.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

---

## Issue metadata rules

### `meta.missing-assignee`

- **Severity**: warning
- **Detects**: an Issue with `Status: In Progress` and nobody assigned, or any
  in-scope open Issue unassigned when the repository requires it.
- **Find it**: empty `assignees` on the Issue and on the Project item.
- **Gate**: `audit.require_assignee: true`.
- **Expected**: work in progress has an owner.
- **Action**: assign someone.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no. Who owns it is a human decision.

### `meta.missing-priority`

- **Severity**: warning
- **Detects**: a Project item with no `Priority` value.
- **Find it**: `priority` is null or empty on the item.
- **Gate**: `audit.require_priority: true`.
- **Expected**: every item carries `P0`, `P1`, or `P2`.
- **Action**: set the priority.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `meta.missing-issue-type`

- **Severity**: info
- **Detects**: an Issue with no Issue Type where the owner has types defined.
- **Find it**: the Issue has no type, and the owner returns a non-empty type
  list.
- **Gate**: `audit.require_issue_type: true`. Also not evaluated when the owner
  has no Issue Types configured, with that as the reason.
- **Expected**: every Issue carries a type.
- **Action**: set the type.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `meta.not-in-project`

- **Severity**: error
- **Detects**: an open in-scope Issue that is not an item in the Project, so it
  is invisible to every count and every view.
- **Find it**: the Issue's own `projectItems` carries no entry whose `title` is
  the configured Project title. Decide this from the Issue list, not from the
  item list: `projectItems` travels with the Issue and is not paged, so it cannot
  report a member as absent because a page filled up.
- **Expected**: every in-scope Issue is an item in the Project.
- **Action**: add it, then set `Priority` and `Status`.
- **Owner**: `github-project-manage`
- **Auto-fixable**: yes.

### `meta.nonstandard-priority`

- **Severity**: error
- **Detects**: an item whose `Priority` value is outside `P0`, `P1`, `P2`.
- **Find it**: `priority` is not one of `P0`, `P1`, `P2`. Rule 8 is the only
  owner of this set; there is no configurable alternative.
- **Expected**: rule 8 holds exactly.
- **Action**: set a valid value on the item. If the Project's field itself
  offers the extra option, that is `project.field-option-drift` and belongs to
  the other owning skill.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no. The correct value is a human decision.

### `meta.nonstandard-status`

- **Severity**: error
- **Detects**: an item whose `Status` value is outside `Todo`, `In Progress`,
  `Done`, including any `Blocked` value, which rule 9 forbids, **and an item in
  the Project whose `Status` is unset**. The catalog has no separate rule for a
  missing status, on purpose: an absent value is a non-standard value, because an
  item with no `Status` is invisible on a board grouped by `Status` exactly as a
  `Blocked` item corrupts one.
- **Find it**: `status` is not one of `Todo`, `In Progress`, `Done`, which
  includes null, empty, and absent. Rule 7 is the only owner of this set; there
  is no configurable alternative.
- **Expected**: rule 7 holds exactly, and every item carries one of the three.
- **Action**: for a wrong value, move the item to a valid status; a `Blocked`
  value becomes `Todo` plus a `blocked-by` relation. For an unset value, set
  `Todo` for an open Issue and `Done` for a closed one, and check
  `project.automation-item-added-missing`, which is the usual cause of a whole
  batch of unset values.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

### `meta.relation-conflict`

- **Severity**: error
- **Detects**: contradictory relations: a dependency cycle, an Issue that is
  both parent and child of the same Issue, an Issue blocked by one it also
  blocks, or a child whose parent is closed while the child is still open and
  unlisted.
- **Find it**: walk the `blocked_by` graph for cycles; compare the sub-issue
  graph against itself for reciprocal edges.
- **Expected**: the relation graph is acyclic and each pair has one direction.
- **Action**: remove the edge the user names. Report the cycle; never break it
  on your own.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no

---

## Issue and Project state rules

### `state.closed-not-done`

- **Severity**: error
- **Detects**: a closed Issue whose Project item is `Todo` or `In Progress`, so
  the board over-counts open work.
- **Find it**: in the Issue-list-to-item join, `state` is `CLOSED` and `status`
  is not `Done`.
- **Expected**: closed Issues are `Done`.
- **Action**: re-read once first, since the `Item closed` automation is not
  instant. If it persists across several Issues, the workflow is off and the
  real finding is `project.automation-item-closed-missing`.
- **Owner**: `github-project-manage`
- **Auto-fixable**: yes, per item. Fixing the workflow is the durable fix.

### `state.open-in-done`

- **Severity**: error
- **Detects**: an open Issue whose Project item is `Done`, so the board
  under-counts open work.
- **Find it**: in the Issue-list-to-item join, `state` is `OPEN` and `status` is
  `Done`.
- **Expected**: only closed Issues are `Done`.
- **Action**: decide which is true. Either close the Issue, or move the item
  back to `Todo` or `In Progress`.
- **Owner**: `github-project-manage`
- **Auto-fixable**: no. Which side is right is a human decision.

---

## Project structure and workflow rules

### `project.contains-pull-request`

- **Severity**: error
- **Detects**: a pull request added as a Project item, which breaks rule 3 and
  makes every count describe delivery artifacts rather than requirements.
- **Find it**: `itemType` is `PullRequest` on any item.
- **Expected**: the Project holds Issues only.
- **Action**: remove the item from the Project. The pull request itself is
  untouched. Then check the Auto-add filter, which is usually the cause.
- **Owner**: `github-project-setup`
- **Auto-fixable**: yes, removing the item. Removal needs an explicit request.

### `project.long-lived-draft`

- **Severity**: warning
- **Detects**: a draft item that has never become a real Issue, so it has no
  URL, no comments, and no acceptance criteria.
- **Find it**: `itemType` is `DraftIssue` in the item list, and the same item's
  `createdAt`, joined on `id` from the GraphQL items query in the collection
  block, is older than `audit.draft_age_days` days.
- **Gate**: evaluated only when `audit.draft_age_days` is configured or the user
  supplies a threshold. With neither, report the rule as not evaluated and
  suggest setting one. Never invent a default period, and never borrow
  `audit.stale_days`: that key is days without an *update* and is read against
  `updatedAt` by `issue.stale`, while this rule measures age from creation. One
  number against two clocks answers two different questions.
- **Expected**: drafts are converted or deleted, not parked.
- **Action**: convert it to an Issue, or delete it.
- **Owner**: `github-project-setup`
- **Auto-fixable**: no

### `project.duplicate-item`

- **Severity**: error
- **Detects**: the same Issue present as two items, so it is counted twice.
- **Find it**: group the items by `number` and report any group above one.
- **Expected**: one item per Issue.
- **Action**: remove the extra items, keeping the one with field values set.
- **Owner**: `github-project-setup`
- **Auto-fixable**: yes, with an explicit request.

### `project.missing-field`

- **Severity**: error
- **Detects**: the Project has no `Status` field or no `Priority` field, so
  every metadata rule below it is unevaluable.
- **Find it**: the field list has no entry with that name and type
  `ProjectV2SingleSelectField`.
- **Expected**: both fields exist as single selects.
- **Action**: create the missing field with its exact option set.
- **Owner**: `github-project-setup`
- **Auto-fixable**: yes.

### `project.field-option-drift`

- **Severity**: error
- **Detects**: a `Status` or `Priority` field whose option set is not exactly
  the required one, including case and spacing. `In progress` is drift.
- **Find it**: compare the option names to `Todo`, `In Progress`, `Done` and to
  `P0`, `P1`, `P2`. These literals are rules 7 and 8, and they are the same
  literals `meta.nonstandard-status` and `meta.nonstandard-priority` compare
  against, so the three rules can never disagree about the same field.
- **Expected**: rules 7 and 8 hold exactly, with no extra options.
- **Action**: correct the option set. Report which items would lose a value,
  because replacing the option list removes anything omitted, and renaming an
  option rewrites it on every item that holds it.
- **Owner**: `github-project-setup`
- **Auto-fixable**: no. It is destructive and needs confirmation.

### `project.automation-item-added-missing`

- **Severity**: warning
- **Detects**: the `Item added to project` workflow is absent or disabled, so
  new items arrive with no status and disappear from a board grouped by it.
- **Find it**: the workflows query has no enabled workflow with that name.
- **Expected**: enabled, setting `Todo`.
- **Action**: enable and configure it. This is a web UI operation; the API
  cannot write it.
- **Owner**: `github-project-setup`
- **Auto-fixable**: no

### `project.automation-item-closed-missing`

- **Severity**: warning
- **Detects**: the `Item closed` workflow is absent or disabled, which produces
  `state.closed-not-done` on every closed Issue.
- **Find it**: the workflows query has no enabled workflow with that name.
- **Expected**: enabled, setting `Done`.
- **Action**: enable and configure it. This is a web UI operation; the API
  cannot write it.
- **Owner**: `github-project-setup`
- **Auto-fixable**: no

---

## Notes on evaluation

The workflows query returns each workflow's enabled flag but not its configured
target value, so these two rules can confirm that a workflow is on and cannot
confirm that it sets the right value. Say so in the finding rather than
overclaiming.

When many Issues produce the same structural finding, report the rule once with
the full object list rather than one block per Issue, and name the single
underlying cause when there is one. A backlog with forty
`state.closed-not-done` findings has one problem, not forty.
