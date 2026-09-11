# Contributor contract

The repository root is the `prp-core` Claude Code plugin, the `nanoboom`
marketplace that publishes two plugins, and an Agent Skills repository for
`npx skills`. One tree, three consumers.

It is a fork of the `prp-core` plugin from
[Wirasm/PRPs-agentic-eng](https://github.com/Wirasm/PRPs-agentic-eng). See
[NOTICE](./NOTICE) for what changed at the fork point.

## Layout

Skills live at `skills/<bucket>/<name>/SKILL.md`. A promoted bucket is one that
a plugin ships; each is named in the `PLUGINS` table at the top of
`scripts/check-skills.mjs`, which is the single place that list is written down.

- `prp-core/` ships in the `prp-core` plugin, whose root is the repository root
  (marketplace `source: "./"`).
- `github-project/` ships in the `github-project` plugin, whose root is the
  bucket directory itself: it holds its own
  `skills/github-project/.claude-plugin/plugin.json` and the marketplace points
  at it with `source: "./skills/github-project"`. It is independent of
  `prp-core`, installs separately, and stays self-contained. See
  [its README](./skills/github-project/README.md).
- `in-progress/` and `deprecated/` are created when they are needed. They are
  unpromoted: they appear in no `plugin.json`, no `README.md`, and no
  `skills.sh.json`, and they reach users through `npx skills` and
  `scripts/link-skills.sh` only.

`agents/` and `hooks/` at the root are the `prp-core` plugin's components.
`scripts/` at the root holds maintainer tooling and is not a plugin component.
`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's own root, which is the
repository root for `prp-core` and `skills/github-project/` for
`github-project`, so every path built from it stays valid inside the plugin
cache.

## Invariants

- **The plugin name is `prp-core` and cannot change.** 36 call sites across the
  skills dispatch subagents by their scoped name (`prp-core:codebase-explorer`,
  `prp-core:web-researcher`, and 9 more). Renaming the plugin silently breaks
  every one of them.
- Every promoted skill has an entry in its own plugin's `plugin.json` `skills`
  array. Claude Code does not scan bucket folders, so a skill missing from that
  array does not load. The paths there are relative to that plugin's root, which
  is why `prp-core` writes `./skills/prp-core/<name>` and `github-project`
  writes `./<name>`.
- Every promoted skill also has a line in its bucket `README.md`, a row in the
  top-level [README.md](./README.md), and a group in
  [skills.sh.json](./skills.sh.json). All three hold for both plugins.
- A `${CLAUDE_PLUGIN_ROOT}` path that points into `skills/` includes the bucket
  segment: `${CLAUDE_PLUGIN_ROOT}/skills/prp-core/<name>/scripts/...`. Dropping
  the bucket is the mistake to watch for when porting anything from upstream.
- **`github-project` stays self-contained.** No `${CLAUDE_PLUGIN_ROOT}`, no
  `prp-core:<agent>` dispatch, nothing read outside each skill's own directory.
  Its README promises `npx skills` users that a single copied `SKILL.md` works,
  and the checker fails the build on either violation. A cross-plugin dispatch
  would break only for the users who cannot see the break.
- Each `plugin.json`'s `version` equals its own entry's `version` in
  `.claude-plugin/marketplace.json`. The top-level marketplace `version` is the
  repository release.
- Never introduce a `plugins/` directory. A plugin lives at the repository root
  or at its bucket directory, and the marketplace `source` says which.

## Adding a skill

1. `cd skills/<bucket> && npx skills init <name>`. Run it inside the bucket. From
   the repository root it writes `name: skills/<bucket>/<name>`, which is invalid.
2. `name` equals the directory name. `description` states what the skill does and
   when to use it.
3. Keep `SKILL.md` under 500 lines. Put supporting material in `references/`,
   `templates/`, `workflows/`, or `scripts/`.
4. In `prp-core`, a skill that dispatches a `prp-core:<agent>` subagent or reads
   `${CLAUDE_PLUGIN_ROOT}` works only under the installed plugin, and degrades
   for `npx skills` users. That is an accepted trade-off there, not a bug, but
   say so in the skill. In `github-project` it is not a trade-off but an error;
   see the self-containment invariant above.
5. Add its path to that bucket's plugin manifest `skills` array, relative to the
   plugin root.
6. Add a line to the bucket `README.md`, a row to the top-level `README.md`, and
   the name to the matching group in `skills.sh.json`.
7. Bump `version` in that plugin's `plugin.json` and in its
   `.claude-plugin/marketplace.json` entry.
8. Verify.

## Adding a plugin

1. Create `skills/<bucket>/.claude-plugin/plugin.json`. Its `skills` paths are
   relative to `skills/<bucket>/`.
2. Add an entry to `.claude-plugin/marketplace.json` with
   `"source": "./skills/<bucket>"` and a `version` matching the manifest.
3. Add the bucket to the `PLUGINS` table in `scripts/check-skills.mjs`. Nothing
   else in that script is per-plugin.
4. Promote its skills through the bucket `README.md`, the top-level `README.md`,
   and `skills.sh.json`, as in step 6 above.
5. Verify, including the per-plugin `claude plugin validate` and `--plugin-dir`
   commands below.

## Verification

```bash
node scripts/check-skills.mjs
npx skills add . --list
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
claude plugin validate skills/github-project/.claude-plugin/plugin.json
claude -p "hi" --plugin-dir . --debug-file /tmp/dbg.log
claude -p "hi" --plugin-dir skills/github-project --debug-file /tmp/dbg-gp.log
grep -E "Loaded [0-9]+ (agents|commands|skills)|plugin skills loaded|\[ERROR\]" /tmp/dbg.log
```

`check-skills.mjs` reports `OK 26 skill(s) in 2 plugin(s), 11 agent(s)`.
`npx skills` reports `Found 26 skills`, which it discovers by scanning `skills/`
rather than by reading a manifest, so the count is the same whether a bucket is
promoted or not. `claude plugin validate .` checks the marketplace manifest only,
which is why each `plugin.json` is validated by path as well. Validating the root
`plugin.json` warns that `CLAUDE.md` at the plugin root is not loaded as project
context; the warning is expected, so do not pass `--strict` to it. The root debug
log shows 11 agents and 23 skills; the `github-project` one shows 3 skills and no
agents.

To exercise the install path end to end without pushing, point the marketplace at
the working tree. This rewrites the `nanoboom` entry in user settings, so restore
it afterwards:

```bash
claude plugin marketplace add "$PWD"
claude plugin install github-project@nanoboom --scope local -y
claude plugin details github-project@nanoboom
claude plugin uninstall github-project@nanoboom --scope local
claude plugin marketplace add NanoBoom/skills
```

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
