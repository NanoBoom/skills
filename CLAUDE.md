# Contributor contract

The repository root is the `prp-core` Claude Code plugin, its own single-plugin
marketplace (`prp-core@nanoboom`), and an Agent Skills repository for
`npx skills`. One tree, three consumers.

It is a fork of the `prp-core` plugin from
[Wirasm/PRPs-agentic-eng](https://github.com/Wirasm/PRPs-agentic-eng). See
[NOTICE](./NOTICE) for what changed at the fork point.

## Layout

Skills live at `skills/<bucket>/<name>/SKILL.md`.

- `prp-core/` is the promoted bucket. It ships in the plugin.
- `github-project/` is a deliberately unregistered bucket of self-contained
  GitHub Issue management skills. Do not register it: `scripts/check-skills.mjs`
  errors on any `plugin.json` or `skills.sh.json` entry outside `prp-core`, so
  adding one turns the checker red. It reaches users through `npx skills` and
  `scripts/link-skills.sh` instead. See
  [its README](./skills/github-project/README.md).
- `in-progress/` and `deprecated/` are created when they are needed. They never
  appear in `.claude-plugin/plugin.json`, `README.md`, or `skills.sh.json`.

Only `prp-core/` is promoted. Every other bucket stays out of
`.claude-plugin/plugin.json`, `README.md`, and `skills.sh.json`.

`agents/` and `hooks/` at the root are the plugin's components. `scripts/` at the
root holds maintainer tooling and is not a plugin component.
`${CLAUDE_PLUGIN_ROOT}` resolves to the repository root, so every path built from
it stays valid inside the plugin cache.

## Invariants

- **The plugin name is `prp-core` and cannot change.** 36 call sites across the
  skills dispatch subagents by their scoped name (`prp-core:codebase-explorer`,
  `prp-core:web-researcher`, and 9 more). Renaming the plugin silently breaks
  every one of them.
- Every promoted skill has an entry in `.claude-plugin/plugin.json`'s `skills`
  array. Claude Code does not scan bucket folders, so a skill missing from that
  array does not load.
- Every promoted skill also has a line in the bucket
  [README.md](./skills/prp-core/README.md), a row in the top-level
  [README.md](./README.md), and a group in [skills.sh.json](./skills.sh.json).
- A `${CLAUDE_PLUGIN_ROOT}` path that points into `skills/` includes the bucket
  segment: `${CLAUDE_PLUGIN_ROOT}/skills/prp-core/<name>/scripts/...`. Dropping
  the bucket is the mistake to watch for when porting anything from upstream.
- `.claude-plugin/plugin.json`'s `version` equals the `prp-core` entry's
  `version` in `.claude-plugin/marketplace.json`. The marketplace `version` is
  the repository release.
- Never introduce a `plugins/` directory. The root is the plugin.

## Adding a skill

1. `cd skills/prp-core && npx skills init <name>`. Run it inside the bucket. From
   the repository root it writes `name: skills/prp-core/<name>`, which is invalid.
2. `name` equals the directory name. `description` states what the skill does and
   when to use it.
3. Keep `SKILL.md` under 500 lines. Put supporting material in `references/`,
   `templates/`, `workflows/`, or `scripts/`.
4. A skill that dispatches a `prp-core:<agent>` subagent or reads
   `${CLAUDE_PLUGIN_ROOT}` works only under the installed plugin, and degrades
   for `npx skills` users. That is an accepted trade-off here, not a bug, but say
   so in the skill.
5. Add its path to `.claude-plugin/plugin.json`'s `skills` array.
6. Add a line to the bucket `README.md`, a row to the top-level `README.md`, and
   the name to the matching group in `skills.sh.json`.
7. Bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
8. Verify.

## Verification

```bash
node scripts/check-skills.mjs
npx skills add . --list
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
claude -p "hi" --plugin-dir . --debug-file /tmp/dbg.log
grep -E "Loaded [0-9]+ (agents|commands|skills)|plugin skills loaded|\[ERROR\]" /tmp/dbg.log
```

`npx skills` reports `Found 26 skills`: the 23 promoted ones plus the three in
the unregistered `github-project/` bucket, which it discovers by scanning
`skills/` rather than by reading a manifest. `claude plugin validate .` checks the
marketplace manifest only, which is why `plugin.json` is validated by path as
well. That second command warns that `CLAUDE.md` at the plugin root is not loaded
as project context; the warning is expected, so do not pass `--strict` to it. The
debug log shows 11 agents and 23 skills.

## Scripts

- `scripts/check-skills.mjs`: enforces the invariants above. Run it first.
- `scripts/list-skills.sh`: prints every `SKILL.md` path under `skills/`.
- `scripts/link-skills.sh`: maintainer tool, symlinks every skill outside
  `deprecated/` into `~/.claude/skills` and `~/.agents/skills`.

## Upstream

`.claude-plugin/plugin.json`'s `metadata.upstreamCommit` records the commit this
fork is based on. To pull upstream changes, diff that commit against upstream
`main` under `plugins/prp-core/`, apply what you want, remembering that skills
sit one level deeper here, and update `metadata.upstreamCommit`.

## Prose

All text in this repository is English. No em dashes in new prose; text carried
over from upstream stays as written.
