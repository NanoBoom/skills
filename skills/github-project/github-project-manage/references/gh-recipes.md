# gh recipes per mode

Prefer typed `gh` commands. Fall back to `gh api` or GraphQL only where a typed
command cannot reach. In this skill the operations that need the fallback are:
Project field mutations that need field and option IDs, sub-issue relations,
issue dependencies, and Issue Types. Everything else has a typed command.

Substitute `<owner>`, `<repo>`, and `<project>` from `.github/github-project.yml`
or from the derivation in section 1 of `SKILL.md`.

## Every list call has a limit, and a filled limit is not an answer

`gh issue list` and `gh project item-list` both page. Pass an explicit `--limit`
on every one, then check the result count against it. **A list that comes back at
exactly its limit is truncated, not complete.** Raise the limit and re-run, or
page, before drawing any conclusion from it, and say in the output how many
objects were covered.

This matters most where a miss turns into a write. A truncated membership scan
says the Issue is not in the Project, and the next step adds it, producing a
second item for the same Issue. So for anything about one specific Issue, use the
per-Issue query below, which is not paged, rather than searching a page of the
Project.

```bash
# Membership, the item id, and the Project title for one Issue. Not paged.
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        projectItems(first: 20) { nodes { id project { number title } } }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F number=<number>
```

The typed equivalent, `gh issue view <number> --json projectItems`, is also
unpaged but returns only the Project title and the field values, not the item id,
so use it for a membership answer and the GraphQL form when you need the id to
write.

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

If the field has no option named `Todo`, `In Progress`, `Done`, `P0`, `P1`, or
`P2`, stop and report the drift. Those six names come from rules 7 and 8, not
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
# Find the item id for an Issue already in the Project. Use the unpaged
# per-Issue query from "Every list call has a limit", not an item-list scan.
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        projectItems(first: 20) { nodes { id project { number title } } }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F number=<number> \
  --jq '.data.repository.issue.projectItems.nodes[]
        | select(.project.number == <project>) | .id'

gh project item-edit --id <item-id> --project-id <PROJECT_ID> \
  --field-id <PRIORITY_FIELD_ID> --single-select-option-id <OPTION_ID>
```

If that query returns no node for this Project number, the Issue really has no
item and it is `meta.not-in-project`. Add it with `gh project item-add`, then set
the field. This is the one place where an unpaged answer is not optional: an
item-list scan that filled its page would send you down this branch for an Issue
that is already an item, and the result is a duplicate item.

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

Both of these page. If either returns exactly its `--limit`, the answer is a
page, not the truth. Raise the limit or page through, and state the number of
objects covered alongside any count you report. A capped list quietly answers a
different question than the one the user asked.

`gh project item-list` reports no Issue state. `.content` carries only `body`,
`number`, `repository`, `title`, `type`, and `url`, so `.content.state` is always
null. Take `state` from `gh issue list` and join on `number`. The `select(.archive
== null)` filter drops archived items, which are not live board state.

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
