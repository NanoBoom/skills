# kitchen-sink

A test fixture, not a shipped plugin. It holds one of every component a Claude
Code plugin can carry, so `tools/tests/test_components.py` can check that every
adapter and the installer handle each of them.

- **[kitchen-skill](./skills/kitchen-skill/SKILL.md)**: dispatches an agent and runs a bundled script.
- **[kitchen-long](./skills/kitchen-long/SKILL.md)**: longer than the Codex prompt limit.

`hooks/hooks.json` and `.mcp.json` are Claude Code's. `harness/codex/` holds the
Codex versions, laid over the generated Codex plugin, and `harness/pi/extensions/`
holds a Pi hook and a stand-in MCP client, one as a file and one as a directory.
