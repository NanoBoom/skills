# gh recipes per mode

Prefer typed `gh` commands. Fall back to `gh api` or GraphQL only where a typed
command cannot reach. In this skill the operations that need the fallback are:
Project field mutations that need field and option IDs, sub-issue relations,
issue dependencies, and Issue Types. Everything else has a typed command.

Substitute `<owner>`, `<repo>`, and `<project>` from `.github/github-project.yml`
or from the derivation in section 1 of `SKILL.md`.

## Every list call is paged, and a filled limit is not an answer

This applies to every list call in this bucket, not to a remembered list of
command names. If a call returns a collection, it is paged: `gh issue list`,
`gh project list`, `gh project item-list`, `gh project field-list`, every
GraphQL connection (`projectItems`, `subIssues`, `items`), and every `gh api`
REST endpoint that answers with an array. Before drawing any conclusion from
one, prove it is the whole collection and say in the output how many objects
were covered.

- **`gh project list`, `gh project item-list`, and `gh project field-list`
  return `totalCount` beside the array.** Compare the array length to
  `totalCount`. That is an exact answer rather than a heuristic, so prefer it
  wherever it exists. A `--jq` that starts at `.projects[]`, `.items[]`, or
  `.fields[]` throws the count away, so select it alongside. All three default
  to 30, and `gh project list` also omits closed Projects entirely: pass
  `--limit`, and pass `--closed` to that one.
- **`gh issue list` reports no count.** Pass an explicit `--limit` and treat a
  result that comes back at exactly the limit as truncated, not complete. Raise
  it and re-run, or page.
- **A GraphQL connection carries `totalCount` and
  `pageInfo { hasNextPage endCursor }`.** Select them, and follow `endCursor`
  through an `$after: String` argument until `hasNextPage` is false. Do not
  raise `first` past 100 to avoid the loop: the server rejects it with
  `EXCESSIVE_PAGINATION`, `exceeds the first limit of 100 records`.
- **A REST array carries neither.** It pages at 30 through the `Link` header, so
  pass `gh api --paginate` and let it follow the header.

This matters most where a miss turns into a write. A truncated membership scan
says the Issue is not in the Project, and the next step adds it, producing a
second item for the same Issue. So for anything about one specific Issue, use the
per-Issue query below rather than searching a page of the Project.

```bash
# Membership, the item id, and the Project title for one Issue.
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        projectItems(first: 20) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { id project { number title } }
        }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F number=<number>
```

One Issue in more than twenty Projects is rare, which is the reason to select
`totalCount` rather than to assume: if it exceeds the twenty returned, page with
`$after` before deciding the Issue is not a member. This is the one query whose
scope is a single Issue, so it cannot be truncated by other Issues on the board,
which is what makes it the right call for a membership question.

The typed equivalent, `gh issue view <number> --json projectItems`, returns every
Project the Issue belongs to but only the Project title and the field values, not
the item id, so use it for a membership answer and the GraphQL form when you need
the id to write.

## Preflight

```bash
gh auth status
gh repo view --json owner,name,nameWithOwner,defaultBranchRef

# --limit and --closed are both required: this call defaults to 30 and to open
# Projects only. Check the returned array length against totalCount.
gh project list --owner <owner> --limit 100 --closed --format json \
  --jq '{totalCount, returned: (.projects | length), projects: [.projects[] | {number, title, closed}]}'
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

# Field ids and single-select option ids. This call defaults to 30 fields, so
# --limit is required, and totalCount is selected because the miss below is
# reported as drift.
gh project field-list <project> --owner <owner> --limit 100 --format json --jq '
  {totalCount, returned: (.fields | length),
   fields: [.fields[] | select(.type=="ProjectV2SingleSelectField")
            | {field: .name, id: .id, options: [.options[] | {name, id}]}]}'
```

Cache these as `PROJECT_ID`, `STATUS_FIELD_ID`, `PRIORITY_FIELD_ID`, and the
option IDs for `Todo`, `In Progress`, `Blocked`, `Done`, `P0`, `P1`, `P2`.

If `returned` is below `totalCount`, page before concluding anything: a
truncated field list makes a configured field look absent and its options look
missing.

If the field has no option named `Todo`, `In Progress`, `Blocked`, `Done`,
`P0`, `P1`, or `P2`, stop and report the drift. Those seven names come from
rules 7 and 8, not
from the config file, which carries no option names. Do not create the option;
that is `github-project-setup`'s work.

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

# 7. Read back. issueType is requested because the output block renders a
# `Type:` line, and every line in that block is read back rather than restated
# from what was sent. It comes back null when the owner has no Issue Types.
gh issue view <number> --repo <owner>/<repo> \
  --json number,title,url,state,assignees,labels,issueType,projectItems
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

If this returns 20 results, the search was too broad and the Issue you are
looking for may be on the next page. Narrow the search or raise the limit before
concluding the Issue does not exist, because the branch that follows a miss is
`gh issue create`.

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
gh issue view <number> --repo <owner>/<repo> \
  --json number,title,body,labels,assignees,state,issueType
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

Find the item id with the per-Issue membership query from
*Every list call is paged*, not with an item-list scan. Run that query
unchanged and add this selector:

```bash
  --jq '.data.repository.issue.projectItems.nodes[]
        | select(.project.number == <project>) | .id'

gh project item-edit --id <item-id> --project-id <PROJECT_ID> \
  --field-id <PRIORITY_FIELD_ID> --single-select-option-id <OPTION_ID>
```

If that query returns no node for this Project number, and its `totalCount`
matches what it returned, the Issue really has no item and it is
`meta.not-in-project`. Add it with `gh project item-add`, then set the field.
This is the one place where a proven-complete answer is not optional: an
item-list scan that filled its page would send you down this branch for an Issue
that is already an item, and the result is a duplicate item.

### Moving to `Blocked`

`Blocked` is the one target value that also writes the Issue. Do the body first,
then the field, then read both back:

```bash
# 1. Read the current body and append the record under Additional context,
#    following the refine and edit recipe above. --body-file replaces the whole
#    body, so every section the user did not ask to change must survive.
gh issue view <number> --repo <owner>/<repo> --json body --jq .body > /tmp/issue-body.md
# Edit /tmp/issue-body.md: add one line beginning "Waiting on:", such as
#   Waiting on: vendor API key, expected 2026-10-01
# The prefix is what the audit checks for and is never translated; the rest
# is for the reader, in the Issue's language.
gh issue edit <number> --repo <owner>/<repo> --body-file /tmp/issue-body.md

# 2. Set the field with the item id found above.
gh project item-edit --id <item-id> --project-id <PROJECT_ID> \
  --field-id <STATUS_FIELD_ID> --single-select-option-id <BLOCKED_OPTION_ID>

# 3. Read both back.
gh issue view <number> --repo <owner>/<repo> --json body,projectItems \
  --jq '{body, status: [.projectItems[] | .status.name]}'
```

If the user gave no reason, stop before step 1 and ask. Leaving `Blocked` runs
the same three steps with the `Waiting on:` line removed and the target option
id for `Todo` or `In Progress`.

## query

```bash
# Issues by state, label, assignee. This is also the only source of Issue state.
# Its projectItems[] carries each Project's title and the item's field values.
gh issue list --repo <owner>/<repo> --state open --limit 200 \
  --json number,title,url,state,stateReason,assignees,labels,updatedAt,projectItems

# Everything in the Project with its field values.
gh project item-list <project> --owner <owner> --format json --limit 500 --jq '
  .items[] | select(.archive == null) | {
    type: .content.type,
    number: .content.number,
    title: .content.title,
    status: .status,
    priority: .priority,
    assignees: .assignees
  }'
```

Both of these page. `gh project item-list` returns `totalCount` beside `.items`,
so compare the two and settle it exactly. `gh issue list` returns no count, so
treat a result that is exactly its `--limit` as a page rather than the truth.
Either way, raise the limit or page through, and state the number of objects
covered alongside any count you report. A capped list quietly answers a
different question than the one the user asked.

`gh project item-list` reports no Issue state. `.content` carries only `body`,
`number`, `repository`, `title`, `type`, and `url`, so `.content.state` is always
null. Take `state` from `gh issue list` and join on `number`. The `select(.archive
== null)` filter drops archived items, which are not live board state.

`gh project item-list` returns pull requests and draft items as well as Issues.
Filter on `.content.type == "Issue"` when the question is about requirements.

## close and reopen

The comment strings below are the shape; write them in the Issue's language.

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
gh issue view <number> --repo <owner>/<repo> \
  --json number,state,projectItems \
  --jq '.projectItems[] | {project: .title, status: .status.name}'
```

This is the per-Issue read, so no page limit can make a `Done` item look like a
missing one. If it is still not `Done`, report the lag. Set it by hand only when
the user asks.

## Bulk changes

Print the match count and the full target list before the first write:

```bash
gh issue list --repo <owner>/<repo> --state open --limit 500 \
  --search "<query>" --json number,title --jq 'length'
```

**If this returns exactly 500, the count is the limit, not the match count.**
Rule 11 asks the human to confirm a number, and the writes that follow are not
capped at 500, so a capped count means they would be confirming a change to fewer
objects than the change touches. Raise the limit until the result is below it, or
page and sum, before showing the number. Never present a limit as a count.

Then iterate, verifying each write, and report failures individually.
