---
name: prp-review
description: Reviews GitHub pull requests through specialist review agents, runs repository validation, verifies corrections, aggregates findings, and posts the result. Defaults to code, seam, and simplification review; the operator can add scopes or explicitly request only selected scopes. Use when the operator asks to review a PR, re-review fixes, check whether a PR is ready to merge, run review agents, or invokes /prp-review.
argument-hint: "<pr-number|pr-url|branch> [add <scopes>|only <scopes>|all] [--verify-corrections] [--approve|--request-changes]"
---

# Review a Pull Request

Coordinate an evidence-based PR review. Reviewer agents are the only path for judging the code:
do not add an inline review pass before or after them.

**Input**: $ARGUMENTS (if absent, use the current branch's PR).

Let `workflows/agents.md` own scope selection, reviewer dispatch, correction verification,
aggregation, and publication. Pass the operator's scope intent and flags through without rebuilding
those contracts here.

Resolve the canonical store before starting:

```bash
# --- PRP store resolver (canonical; keep byte-identical across skills) ---
# The store is `.prp/` in the project root, so it travels with the checkout and
# the operator can find it without resolving a derived key.
# --git-common-dir resolves a linked worktree to its main checkout, so every
# worktree of a project shares one store.
# The store ignores itself (`*` covers its own .gitignore), so no artifact ever
# reaches `git status` or gets swept into a commit. Set PRP_DIR to relocate it.
_gd="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
case "$_gd" in */.git) _root="${_gd%/.git}" ;; "") _root="$PWD" ;; *) _root="$_gd" ;; esac
_root="$(cd "$_root" && pwd -P)"
PRP_DIR="${PRP_DIR:-$_root/.prp}"
mkdir -p "$PRP_DIR"; [ -f "$PRP_DIR/.gitignore" ] || printf '*\n' > "$PRP_DIR/.gitignore"
```

Read `workflows/agents.md` and execute it end-to-end. Before producing the report, read
`templates/review-report.md` and follow its output contract exactly.

## Resources

- `workflows/agents.md` — PR resolution, validation, agent scopes, aggregation, and publication
- `templates/review-report.md` — canonical local and GitHub review format
