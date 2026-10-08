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
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Reply under the response-policy skill."}}
JSON
