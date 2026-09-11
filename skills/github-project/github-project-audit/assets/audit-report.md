# Copy-ready output skeletons

Three skeletons, one per mode. Copy the one that matches the mode and fill every
placeholder. `references/report-formats.md` holds the rules these skeletons
obey: the eight per-finding fields, the ordering, and the grouping.

Delete no heading. A heading with `None` under it says the check ran and found
nothing. A missing heading says nothing at all, and the reader cannot tell the
difference between a clean result and a skipped one.

## audit

```markdown
## Audit

Repository: <owner>/<repo>
Project: <title> #<number>
Mode: audit
Scope: <n> Issues, <m> Project items, <what was included>

## Findings

### [<severity>] <rule-id> - <object>

- Current: <what is true now, read from GitHub>
- Expected: <what the rule requires>
- Action: <the concrete change, in the imperative>
- Fix with: <github-project-manage | github-project-setup>
- Auto-fixable: <yes | no>

## Rules not evaluated

- <rule-id>: <why, and what would enable it>

## Additional observations

<Real problems no catalog rule covers, marked as outside the catalog, or "None".>

## Assumptions

<Derived values when the repository config file was absent, or "None".>
```

## report

```markdown
## Issue management report

Repository: <owner>/<repo>
Project: <title> #<number>
Period: <what was covered>
Scope: <n> Issues, <m> Project items

## By severity

| Severity | Findings | Objects |
|---|---|---|
| error | <n> | <n> |
| warning | <n> | <n> |
| info | <n> | <n> |

## By assignee

| Assignee | error | warning | info | Total |
|---|---|---|---|---|
| <login> | <n> | <n> | <n> | <n> |
| unassigned | <n> | <n> | <n> | <n> |

## By rule

| Rule | Severity | Count | Fix with |
|---|---|---|---|
| <rule-id> | <severity> | <n> | <owning skill> |

## What to do first

1. <Action, the skill to invoke, and how many findings it clears.>

## Findings

<Per-finding blocks, errors first, then warnings, then info.>

## Rules not evaluated

- <rule-id>: <why>
```

## verify

```markdown
## Verification

Repository: <owner>/<repo>
Project: <title> #<number>
Re-checked: <the rule ids and objects that were named>

## Resolved

- <rule-id> - <object>: <what is true now that satisfies the rule>

## Still failing

<Per-finding blocks, unchanged format.>

## Newly introduced

<Per-finding blocks for anything that was not failing before and is now, inside
the re-checked scope.>

## Not re-checked

<Anything in the original findings that was outside the named scope, so this is
not read as a clean audit.>
```
