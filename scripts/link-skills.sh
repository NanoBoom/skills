#!/usr/bin/env bash
set -euo pipefail

# NOTE: This is a maintainer tool, not an installer. Users install with
# `npx skills add NanoBoom/skills` or by installing the prp-core plugin. On
# Claude Code this script duplicates the skills that an installed prp-core
# plugin already provides, so run it only when you work on this repository
# without the plugin installed.
#
# Be aware that a linked skill is NOT the same as the installed plugin: the
# prp-core:<agent> subagents in agents/ and the Stop hook in hooks/ only exist
# under the plugin. Skills that dispatch them will fail when reached this way.
#
# Links every skill in this repository into the local skill directories used by
# each agent harness:
#   - ~/.claude/skills: Claude Code
#   - ~/.agents/skills: Codex and other Agent Skills compatible harnesses
# Each entry is a symlink into this repo, so a `git pull` keeps the linked
# skills current. Re-run after adding, removing, or renaming a skill.
#
# A real file or directory already sitting at a destination path is left alone
# and reported as skipped. Pass --force to replace those with symlinks; it
# prints every path it removes.

FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    *)
      echo "usage: $(basename "$0") [--force]" >&2
      exit 1
      ;;
  esac
done

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DESTS=("$HOME/.claude/skills" "$HOME/.agents/skills")

# Collect the repo's skills once, link into every destination. `deprecated/` is
# retired and is skipped, same as everywhere else non-promoted skills are kept
# out.
names=()
srcs=()
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  names+=("$(basename "$src")")
  srcs+=("$src")
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/node_modules/*' -not -path '*/deprecated/*' -print0)

for DEST in "${DESTS[@]}"; do
  # If $DEST is a symlink that resolves into this repo, we would write the
  # per-skill symlinks back into the repo's own skills/ tree. Detect and bail
  # out instead of polluting the working copy.
  if [ -L "$DEST" ]; then
    resolved="$(cd "$(dirname "$DEST")" && cd "$(readlink "$DEST")" && pwd)"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $DEST is a symlink into this repo ($resolved)." >&2
        echo "Remove it (rm \"$DEST\") and re-run; the script will recreate it as a real dir." >&2
        exit 1
        ;;
    esac
  fi

  mkdir -p "$DEST"

  for i in "${!names[@]}"; do
    name="${names[$i]}"
    src="${srcs[$i]}"
    target="$DEST/$name"

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      if [ "$FORCE" -eq 1 ]; then
        echo "removing real path $target (--force)"
        rm -rf "$target"
      else
        echo "skipped $name: $target is a real directory, not a symlink (use --force to replace)"
        continue
      fi
    fi

    ln -sfn "$src" "$target"
    echo "linked $name -> $src ($DEST)"
  done
done
