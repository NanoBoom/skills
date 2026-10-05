#!/bin/bash

# PRP Response Policy Prompt Hook
# Opt-in UserPromptSubmit hook. When PRP_RESPONSE_POLICY=1, it adds one short
# reminder to each turn so that every reply, not only the ones a PRP skill
# reports, follows the response-policy skill. Otherwise it prints nothing, so
# installing the plugin changes no reply until the user turns it on.
#
# It does not read the prompt, and it never touches the PRP store.

set -euo pipefail

[ "${PRP_RESPONSE_POLICY:-}" = "1" ] || exit 0

cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"[prp-core response-policy] Write this turn's reply to the user under the prp-core:response-policy skill: the user's language, the conclusion first, controlled writing (ASD-STE100 at 80% for English, controlled technical Chinese for Chinese), no fact added or dropped, and fixed signals, paths, and code verbatim. Load the skill first if it is not loaded."}}
JSON
