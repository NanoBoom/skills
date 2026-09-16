# Fallback Issue body

Use this structure **only** when the repository has no applicable template under
`.github/ISSUE_TEMPLATE/` on the default branch. A repository template always
wins, including its extra fields and its wording.

When `.github/github-project.yml` sets `language`, write the headings and the
content in that language. The five sections, their order, and the
`Waiting on:` prefix stay as they are.

Copy the block below, keep all five headings even when a section is short, and
replace the italic guidance with real content. Delete no heading: an empty
heading is a visible gap, a missing heading is invisible.

```markdown
## Background and goal

What is wrong or missing today, and why fixing it matters. One or two
paragraphs. Not a restatement of the title and not a design.

## Scope

What is included, named concretely enough that a reviewer can decide whether a
change belongs here.

## Acceptance criteria

- [ ] An observable condition a third party can check without asking the author.
- [ ] Another one. State what you run or look at, and what result counts as pass.

## Non-goals

The near misses a reader would otherwise assume are included.

## Additional context

Links, prior discussion, screenshots, affected users, constraints, and known
dependencies. Note a dependency on another Issue here as well as in the
relation. A block with no Issue to relate to is one line beginning
"Waiting on:", which is what moves the Project item to Blocked. Write "None"
rather than deleting the heading.
```

Replace the guidance text with real content. Leaving it in place is the same as
leaving a section empty: it describes what belongs there, not what belongs to
this requirement.

## Worked example

```markdown
## Background and goal

Accounts with more than 500k orders time out on the CSV export and get a 504
with no file. Support has escalated it four times this month. The goal is that
the export completes for every account we currently host.

## Scope

The orders CSV export path: the request handler, the query, and the streaming
writer. Both the UI download and the API endpoint.

## Acceptance criteria

- [ ] The export completes for a 500k row account in under 10 minutes.
- [ ] The response streams, so no request exceeds the 60 second gateway timeout.
- [ ] A failed export returns a 5xx with an error body, never a truncated file.
- [ ] The existing column order and header row are unchanged.

## Non-goals

- Exports other than orders.
- A new async job and notification flow. That is #212.
- Changing the CSV schema.

## Additional context

Escalations: SUP-1841, SUP-1902. The slow query is the per-row customer lookup.
Blocked by nothing.
```

## Notes

- Acceptance criteria are a checkbox list. That is what makes progress readable
  from the Issue itself.
- Keep the criteria about outcomes, not about activities. "Refactor the writer"
  is not a criterion. "The response streams" is.
- If Non-goals or Additional context would be genuinely empty, write "None", or
  its equivalent in the Issue's language. Do not invent content to fill it, and
  do not drop the heading. "None" is not an
  answer under Background and goal, Scope, or Acceptance criteria: an audit
  counts it as absent there, which is correct, because those three are what make
  the Issue deliverable.
