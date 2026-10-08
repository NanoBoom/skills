#!/bin/bash

# PRP Loop Stop Hook
# Keeps the session that drives a running prp-loop from stopping between
# stages, so one /prp-loop invocation carries the loop to done or halted.
# The loop's state file is the only signal; the hook never judges the work itself.

set -euo pipefail

HOOK_INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0

# --- PRP store resolver, READ-ONLY variant (hooks must NEVER create a store) ---
# Same derivation and bail-outs as prp-research-team-stop.sh; see the reasoning there.
_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$_root" ] || _root="$PWD"
_root="$(cd "$_root" 2>/dev/null && pwd -P)" || exit 0
[ -n "$_root" ] || exit 0
PRP_DIR="${PRP_DIR:-$_root/.prp}"

STATE_FILE="$PRP_DIR/state/prp-loop.state.json"
[ -f "$STATE_FILE" ] || exit 0

field() { jq -r "$1 // empty" "$STATE_FILE" 2>/dev/null || true; }

[ "$(field .status)" = "running" ] || exit 0

# Only the session that started or resumed the loop is held. A loop started where the
# harness exports no session id records no owner, and any other session in this
# checkout stops normally.
SESSION=$(printf '%s' "$HOOK_INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)
OWNER=$(field .owner)
[ -n "$OWNER" ] && [ "$OWNER" = "$SESSION" ] || exit 0

# A dispatched stage agent is still running; its completion notification resumes the session.
[ -z "$(field .pending.dispatched_at)" ] || exit 0

# Never hold the session forever: after three continuations without a single state
# change, let it stop. The loop stays resumable with /prp-loop --resume.
GUARD_FILE="$PRP_DIR/state/prp-loop.stop-guard"
UPDATED_AT=$(field .updated_at)
COUNT=0
if [ -f "$GUARD_FILE" ] && [ "$(sed -n 1p "$GUARD_FILE")" = "$UPDATED_AT" ]; then
  COUNT=$(sed -n 2p "$GUARD_FILE")
fi
COUNT=$((COUNT + 1))
if (( COUNT > 3 )); then
  echo "prp-loop: no state change across 3 continuations; allowing stop. Resume with /prp-loop --resume." >&2
  rm -f "$GUARD_FILE"
  exit 0
fi
printf '%s\n%s\n' "$UPDATED_AT" "$COUNT" > "$GUARD_FILE"

SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/skills/prp-loop/scripts/prp_loop.py"
STAGE=$(field .stage)

REASON="prp-loop is still running (stage: ${STAGE}). Do not stop until it reports done or halted.
Run \`uv run ${SCRIPT} next\` and follow the prp-loop skill: if its action is \"agent\" and you have not dispatched that action id yet, dispatch it to one fresh subagent with the prompt verbatim, then run \`uv run ${SCRIPT} dispatched\`. If you already dispatched it and it is still running, run \`uv run ${SCRIPT} dispatched\` and end your turn. When the stage agent has finished, run \`uv run ${SCRIPT} report\`."

jq -n --arg reason "$REASON" '{"decision": "block", "reason": $reason}'

exit 0
