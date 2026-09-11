# gh recipes per mode

Prefer typed `gh` commands. Fall back to `gh api` or GraphQL only where a typed
command cannot reach. In this skill the operations that need the fallback are:
Project field mutations that need field and option IDs, sub-issue relations,
issue dependencies, and Issue Types. Everything else has a typed command.

Substitute `<owner>`, `<repo>`, and `<project>` from `.github/github-project.yml`
or from the derivation in section 1 of `SKILL.md`.

## Preflight

```bash
gh auth status
gh repo view --json owner,name,nameWithOwner,defaultBranchRef
gh project list --owner <owner> --format json
```

If a Project call fails with an insufficient scope error:

```bash
gh auth refresh -s project,read:project
```

## IDs you need once per session

Project field writes take IDs, not names. Fetch them once and reuse them.

```bash
# Project node id.
gh project view <project> --owner <owner> --format json --jq '.id'

# Field ids and single-select option ids.
gh project field-list <project> --owner <owner> --format json --jq '
  .fields[] | select(.type=="ProjectV2SingleSelectField")
  | {field: .name, id: .id, options: [.options[] | {name, id}]}'
```

Cache these as `PROJECT_ID`, `STATUS_FIELD_ID`, `PRIORITY_FIELD_ID`, and the
option IDs for `Todo`, `In Progress`, `Done`, `P0`, `P1`, `P2`.

If a name from the config file has no matching option, stop and report the
drift. Do not create the option; that is `github-project-setup`'s work.

## draft

No GitHub write. Produce the proposed title and body only. Find the template
first:

```bash
gh api repos/<owner>/<repo>/contents/.github/ISSUE_TEMPLATE --jq '.[].name'
```

A `404` means no template directory, so use `assets/issue-body.md`. Also check
`.github/ISSUE_TEMPLATE/config.yml` for `blank_issues_enabled` and for the forms
that apply.

## create

```bash
# 3. Create.
gh issue create --repo <owner>/<repo> \
  --title "<title>" \
  --body-file /tmp/issue-body.md \
  --label "<label>" \
  --assignee "<login>"
# Capture the printed URL and derive the number from it.

# 4. Add to the Project. Prints the item id.
gh project item-add <project> --owner <owner> --url <issue-url> --format json --jq '.id'

# 5. Priority, then Status.
gh project item-edit --id <item-id> --project-id <PROJECT_ID> \
  --field-id <PRIORITY_FIELD_ID> --single-select-option-id <P1_OPTION_ID>
gh project item-edit --id <item-id> --project-id <PROJECT_ID> \
  --field-id <STATUS_FIELD_ID> --single-select-option-id <TODO_OPTION_ID>

# 7. Read back.
gh issue view <number> --repo <owner>/<repo> \
  --json number,title,url,state,assignees,labels,projectItems
```

Note that `gh issue create --body-file -` reads stdin, which avoids quoting
problems with a multi paragraph body.

### Retrying after a partial failure

Find the Issue before creating anything:

```bash
gh issue list --repo <owner>/<repo> --state all --limit 20 \
  --search "<exact title> in:title" \
  --json number,title,url,state
```

If it exists, resume at the step that failed. Never run `gh issue create` twice
for the same requirement.

### Issue Type

Issue Types are an organization level feature and may not exist.

```bash
gh issue edit <number> --repo <owner>/<repo> --type "<type>"
```

If `--type` is not a flag on the installed `gh`, or the call reports that no
types are defined, report `Type: unset (not configured for this owner)` rather
than failing the run.

## refine and edit

```bash
gh issue view <number> --repo <owner>/<repo> --json number,title,body,labels,assignees,state
# Edit the body in a file, then:
gh issue edit <number> --repo <owner>/<repo> --body-file /tmp/issue-body.md
gh issue edit <number> --repo <owner>/<repo> --title "<title>"
gh issue edit <number> --repo <owner>/<repo> --add-label "<label>" --remove-label "<label>"
gh issue edit <number> --repo <owner>/<repo> --add-assignee "@me"
```

Read the current body before editing and preserve any section the user did not
ask you to change. `--body-file` replaces the whole body, so a partial edit that
drops a section is a data loss bug, not a formatting choice.

## split

Create each child with the `create` recipe, then apply the relations in
`references/issue-relations.md`, then set each child's Project fields. Finally
update the parent body to reference the children.

## relate

See `references/issue-relations.md`.

## prioritize and move

```bash
# Find the item id for an Issue already in the Project.
gh project item-list <project> --owner <owner> --format json --limit 500 --jq '
  .items[] | select(.content.number == <number>) | .id'

gh project item-edit --id <item-id> --project-id <PROJECT_ID> \
  --field-id <PRIORITY_FIELD_ID> --single-select-option-id <OPTION_ID>
```

If the Issue has no item, it is `meta.not-in-project`. Add it first with
`gh project item-add`, then set the field.

## query

```bash
# Issues by state, label, assignee.
gh issue list --repo <owner>/<repo> --state open --limit 200 \
  --json number,title,url,state,assignees,labels,updatedAt

# Everything in the Project with its field values.
gh project item-list <project> --owner <owner> --format json --limit 500 --jq '
  .items[] | {
    type: .content.type,
    number: .content.number,
    title: .content.title,
    state: .content.state,
    status: .status,
    priority: .priority,
    assignees: .assignees
  }'
```

`gh project item-list` returns pull requests and draft items as well as Issues.
Filter on `.content.type == "Issue"` when the question is about requirements.

## close and reopen

```bash
gh issue close <number> --repo <owner>/<repo> \
  --reason completed \
  --comment "Delivered. Acceptance criteria met: <summary>."

gh issue close <number> --repo <owner>/<repo> \
  --reason "not planned" \
  --comment "Cancelled: <why>. Superseded by #<other>."

gh issue reopen <number> --repo <owner>/<repo> --comment "<why>"
```

After a close, re-read the Project item once to see whether automation moved it
to `Done`:

```bash
gh project item-list <project> --owner <owner> --format json --limit 500 --jq '
  .items[] | select(.content.number == <number>) | {status}'
```

If it is still not `Done`, report the lag. Set it by hand only when the user
asks.

## Bulk changes

Print the match count and the full target list before the first write:

```bash
gh issue list --repo <owner>/<repo> --state open --limit 500 \
  --search "<query>" --json number,title --jq 'length'
```

Then iterate, verifying each write, and report failures individually.
