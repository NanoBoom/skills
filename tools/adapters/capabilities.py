"""Model aliases, effort levels, and tool-name maps shared by the adapters.

What each harness does with a plugin is described where it happens, in its
adapter; docs/harnesses.md describes it for readers. The values here are the
facts that change when a harness or a model lineup does.

Adapted from wshobson/agents `tools/adapters/capabilities.py` (MIT). See NOTICE.
"""

from __future__ import annotations

# Source `model:` alias -> the harness's model identifier. `inherit` maps to None:
# the adapter omits the field and the agent runs on the parent session's model.
#
# Codex targets follow plugins/prp-core/skills/agent-policy/references/codex.md
# (checked 2026-09-30 against Codex CLI 0.159.2). Pi takes `provider/model-id`;
# the targets are the current Anthropic model IDs.
MODEL_ALIASES: dict[str, dict[str, str | None]] = {
    "codex": {
        "fable": "gpt-6-astra",
        "opus": "gpt-6.1-sol",
        "sonnet": "gpt-6.1-sol",
        "haiku": "gpt-6-luna",
        "inherit": None,
    },
    "pi": {
        "fable": "anthropic/claude-fable-5-1",
        "opus": "anthropic/claude-opus-5-5",
        "sonnet": "anthropic/claude-sonnet-5-5",
        "haiku": "anthropic/claude-haiku-5-5",
        "inherit": None,
    },
}

# Source `model:` aliases an agent may use.
SOURCE_MODELS = frozenset(MODEL_ALIASES["codex"])

# `effort:` levels an agent may set. Claude Code and Codex (`model_reasoning_effort`)
# share them; Pi has no per-agent effort, so the value is dropped there.
EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max"})

# Claude Code tools that change files. An agent without any of them is read-only.
WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})

# Pi built-in tools that leave files untouched, for agents that must not write.
PI_READ_ONLY_TOOLS = ("read", "grep", "find", "ls", "bash")
PI_TOOL_NAMES = {
    "Read": "read",
    "Edit": "edit",
    "Write": "write",
    "Bash": "bash",
    "Grep": "grep",
    "Glob": "find",
    "LS": "ls",
}
