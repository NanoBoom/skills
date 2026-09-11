# The field and view model

The whole model is two single select fields and two views. Everything else the
Project could hold belongs in the Issue.

## Fields

| Field | Type | Options, in this order | Purpose |
|---|---|---|---|
| `Status` | single select | `Todo`, `In Progress`, `Done` | Where the work is. Written by automation, and by hand only for `In Progress`. |
| `Priority` | single select | `P0`, `P1`, `P2` | What to pick up next. Always set by hand. |

`Title`, `Assignees`, `Labels`, `Repository`, `Milestone`, and `Linked pull
requests` come with every Project and need no setup. `Status` is created by
GitHub on a new Project with the default options `Todo`, `In Progress`, `Done`,
which already match, so the usual work is verification rather than creation.

There is no `Blocked` option and there never is one. A block lives in the Issue
and in the dependency relation. Adding `Blocked` splits the meaning of the board
and makes the `Todo` count wrong, which is why the audit catalog treats a
non-standard status option as an error rather than a preference.

### Semantics

- `Todo`: accepted into the backlog, not started. A blocked Issue sits here.
- `In Progress`: someone is actively working on it now. Set together with an
  Assignee, and only when the user says they are starting.
- `Done`: the Issue is closed. Set by automation on close.

`P0` is drop everything. `P1` is planned for the current cycle. `P2` is
everything else that is still real work. Three levels is deliberate: a scale
with more levels stops being used consistently and stops ordering anything.

## Reading the current state

```bash
# Does a Project exist for this owner, and which are linked here?
gh project list --owner <owner> --format json --jq '.projects[] | {number, title, url, closed}'

# Project node id, needed for every field mutation.
gh project view <project> --owner <owner> --format json --jq '{id, title, number, url}'

# Fields, with single select option names and ids.
gh project field-list <project> --owner <owner> --format json --jq '
  .fields[] | {name, id, type, options: (.options // [] | map(.name))}'
```

Compare the reported option names to the table above, exactly, including case
and spacing. `In progress` is drift, not a match.

## Creating what is missing

```bash
# Create and link a Project.
gh project create --owner <owner> --title "<title>" --format json --jq '{number, url, id}'
gh project link <project> --owner <owner> --repo <owner>/<repo>

# Create the Priority field.
gh project field-create <project> --owner <owner> \
  --name "Priority" \
  --data-type SINGLE_SELECT \
  --single-select-options "P0,P1,P2"

# Create a Status field, only if the Project somehow has none.
gh project field-create <project> --owner <owner> \
  --name "Status" \
  --data-type SINGLE_SELECT \
  --single-select-options "Todo,In Progress,Done"
```

`--single-select-options` takes one comma separated string. Option names
containing a comma are not expressible; do not use any.

## Repairing option drift

`gh` has no typed command to add an option to an existing single select field.
Use the GraphQL mutation, which replaces the whole option list:

`-f` and `-F` send scalars. A `[ProjectV2SingleSelectFieldOptionInput!]!`
variable bound with either is rejected as "expected to be a key-value object"
before the request reaches field validation, so the option list has to travel as
real JSON. Send the whole payload on stdin with `--input -`:

```bash
cat <<'JSON' | gh api graphql --input -
{
  "query": "mutation($field: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) { updateProjectV2Field(input: { fieldId: $field, singleSelectOptions: $options }) { projectV2Field { ... on ProjectV2SingleSelectField { id name options { id name } } } } }",
  "variables": {
    "field": "<FIELD_ID>",
    "options": [
      {"name": "Todo", "color": "GRAY", "description": ""},
      {"name": "In Progress", "color": "YELLOW", "description": ""},
      {"name": "Done", "color": "GREEN", "description": ""}
    ]
  }
}
JSON
```

With `--input -`, `query` and `variables` are the two keys of one JSON document,
and every variable keeps its real type. The same applies to any other non-scalar
variable: a list or an input object cannot be bound with `-f`.

Three things to know before running it:

1. **The list replaces the existing one.** Any option you omit is removed, and
   every item carrying it loses its value. List every option you intend to keep.
2. **Renaming is a rewrite.** Changing `In progress` to `In Progress` changes
   the displayed value on every item that holds it. Say so and confirm first.
3. **Removing an option is a deletion.** The skill's boundaries forbid it
   without an explicit request. Report the extra option as drift and let the
   user decide.

If the mutation is rejected or the schema differs on the host, stop and report
the web UI path: the Project page, then the field header menu, then `Edit
values`.

## Views

| View | Layout | Grouped or sorted by | Purpose |
|---|---|---|---|
| `Board` | board | grouped by `Status` | The working view. Three columns. |
| `Backlog` | table | sorted by `Priority`, then by creation date | The planning view. |

GitHub's public API does not offer a reliable way to create or configure a
Project view. `gh project view --web` opens the Project; view creation is a web
UI operation.

Read the existing views to report them:

```bash
gh api graphql -f query='
  query($owner: String!, $number: Int!) {
    organization(login: $owner) {
      projectV2(number: $number) {
        views(first: 20) { nodes { name layout } }
      }
    }
  }' -F owner=<owner> -F number=<project>
```

For a user owned Project, replace `organization(login:)` with `user(login:)`.
If both fail, report the views as `needs web UI` rather than guessing.

When a view is missing, report it with the exact steps:

1. Open `https://github.com/orgs/<owner>/projects/<number>` (or
   `https://github.com/users/<owner>/projects/<number>` for a user Project).
2. Click `+` beside the view tabs, then `New view`.
3. For `Board`: set the layout to Board, set `Group by` to `Status`, rename the
   view to `Board`, then save.
4. For `Backlog`: set the layout to Table, set `Sort by` to `Priority`
   ascending, rename the view to `Backlog`, then save.

Never report a view as created unless a read back shows it.
