# Report formats

The rules every audit output obeys. The copy-ready skeletons for the three
modes live in `assets/audit-report.md`. Read this file for the rules, then copy
the skeleton for the mode you are in.

## The per-finding block

Every finding carries all eight fields. None is optional, and none is left for
the reader to infer.

```markdown
### [<severity>] <rule-id> - <object>

- Current: <what is true now, read from GitHub>
- Expected: <what the rule requires>
- Action: <the concrete change, in the imperative>
- Fix with: <github-project-manage | github-project-setup>
- Auto-fixable: <yes | no><, with the condition when it is conditional>
```

- `<severity>` is `error`, `warning`, or `info`, taken from the catalog and
  never re-ranked to make a report look better or worse.
- `<object>` is `#<number> <title>` for an Issue, `item <id>` for a draft or a
  pull request item, or `field Status` for a Project field.
- `Current` is read back from GitHub, never restated from the request or from
  what a previous run reported.
- `Action` says what to change. It never says it was changed, and it never
  reads as a completed fix (rule 10).
- `Fix with` is the owning skill from the catalog. It is what makes the report
  actionable without a fix mode.

Worked example:

```markdown
### [error] state.closed-not-done - #142 Export orders CSV completes for large accounts

- Current: Issue is CLOSED, Project item Status is In Progress
- Expected: closed Issues are Done
- Action: move item 142 to Done, or enable the Item closed workflow, which is
  the cause if other closed Issues show the same thing
- Fix with: github-project-manage
- Auto-fixable: yes, per item
```

## Grouping repeated findings

When one rule fires on many objects with one underlying cause, use a single
block with an object list rather than one block per object:

```markdown
### [error] state.closed-not-done - 14 Issues

- Objects: #101, #104, #108, #112, #115, #118, #120, #123, #127, #130, #133,
  #136, #139, #142
- Current: all closed, all still Todo or In Progress
- Expected: closed Issues are Done
- Action: enable and configure the Item closed workflow, then correct the 14
  existing items
- Fix with: github-project-setup, then github-project-manage
- Auto-fixable: no for the workflow, yes per item
```

Forty findings that share one cause are one problem. Reporting them forty times
buries the cause.

## Ordering

Errors first, then warnings, then info. Within one severity, order by rule ID,
so two runs of the same audit are comparable line by line.

## Rules not evaluated

This section is never omitted and never left empty when a rule was gated off or
unevaluable. A rule that was skipped and a rule that passed look identical
otherwise, which is the whole failure this section prevents. One line each, with
what would enable it:

```markdown
- issue.stale: the stale threshold is not configured and none was supplied.
  Set audit.stale_days to enable it.
- meta.missing-issue-type: the owner has no Issue Types defined.
- project.automation-item-added-missing: the workflows query is unavailable on
  this host.
```

## Rollups in `report` mode

Rollups come before the findings, not after: the reader wants the shape first.
Three rollups, by severity, by assignee, and by rule.

Counts must agree across all three rollups and with the finding list. A rollup
that does not add up is worse than no rollup, because it is believed. Two counts
differ on purpose and must be labelled: `Findings` counts blocks, `Objects`
counts distinct Issues and items, and a grouped block contributes one finding
and many objects.

A Project item with no Issue, a draft, or a pull request item has no assignee
and belongs in the `unassigned` row. Add a line under the table saying so when
that row is large enough to mislead.

`What to do first` lists at most five actions, ordered by severity and then by
how many findings each one clears, and names the skill to invoke for each. When
there are no errors and no warnings, write `Nothing. No errors or warnings.`

## `verify` mode

`verify` re-checks only the named Issues or rule IDs. Its job is to say whether
a fix worked, so it reports four buckets and never silently re-audits the whole
Project.

`Newly introduced` is the bucket that earns the mode. A fix that clears
`meta.not-in-project` by adding an item, and leaves that item with no
`Priority`, has traded an error for a warning, and the report has to say so.

`Not re-checked` exists so a narrow verification is never read as a clean audit.

If a named object no longer exists, say that rather than reporting it as
resolved. A deleted Issue is not a fixed Issue.
