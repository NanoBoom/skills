# Built-in Project automations

Three workflows carry the whole status model. Two are required. One is optional
but is what keeps rule 3 true without anyone policing it.

| Workflow | Effect | Required |
|---|---|---|
| `Item added to project` | Sets `Status` to `Todo` | Yes |
| `Item closed` | Sets `Status` to `Done` | Yes |
| `Auto-add to project` | Adds matching new Issues to the Project | Optional |

With the first two enabled, nobody sets `Todo` or `Done` by hand, and the board
stays true without maintenance. `In Progress` is the only value a person sets,
and that is correct: it is the only one that carries a human decision.

## What the API can and cannot do

**Read: partially.** The GraphQL `ProjectV2` type exposes `workflows`, which
gives each workflow's `name`, `number`, and `enabled` flag. It does not expose
the configured target value, so a read can tell you that
`Item added to project` is enabled but not that it sets `Todo` rather than
something else.

**Write: no.** There is no public mutation to create, configure, or enable a
built-in Project workflow. Do not attempt one, and never report one of these as
configured on the strength of a call that did not read back.

So: read what you can, report the rest as `needs web UI`, and give the steps.

## Reading the workflow state

```bash
gh api graphql -f query='
  query($owner: String!, $number: Int!) {
    organization(login: $owner) {
      projectV2(number: $number) {
        workflows(first: 20) { nodes { id name number enabled } }
      }
    }
  }' -F owner=<owner> -F number=<project>
```

For a user owned Project, replace `organization(login:)` with `user(login:)`.

Report each of the three as one of:

- `enabled` when the query returns it with `enabled: true`. Add
  `target value not verifiable through the API` so the report does not overclaim.
- `disabled` when the query returns it with `enabled: false`.
- `needs web UI` when the query fails, the field is unavailable on the host, or
  the workflow is absent from the result.

## Configuring them, which is a web UI operation

Open the Project, then the `...` menu at the top right, then `Workflows`.

### Item added to project

1. Select `Item added to project`.
2. Under `When`, leave the default.
3. Under `Set value`, choose `Status`, then `Todo`.
4. Save, then toggle the workflow on.

### Item closed

1. Select `Item closed`.
2. Under `Set value`, choose `Status`, then `Done`.
3. Save, then toggle the workflow on.

### Auto-add to project

1. Select `Auto-add to project`.
2. Choose the repository.
3. Set the filter to exactly `is:issue`.
4. Save, then toggle the workflow on.

The `is:issue` filter is the point. Without it the workflow adds pull requests,
which breaks rule 3, produces `project.contains-pull-request` findings on every
audit, and makes the Todo and Done counts describe delivery artifacts rather
than requirements. If the user does not want Auto-add, that is fine; Issues are
then added by `github-project-manage` at creation time.

## After configuring

Verify by behavior, not by belief. Ask the user to confirm with one real Issue,
or do it yourself when the user asks:

1. Create or pick a throwaway Issue in the repository.
2. Add it to the Project and read the item's `Status`. It should be `Todo`.
3. Close the Issue, wait a few seconds, and re-read. It should be `Done`.

```bash
gh project item-list <project> --owner <owner> --format json --limit 500 --jq '
  .items[] | select(.content.number == <number>) | {number: .content.number, status}'
```

Automation is not instant. A single read immediately after the close can show
the old value. Re-read once before reporting a workflow as broken.

## When a workflow is off

Say so plainly and say what it costs:

- `Item added to project` off: new items arrive with no `Status`, so they are
  invisible on a board grouped by `Status`, and the audit reports them.
- `Item closed` off: closed Issues stay in `Todo` or `In Progress`, which is
  `state.closed-not-done` on every audit and makes the board's counts wrong.

Never compensate for a disabled workflow by setting the field by hand across the
Project. That hides the real problem and has to be repeated forever. Report it,
and fix the workflow.
