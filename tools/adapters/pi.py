"""Pi adapter (pi.dev, npm `@earendil-works/pi-coding-agent`).

Generated and gitignored, installed by `make install-pi`. Every artifact sits
under its plugin, `build/pi/<plugin>/`, so the installer can take some plugins and
leave others:

- `skills/<skill>/`: skill copies with `<plugin>:<agent>` rewritten.
- `agents/<plugin>__<agent>.md`: the format of Pi's reference `subagent`
  extension (name, description, tools, model; the body is the system prompt).
  Pi core has no subagents, so these load only with that extension or a
  compatible one.
- `prompts/<command>.md`: prompt templates, Pi's slash commands. Pi
  substitutes `$ARGUMENTS` as Claude Code does.
- `extensions/<plugin>__<name>`: each entry of the source
  `harness/pi/extensions/`, a `.ts` or `.js` file or a directory with an
  `index.ts` or `index.js`, copied unread. Pi runs hooks, and MCP clients, as
  extensions, so this is where a plugin's Pi hooks and MCP servers live. The
  plugin prefix keeps two plugins' extensions apart.

The source's Claude Code `hooks/hooks.json` and `.mcp.json` are never translated.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.adapters.base import (
    AgentSource,
    CommandSource,
    EmitResult,
    HarnessAdapter,
    InstallKind,
    PluginSource,
    namespaced,
    render_frontmatter,
    rewrite_dispatch,
)
from tools.adapters.capabilities import MODEL_ALIASES, PI_READ_ONLY_TOOLS, PI_TOOL_NAMES

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
EXTENSION_ENTRY = ("index.ts", "index.js")


class PiAdapter(HarnessAdapter):
    harness_id = "pi"
    display_name = "Pi"
    user_env = "PI_CODING_AGENT_DIR"
    user_default = ".pi/agent"
    project_dir = ".pi"

    @classmethod
    def plugin_root(cls, plugin: str) -> Path:
        return cls.build() / plugin

    @classmethod
    def install_kinds(cls, project: bool) -> tuple[InstallKind, ...]:
        root = cls.plugin_root("{plugin}")
        return (
            InstallKind("skills", f"{root}/skills", "*", "skills"),
            InstallKind("agents", f"{root}/agents", "*.md", "agents"),
            InstallKind("commands", f"{root}/prompts", "*.md", "prompts"),
            InstallKind("extensions", f"{root}/extensions", "*", "extensions"),
        )

    @classmethod
    def check_native(cls, plugin: PluginSource) -> list[tuple[Path, str]]:
        """`harness/pi/` holds only `extensions/`, each a .ts or .js file or a directory with an index."""
        problems = []
        pi = plugin.native_dir(cls.harness_id)
        for entry in sorted(pi.iterdir()) if pi.is_dir() else []:
            if entry.name != "extensions":
                problems.append((entry, "harness/pi/ holds only extensions/"))
        extensions = pi / "extensions"
        for entry in sorted(extensions.iterdir()) if extensions.is_dir() else []:
            if not KEBAB.match(entry.name if entry.is_dir() else entry.stem):
                problems.append((entry, "extension name must be kebab-case"))
            if entry.is_dir():
                if not any((entry / name).is_file() for name in EXTENSION_ENTRY):
                    problems.append((entry, "an extension directory needs index.ts or index.js"))
            elif entry.suffix not in (".ts", ".js"):
                problems.append((entry, "an extension is a .ts or .js file, or a directory"))
        return problems

    def emit(self, plugins: list[PluginSource]) -> EmitResult:
        result = EmitResult()
        for plugin in plugins:
            for skill in plugin.skills:
                self.emit_skill_copy(skill, self.plugin_root(plugin.name) / "skills" / skill.name, plugins, result)
            for agent in plugin.agents:
                self._emit_agent(agent, plugins, result)
            for command in plugin.commands:
                self._emit_prompt(command, plugins, result)
            self._emit_extensions(plugin, result)
            self.note_claude_only(plugin, result)
        return result

    def _emit_extensions(self, plugin: PluginSource, result: EmitResult) -> None:
        source = plugin.native_dir(self.harness_id) / "extensions"
        for entry in sorted(source.iterdir()) if source.is_dir() else []:
            dest = self.plugin_root(plugin.name) / "extensions" / namespaced(plugin.name, entry.name)
            if entry.is_dir():
                self.copy_tree(entry, dest, result)
            elif entry.is_file():
                result.written.append(self.copy(entry, dest))

    def _emit_prompt(self, command: CommandSource, plugins: list[PluginSource], result: EmitResult) -> None:
        fields = {"description": command.description, "argument-hint": command.argument_hint or None}
        body = rewrite_dispatch(command.body, plugins).strip() + "\n"
        result.written.append(
            self.write(
                self.plugin_root(command.plugin) / "prompts" / f"{command.name}.md",
                render_frontmatter(fields) + "\n" + body,
            )
        )

    def _emit_agent(self, agent: AgentSource, plugins: list[PluginSource], result: EmitResult) -> None:
        name = namespaced(agent.plugin, agent.name)
        model = MODEL_ALIASES[self.harness_id].get(agent.model)
        if agent.read_only:
            tools = list(PI_READ_ONLY_TOOLS)
        elif agent.tools is not None:
            tools = [PI_TOOL_NAMES.get(t, t) for t in agent.tools]
        else:
            tools = None
        fields = {
            "name": name,
            "description": agent.description,
            "tools": ", ".join(tools) if tools else None,
            "model": model,
        }
        body = rewrite_dispatch(agent.body, plugins).strip() + "\n"
        result.written.append(
            self.write(
                self.plugin_root(agent.plugin) / "agents" / f"{name}.md", render_frontmatter(fields) + "\n" + body
            )
        )
