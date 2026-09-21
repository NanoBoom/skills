---
name: prp-commit
description: Creates Git commits for completed work. Always use when committing changes, when the user explicitly asks to commit the work, when another PRP workflow reaches its commit step, or when the user invokes /prp-commit.
argument-hint: "[target description]"
---

# Commit Intended Work

Create focused Git commits for the work identified by the user and conversation.

**Target**: $ARGUMENTS

## Scope

Infer the intended work from the request, conversation, and current task, including changes produced by subagents. Blank arguments mean infer the target, never commit everything by default.

Inspect staged, unstaged, and untracked changes. Preserve unrelated work in every state. If intended and unrelated changes cannot be separated safely, stop and ask rather than widening the commit.

Keep each commit focused on one coherent outcome. Split unrelated outcomes, but do not fragment one outcome into mechanical implementation layers.

## Message

Write the subject in the imperative mood, as an instruction to the codebase: `add`, `remove`, `rename`, `collapse`, never `added`, `adds`, or a sentence describing the new state. Read it as completing "this commit will ...". The imperative is mandatory even when the repository's history mixes styles.

Keep it short. One line, no trailing period, under 72 characters including any type and scope. State the meaningful outcome and stop; commit subjects often become changelog entries or PR titles, so they must make sense without reading the diff.

Use plain language and the repository's exact terms. Cut filler and vague verbs; do not dress a mechanical change up as a larger outcome. Name a concrete object, not a category of work.

Add a body only when the reason is not obvious from the subject and the diff. When you write one, keep it to a few lines that say why, not what.

Respect enforced repository syntax such as required types or scopes. Treat Git history as evidence of valid structure, not as the writing-quality standard. Never add AI attribution, generated-by text, robot emoji, or `Co-Authored-By: Claude`.

**Bad:** `refactor(prp-pr): update skill instructions` (vague verb, no outcome)

**Bad:** `refactor(prp-pr): PR creation now uses one focused workflow` (describes a state, not imperative)

**Good:** `refactor(prp-pr): collapse PR creation into one workflow`

## Commit and verify

Stage and commit only the intended work. Verify the resulting commit contains every intended change, excludes unrelated changes, and leaves the remaining worktree state untouched. Do not amend or push unless explicitly requested.

Return the commit hash, message, committed scope, and any remaining changes. The commit is the artifact; do not create a separate report.
