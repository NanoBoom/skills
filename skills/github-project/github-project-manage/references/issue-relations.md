# Issue relations: parent, child, blocked-by, blocking

Two relation families, with different mechanics.

| Relation | Meaning | Where it lives |
|---|---|---|
| parent / sub-issue | Decomposition. The child is part of the parent's outcome. | GitHub sub-issue relation |
| `blocked-by` / `blocking` | Sequencing. The blocked Issue cannot start until the blocker closes. | GitHub issue dependency |

They are independent. A child can be blocked by another child, and an Issue with
no parent can still be blocked.

## Before writing any relation

Confirm both Issues exist and are in the same repository or, for a cross
repository relation, confirm the host supports it before trying:

```bash
gh issue view <number> --repo <owner>/<repo> --json number,title,url,state,id
```

Keep the `id` values. Both the GraphQL sub-issue mutations and the REST
dependency endpoints identify Issues by node ID or numeric ID, not by number.

Never create a cycle. Before adding `A blocked-by B`, walk B's own `blocked-by`
chain and refuse if it reaches A. Report the cycle instead. A cycle that already
exists is `meta.relation-conflict` and belongs in an audit report, not in a
silent repair.

## Parent and child

### Preferred path

Some `gh` builds expose sub-issues directly:

```bash
gh issue edit <child> --repo <owner>/<repo> --parent <parent>
gh issue edit <child> --repo <owner>/<repo> --remove-parent

# From the parent's side, the same relation:
gh issue edit <parent> --repo <owner>/<repo> --add-sub-issue <child>
gh issue edit <parent> --repo <owner>/<repo> --remove-sub-issue <child>
```

The flag that sets a parent is `--parent`, not `--add-parent`. Run
`gh issue edit --help` once and check for `--parent` before relying on it. If the
flag is absent, use the GraphQL path.

### GraphQL fallback

```bash
# Node IDs for both Issues.
gh issue view <parent> --repo <owner>/<repo> --json id --jq .id
gh issue view <child>  --repo <owner>/<repo> --json id --jq .id

gh api graphql -f query='
  mutation($parent: ID!, $child: ID!) {
    addSubIssue(input: { issueId: $parent, subIssueId: $child }) {
      issue { number }
      subIssue { number }
    }
  }' -F parent=<parent-node-id> -F child=<child-node-id>
```

Removal uses `removeSubIssue` with the same inputs. Reordering uses
`reprioritizeSubIssue`.

Read the children back before reporting:

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!, $after: String) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        subIssues(first: 50, after: $after) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { number title state url }
        }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F number=<parent>
```

`subIssues` is a paged connection like every other one in this bucket. Compare
the returned node count to `totalCount`, and follow `endCursor` through `$after`
while `hasNextPage` is true. A parent read back on one page reports the children
it happened to see, so a `split` that created more of them than the page holds
would look partially failed and invite a second run that creates duplicates.

### If the mutation is rejected

If the host rejects `addSubIssue` as an unknown field, sub-issues are not
available there. Do not silently fall back to a checkbox list and call it done.
Record the decomposition in the parent body as a task list of real Issue
references, state in the output that the parent-child relation is recorded as
text rather than as a GitHub relation, and keep each child in the Project with
its own fields so scheduling still works.

## Blocked by and blocking

### Preferred path

Issue dependencies are reachable through `gh api` against the dependency
endpoints:

```bash
# Numeric database id, which these endpoints take.
gh api repos/<owner>/<repo>/issues/<blocker> --jq .id

# Declare that <issue> is blocked by <blocker>.
gh api --method POST \
  repos/<owner>/<repo>/issues/<issue>/dependencies/blocked_by \
  -F issue_id=<blocker-database-id>

# Read back. Both endpoints are REST lists and page at 30, so --paginate is
# required: without it a read-back on an Issue with more relations than that can
# fail to show the one just written, and the verify step would report a
# successful write as lost.
gh api --paginate repos/<owner>/<repo>/issues/<issue>/dependencies/blocked_by \
  --jq '.[] | {number, title, state}'
gh api --paginate repos/<owner>/<repo>/issues/<issue>/dependencies/blocking \
  --jq '.[] | {number, title, state}'
```

Create the relation on one side only. `blocking` is the inverse view of
`blocked_by` and is created automatically. Writing both produces duplicates or
an error.

Removal:

```bash
gh api --method DELETE \
  repos/<owner>/<repo>/issues/<issue>/dependencies/blocked_by/<blocker-database-id>
```

### If the endpoint is unavailable

A `404` or `422` from these endpoints on a host that has not enabled issue
dependencies is not a bug in the request. Confirm with one read call on a known
Issue before concluding. Then record the dependency in the Issue body:

```markdown
## Dependencies

- Blocked by: #101
```

and say in the output that it is recorded as text, not as a GitHub relation.
`## Dependencies` and `Blocked by: #n` are markers and stay as written in every
language; only the rest of the body follows the configured `language`.
Rule 9 still holds either way: the block goes in the Issue, and a block by
another Issue never becomes a `Blocked` status, even when the relation can only
be recorded as text.

## The status of a blocked Issue

There are two kinds of block, and they go to two different places.

An Issue blocked by another Issue stays in `Todo`. It does not move to
`In Progress`, and it does not move to `Blocked`. The `blocked-by` relation and
the note in the body are the whole record, and both can be checked against the
blocker's state. A `Blocked` status on top of a relation would be a second copy
of the same fact.

An Issue waiting on something that has no Issue here, such as a vendor, a
customer, or a team in another organization, is `Blocked`. There is no relation
to create, so a body line beginning `Waiting on:` is the record, and `move`
sets the status together with that line. Section 7 of `SKILL.md` has the rules
and `references/gh-recipes.md` has the transaction.

When a blocker closes, the blocked Issue does not move on its own. Moving it is
a decision, so ask, or leave it in `Todo` and report that the blocker is now
closed.

## Reporting relations

Every relation write ends with a read back and a line in the output block:

```
Parent: #100 (or "none")
Blocked by: #101, #102 (or "none")
Blocking: #110 (or "none")
```

If a read back shows a relation that was not requested, report it. Do not remove
a relation the user did not ask you to remove.
