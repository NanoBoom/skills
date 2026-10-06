"""OpenAI Codex CLI adapter.

Generated and gitignored, installed by `make install-codex`:

- `build/codex/.agents/plugins/marketplace.json`: a local Codex marketplace that
  lists every plugin with something for Codex. The installer registers it with
  `codex plugin marketplace add` and installs each plugin with `codex plugin add`,
  so Codex loads skills, hooks, and MCP servers the way it loads any plugin.
- `build/codex/plugins/<plugin>/`: one Codex plugin per source plugin.
  - `.codex-plugin/plugin.json`: the manifest.
  - `skills/<skill>/`: skill copies with `<plugin>:<agent>` rewritten to the TOML
    agent names, and bodies over Codex's 8000-byte prompt cap split into
    `references/`. Codex has no slash commands, so each `commands/<name>.md`
    becomes a skill here too.
  - everything in the source `harness/codex/`, copied unread. Its
    `hooks/hooks.json` and `.mcp.json` become the manifest's `hooks` and
    `mcpServers`. The source's Claude Code `hooks/hooks.json` and `.mcp.json` are
    never copied.
- `build/codex/agents/<plugin>/<plugin>__<agent>.toml`: custom agents, grouped by
  plugin so the installer can take some plugins and leave others. A Codex plugin
  manifest has no agents field, so the installer links these into
  `~/.codex/agents/` instead.

The body splitter is adapted from wshobson/agents `tools/adapters/codex.py` (MIT).
See NOTICE.
"""

from __future__ import annotations

from pathlib import Path

from tools.adapters.base import (
    AgentSource,
    CommandSource,
    EmitResult,
    HarnessAdapter,
    InstallKind,
    PluginSource,
    SkillSource,
    namespaced,
    read_marketplace,
    render_frontmatter,
    rewrite_dispatch,
    split_frontmatter,
)
from tools.adapters.capabilities import EFFORTS, MODEL_ALIASES

CATEGORY = "Coding"

# Paths in a Codex plugin the adapter writes itself; `harness/codex/` must not hold them.
RESERVED = ("skills", ".codex-plugin")

OVERFLOW_NAME = "codex-overflow.md"

_POINTER = (
    "\n\n> The rest of this skill is in `references/{name}`, split out to fit the Codex"
    " skill size limit. Read it before acting on any section not shown above.\n"
)


# ── TOML ─────────────────────────────────────────────────────────────────────


def toml_string(value: str) -> str:
    """A TOML basic string, multi-line when the value has newlines."""
    escaped = value.replace("\\", "\\\\")
    if "\n" in value:
        return '"""\n' + escaped.replace('"""', '""\\"') + '"""'
    return '"' + escaped.replace('"', '\\"') + '"'


# ── Skill splitting ──────────────────────────────────────────────────────────


def _sections(body: str) -> list[str]:
    """Split a body before each `## ` heading that sits outside a fenced code block."""
    sections: list[str] = []
    current: list[str] = []
    fence = ""
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[: len(stripped) - len(stripped.lstrip(stripped[0]))]
            if not fence:
                fence = marker
            elif marker.startswith(fence):
                fence = ""
        if not fence and line.startswith("## ") and current:
            sections.append("".join(current))
            current = []
        current.append(line)
    if current:
        sections.append("".join(current))
    return sections


def _utf8_cut(data: bytes, cap: int) -> int:
    """Largest index <= cap that is a UTF-8 boundary, preferring a nearby newline."""
    if cap >= len(data):
        return len(data)
    end = cap
    while end > 0 and (data[end] & 0xC0) == 0x80:
        end -= 1
    nl = data.rfind(b"\n", max(0, end - 512), end)
    return nl + 1 if nl > end // 2 else end


def split_skill(frontmatter: str, body: str, cap: int, overflow_name: str) -> tuple[str, str | None]:
    """Fit `frontmatter + body` into `cap` bytes.

    Whole `## ` sections are kept in order while they fit; the first one that does
    not, and everything after it, moves to the overflow file so the reading order
    survives. A head that cannot fit even its first section is cut at a UTF-8
    boundary. Returns (SKILL.md content, overflow or None).
    """
    whole = frontmatter + body
    if len(whole.encode("utf-8")) <= cap:
        return whole, None

    pointer = _POINTER.format(name=overflow_name)
    budget = cap - len(frontmatter.encode("utf-8")) - len(pointer.encode("utf-8"))
    sections = _sections(body)
    head = ""
    rest_at = len(sections)
    for i, section in enumerate(sections):
        if len((head + section).encode("utf-8")) > budget:
            rest_at = i
            break
        head += section
    overflow = "".join(sections[rest_at:])

    if not head:
        data = body.encode("utf-8")
        at = _utf8_cut(data, max(budget, 0))
        head, overflow = data[:at].decode("utf-8"), data[at:].decode("utf-8")

    return frontmatter + head.rstrip("\n") + pointer, overflow.lstrip("\n")


# ── Adapter ──────────────────────────────────────────────────────────────────


class CodexAdapter(HarnessAdapter):
    harness_id = "codex"
    display_name = "Codex"
    user_env = "CODEX_HOME"
    user_default = ".codex"
    project_dir = ".codex"
    cli_plugins = True
    # Codex truncates a skill prompt at 8000 bytes (MAX_SKILL_PROMPT_BYTES in
    # codex-rs/ext/skills/src/render.rs). Leave headroom for the path and name
    # lines it adds around the file.
    PROMPT_CAP = 8000
    SKILL_FILE_CAP = PROMPT_CAP - 400

    @classmethod
    def plugin_root(cls, plugin: str) -> Path:
        return cls.build() / "plugins" / plugin

    @classmethod
    def marketplace_path(cls) -> Path:
        return cls.build() / ".agents" / "plugins" / "marketplace.json"

    @classmethod
    def install_kinds(cls, project: bool) -> tuple[InstallKind, ...]:
        """Agents go to `agents/`. At user level the skills arrive in a Codex plugin
        instead, which install.py adds with the Codex CLI; a project gets them here."""
        agents = InstallKind("agents", f"{cls.build()}/agents/{{plugin}}", "*.toml", "agents")
        if not project:
            return (agents,)
        return (InstallKind("skills", f"{cls.plugin_root('{plugin}')}/skills", "*", "skills"), agents)

    @classmethod
    def check_native(cls, plugin: PluginSource) -> list[tuple[Path, str]]:
        native = plugin.native_dir(cls.harness_id)
        return [
            (native / name, "the Codex adapter writes this path; remove it")
            for name in RESERVED
            if (native / name).exists()
        ]

    def emit(self, plugins: list[PluginSource]) -> EmitResult:
        result = EmitResult()
        listed = []
        for plugin in plugins:
            root = self.plugin_root(plugin.name)
            native = plugin.native_dir(self.harness_id)
            for path, problem in self.check_native(plugin):
                raise ValueError(f"{path}: {problem}")
            for skill in plugin.skills:
                self._emit_skill(skill, root, plugins, result)
            for command in plugin.commands:
                self._emit_command(command, root, plugins, result)
            for agent in plugin.agents:
                self._emit_agent(agent, plugins, result)
            self.copy_tree(native, root, result)
            self.note_claude_only(plugin, result)
            if plugin.skills or plugin.commands or plugin.native_files(self.harness_id):
                result.written.append(
                    self.write_json(root / ".codex-plugin" / "plugin.json", self.plugin_manifest(plugin))
                )
                listed.append(plugin)
        result.written.append(self.write_json(self.marketplace_path(), self.marketplace(listed)))
        return result

    def _emit_skill(self, skill: SkillSource, root: Path, plugins: list[PluginSource], result: EmitResult) -> None:
        if (skill.dir / "references" / OVERFLOW_NAME).exists():
            raise ValueError(f"skill `{skill.name}` already has references/{OVERFLOW_NAME}")
        dest = root / "skills" / skill.name
        text = rewrite_dispatch((skill.dir / "SKILL.md").read_text(encoding="utf-8"), plugins)
        content = self._fit(dest, *split_frontmatter(text), f"skill `{skill.name}`", result)
        self.emit_skill_copy(skill, dest, plugins, result, skill_md=content)

    def _emit_command(
        self, command: CommandSource, root: Path, plugins: list[PluginSource], result: EmitResult
    ) -> None:
        """Codex has no slash commands, so each command becomes a skill of the same name."""
        dest = root / "skills" / command.name
        fields: dict = {"name": command.name, "description": command.description}
        if command.argument_hint:
            fields["metadata"] = {"argument-hint": command.argument_hint}
        body = rewrite_dispatch(command.body, plugins).lstrip("\n")
        content = self._fit(dest, render_frontmatter(fields), body, f"command `{command.name}`", result)
        result.written.append(self.write(dest / "SKILL.md", content))

    def _fit(self, dest: Path, frontmatter: str, body: str, label: str, result: EmitResult) -> str:
        """Split a SKILL.md over the Codex cap, writing the overflow; return the SKILL.md text."""
        content, overflow = split_skill(frontmatter.rstrip("\n") + "\n\n", body, self.SKILL_FILE_CAP, OVERFLOW_NAME)
        if overflow is not None:
            result.notes.append(f"{label} is over the Codex prompt cap; tail moved to references/{OVERFLOW_NAME}")
            result.written.append(self.write(dest / "references" / OVERFLOW_NAME, overflow))
        return content

    def _emit_agent(self, agent: AgentSource, plugins: list[PluginSource], result: EmitResult) -> None:
        # validate.py rejects an unknown model alias or effort; here they are left out.
        name = namespaced(agent.plugin, agent.name)
        model = MODEL_ALIASES[self.harness_id].get(agent.model)
        effort = agent.effort if agent.effort in EFFORTS else None
        lines = [f"name = {toml_string(name)}", f"description = {toml_string(agent.description)}"]
        if model:
            lines.append(f"model = {toml_string(model)}")
        if effort:
            lines.append(f"model_reasoning_effort = {toml_string(effort)}")
        if agent.read_only:
            lines.append('sandbox_mode = "read-only"')
        instructions = rewrite_dispatch(agent.body, plugins).strip() + "\n"
        lines.append(f"developer_instructions = {toml_string(instructions)}")
        result.written.append(
            self.write(self.build() / "agents" / agent.plugin / f"{name}.toml", "\n".join(lines) + "\n")
        )

    # ── local marketplace ──

    def plugin_manifest(self, plugin: PluginSource) -> dict:
        """The Codex manifest. `hooks` and `mcpServers` name files from `harness/codex/` only."""
        m = plugin.manifest
        native = plugin.native_dir(self.harness_id)
        short = plugin.description
        if len(short) > 120:
            short = short[:117].rsplit(" ", 1)[0].rstrip(" ,.;:-") + "…"
        manifest = {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description or plugin.name,
            "author": m.get("author"),
            "homepage": m.get("homepage"),
            "repository": m.get("repository"),
            "license": m.get("license"),
            "keywords": m.get("keywords") or sorted(s.name for s in plugin.skills),
            "skills": "./skills/" if plugin.skills or plugin.commands else None,
            "hooks": "./hooks/hooks.json" if (native / "hooks" / "hooks.json").is_file() else None,
            "mcpServers": "./.mcp.json" if (native / ".mcp.json").is_file() else None,
            "interface": {
                "displayName": m.get("displayName") or plugin.name.replace("-", " ").title(),
                "shortDescription": short,
                "developerName": (m.get("author") or {}).get("name"),
                "category": CATEGORY,
            },
        }
        manifest["interface"] = {k: v for k, v in manifest["interface"].items() if v}
        return {k: v for k, v in manifest.items() if v}

    def marketplace(self, plugins: list[PluginSource]) -> dict:
        """The local marketplace, named like the Claude Code one."""
        root = read_marketplace(self.repo_root)
        owner = root.get("owner") or {}
        return {
            "name": root.get("name", "nanoboom"),
            "interface": {"displayName": owner.get("name") or root.get("name", "nanoboom")},
            "plugins": [
                {
                    "name": p.name,
                    "source": {"source": "local", "path": f"./plugins/{p.name}"},
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                    "category": CATEGORY,
                }
                for p in plugins
            ],
        }
