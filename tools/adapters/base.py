"""Source models, parsing, and the adapter base class shared by every harness.

The source of truth is `plugins/<plugin>/` in the Claude Code plugin format. An
adapter reads it through `load_plugins()` and writes harness-native artifacts
under its `output_root`. Sources are never modified.

Frontmatter is YAML, read and written with PyYAML. The adapter layout follows
wshobson/agents `tools/adapters/base.py` (MIT). See NOTICE.
"""

from __future__ import annotations

import json
import re
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tools.adapters.capabilities import WRITE_TOOLS

REPO_ROOT = Path(__file__).resolve().parents[2]

# `plugins/<plugin>/harness/<harness>/` holds files a plugin author writes in one
# harness's own format, such as Codex hooks or a Pi extension. Adapters copy them
# without reading them.
HARNESS_DIR = "harness"

# Never copied out of a source tree: VCS and editor litter, bytecode caches.
_COPY_IGNORE = frozenset({".git", ".DS_Store", "__pycache__", "node_modules"})

# Separates plugin and component in generated names: `prp-core__code-reviewer`.
# Claude Code scopes the same agent as `prp-core:code-reviewer`; the colon is not a
# safe filename character everywhere and no other harness documents it in names.
NAMESPACE_SEP = "__"

# A Claude Code scoped name, `<plugin>:<component>`, not inside a path or a word.
# `<agent>` is the documentation placeholder. Rewriting and validation share it.
SCOPED_NAME = re.compile(r"(?<![\w/-])([a-z0-9][a-z0-9-]*):(<agent>|[a-z0-9][a-z0-9-]*)")


# ── Frontmatter ──────────────────────────────────────────────────────────────


def split_frontmatter(content: str) -> tuple[str, str]:
    """Return (frontmatter block including both `---` lines, body). Block is '' if absent."""
    if not content.startswith("---"):
        return "", content
    end = content.find("\n---", 3)
    if end == -1:
        return "", content
    close = content.find("\n", end + 4)
    close = len(content) if close == -1 else close + 1
    return content[:close], content[close:].lstrip("\n")


class FrontmatterError(ValueError):
    """A frontmatter block that is not a YAML mapping."""


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Return (fields, body). Raises FrontmatterError when the block is not a YAML mapping."""
    block, body = split_frontmatter(content)
    if not block:
        return {}, content
    try:
        fields = yaml.safe_load("\n".join(block.splitlines()[1:-1]))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 2}" if mark else ""  # +2: the opening `---`, and 1-based
        raise FrontmatterError(f"frontmatter is not valid YAML{where}: {getattr(e, 'problem', None) or e}") from e
    if fields is None:
        return {}, body
    if not isinstance(fields, dict):
        raise FrontmatterError("frontmatter must be a YAML mapping")
    return fields, body


def field_text(fields: dict, key: str) -> str:
    """A frontmatter value as text. YAML reads `on`, `1.0`, or a date as other types."""
    value = fields.get(key)
    return "" if value is None else str(value).strip()


def split_list(raw) -> list[str]:
    """Normalize `tools:`-style values, given as `A, B` or a list, into names."""
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return []


def render_frontmatter(fields: dict) -> str:
    """Render a frontmatter block, leaving out fields whose value is None."""
    data = {k: v for k, v in fields.items() if v is not None}
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=float("inf")) + "---\n"


# ── Source models ────────────────────────────────────────────────────────────


@dataclass
class AgentSource:
    """plugins/<plugin>/agents/<name>.md"""

    plugin: str
    name: str
    path: Path
    frontmatter: dict
    body: str

    @property
    def description(self) -> str:
        return field_text(self.frontmatter, "description")

    @property
    def model(self) -> str:
        return field_text(self.frontmatter, "model") or "inherit"

    @property
    def effort(self) -> str | None:
        return field_text(self.frontmatter, "effort") or None

    @property
    def tools(self) -> list[str] | None:
        """The allowlist, or None when the agent sets none and so may use every tool."""
        if "tools" not in self.frontmatter:
            return None
        return split_list(self.frontmatter["tools"])

    @property
    def disallowed_tools(self) -> list[str]:
        return split_list(self.frontmatter.get("disallowedTools"))

    @property
    def read_only(self) -> bool:
        """True when the agent can use no file-writing tool."""
        if self.tools is not None:
            return not (set(self.tools) & WRITE_TOOLS)
        return {"Write", "Edit"} <= set(self.disallowed_tools)


@dataclass
class SkillSource:
    """plugins/<plugin>/skills/<name>/SKILL.md and everything beside it."""

    plugin: str
    name: str
    dir: Path
    frontmatter: dict
    body: str

    @property
    def description(self) -> str:
        return field_text(self.frontmatter, "description")

    def files(self) -> list[Path]:
        """Every file in the skill directory, skipping dot-entries and bytecode caches."""
        return sorted(
            p
            for p in self.dir.rglob("*")
            if p.is_file()
            and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(self.dir).parts)
        )


@dataclass
class CommandSource:
    """plugins/<plugin>/commands/<name>.md, a slash command."""

    plugin: str
    name: str
    path: Path
    frontmatter: dict
    body: str

    @property
    def description(self) -> str:
        return field_text(self.frontmatter, "description")

    @property
    def argument_hint(self) -> str:
        return field_text(self.frontmatter, "argument-hint")


@dataclass
class PluginSource:
    """plugins/<name>/ as one unit.

    Components follow the Claude Code plugin layout: `skills/`, `agents/`,
    `commands/`, `hooks/hooks.json`, and `.mcp.json`. The last two are Claude
    Code's; every other harness takes hooks and MCP servers only from its own
    `harness/<harness>/` directory (`native_dir`). A file that cannot be parsed
    leaves its component empty and adds a message to `load_errors`, which
    validate.py reports, so one broken file does not stop every adapter.
    """

    name: str
    dir: Path
    manifest: dict
    agents: list[AgentSource] = field(default_factory=list)
    skills: list[SkillSource] = field(default_factory=list)
    commands: list[CommandSource] = field(default_factory=list)
    hooks: dict | None = None
    mcp_servers: dict | None = None
    load_errors: list[str] = field(default_factory=list)

    @property
    def description(self) -> str:
        return (self.manifest.get("description") or "").strip()

    @property
    def version(self) -> str:
        return (self.manifest.get("version") or "0.0.0").strip()

    def agent_names(self) -> set[str]:
        return {a.name for a in self.agents}

    @property
    def hooks_path(self) -> Path:
        return self.dir / "hooks" / "hooks.json"

    @property
    def mcp_path(self) -> Path:
        return self.dir / ".mcp.json"

    def native_dir(self, harness_id: str) -> Path:
        return self.dir / HARNESS_DIR / harness_id

    def native_files(self, harness_id: str) -> list[Path]:
        """Every file under `harness/<harness_id>/`, dot-files included."""
        return tree_files(self.native_dir(harness_id))


def tree_files(root: Path) -> list[Path]:
    """Every file under `root`, dot-files included, skipping `_COPY_IGNORE` entries."""
    if not root.is_dir():
        return []
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and not any(part in _COPY_IGNORE for part in p.relative_to(root).parts)
    )


def read_json_object(path: Path) -> tuple[dict | None, str | None]:
    """Parse a file holding one JSON object. Returns (data, None) or (None, why not)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return None, f"cannot parse ({e})"
    if not isinstance(data, dict):
        return None, "must be a JSON object"
    return data, None


def _load_json(path: Path, plugin: PluginSource) -> dict | None:
    data, error = read_json_object(path)
    if error:
        plugin.load_errors.append(f"{path.relative_to(plugin.dir)}: {error}")
    return data


def _read_frontmatter(path: Path, plugin: PluginSource) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    try:
        return parse_frontmatter(text)
    except FrontmatterError as e:
        plugin.load_errors.append(f"{path.relative_to(plugin.dir)}: {e}")
        return {}, split_frontmatter(text)[1]


def load_plugin(plugin_dir: Path) -> PluginSource:
    plugin = PluginSource(name=plugin_dir.name, dir=plugin_dir, manifest={})
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if manifest_path.is_file():
        plugin.manifest = _load_json(manifest_path, plugin) or {}

    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        for md in sorted(agents_dir.glob("*.md")):
            fm, body = _read_frontmatter(md, plugin)
            plugin.agents.append(AgentSource(plugin.name, md.stem, md, fm, body))

    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for sd in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            skill_md = sd / "SKILL.md"
            fm, body = _read_frontmatter(skill_md, plugin) if skill_md.is_file() else ({}, "")
            plugin.skills.append(SkillSource(plugin.name, sd.name, sd, fm, body))

    commands_dir = plugin_dir / "commands"
    if commands_dir.is_dir():
        for md in sorted(commands_dir.glob("*.md")):
            fm, body = _read_frontmatter(md, plugin)
            plugin.commands.append(CommandSource(plugin.name, md.stem, md, fm, body))

    if plugin.hooks_path.is_file():
        plugin.hooks = _load_json(plugin.hooks_path, plugin)
    if plugin.mcp_path.is_file():
        plugin.mcp_servers = _load_json(plugin.mcp_path, plugin)
    return plugin


def load_plugins(repo_root: Path = REPO_ROOT) -> list[PluginSource]:
    plugins_dir = repo_root / "plugins"
    if not plugins_dir.is_dir():
        return []
    return [
        load_plugin(d)
        for d in sorted(plugins_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".") and (d / ".claude-plugin" / "plugin.json").is_file()
    ]


def read_marketplace(repo_root: Path = REPO_ROOT) -> dict:
    path = repo_root / ".claude-plugin" / "marketplace.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


# ── Dispatch names ───────────────────────────────────────────────────────────


def namespaced(plugin: str, name: str) -> str:
    """The name a non-Claude harness knows a plugin's agent or extension by."""
    return f"{plugin}{NAMESPACE_SEP}{name}"


def rewrite_dispatch(text: str, plugins: list[PluginSource]) -> str:
    """Rewrite Claude Code scoped agent names (`prp-core:code-reviewer`) to `namespaced`.

    Only names of agents that exist are rewritten, plus the documentation placeholder
    `<plugin>:<agent>`. A scoped skill name such as `/prp-core:prp-plan` is left alone.
    """
    agents = {p.name: p.agent_names() for p in plugins if p.agents}

    def sub(m: re.Match) -> str:
        plugin, target = m.groups()
        if plugin in agents and (target in agents[plugin] or target == "<agent>"):
            return namespaced(plugin, target)
        return m.group(0)

    return SCOPED_NAME.sub(sub, text)


# ── Adapter base ─────────────────────────────────────────────────────────────


@dataclass
class EmitResult:
    """What an adapter wrote.

    `warnings` are problems worth fixing in the source. `notes` are expected and
    worth knowing, such as Claude Code hooks a harness does not get or a skill
    split to fit Codex; neither generate.py --strict nor validate.py counts them.
    """

    written: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InstallKind:
    """One kind of generated artifact and where tools/install.py puts it."""

    name: str
    source: str  # directory under the output root; `{plugin}` is filled in
    pattern: str  # glob inside `source`; each match is installed as one entry
    dest: str  # directory under the configuration root


class HarnessAdapter(ABC):
    """One harness: what it is called, where it is generated, and where it installs.

    The adapter owns `build/<harness_id>/` outright; generate.py wipes it before
    each run so a renamed or deleted source leaves nothing behind. It sits outside
    `.codex/` and `.pi/`, so running those tools in this checkout does not load it
    as project configuration.
    """

    harness_id: str = ""
    display_name: str = ""
    # The user configuration root: `$<user_env>`, else `~/<user_default>`. A
    # project install goes to `<project>/<project_dir>`.
    user_env: str = ""
    user_default: str = ""
    project_dir: str = ""
    # True when, at user level, the harness takes plugins through its own CLI.
    cli_plugins: bool = False

    def __init__(self, output_root: Path = REPO_ROOT, repo_root: Path = REPO_ROOT) -> None:
        self.output_root = output_root
        self.repo_root = repo_root

    @classmethod
    def build(cls) -> Path:
        return Path("build") / cls.harness_id

    @abstractmethod
    def emit(self, plugins: list[PluginSource]) -> EmitResult:
        """Write every artifact for the given plugins under `output_root`."""

    @classmethod
    @abstractmethod
    def install_kinds(cls, project: bool) -> tuple[InstallKind, ...]:
        """What tools/install.py installs file by file, for the user or a project."""

    @classmethod
    def check_native(cls, plugin: PluginSource) -> list[tuple[Path, str]]:
        """Problems with where files sit in `harness/<harness_id>/`. Contents are not read."""
        return []

    # ── helpers ──

    def note_claude_only(self, plugin: PluginSource, result: EmitResult) -> None:
        """Record Claude Code hooks and MCP servers this harness does not get.

        They are never translated. A plugin that wants them here writes this
        harness's own version under `harness/<harness_id>/`.
        """
        claude_only = [
            name for name, present in (("hooks/hooks.json", plugin.hooks), (".mcp.json", plugin.mcp_servers)) if present
        ]
        if claude_only and not plugin.native_dir(self.harness_id).is_dir():
            result.notes.append(
                f"{plugin.name}: {' and '.join(claude_only)} {'are' if len(claude_only) > 1 else 'is'} "
                "Claude Code only; "
                f"{self.display_name} gets hooks and MCP servers from "
                f"{HARNESS_DIR}/{self.harness_id}/, which this plugin does not have"
            )

    def copy_tree(self, src: Path, rel: str | Path, result: EmitResult) -> None:
        """Copy a directory byte for byte, keeping mode bits, under `output_root/rel`."""
        for file in tree_files(src):
            result.written.append(self.copy(file, Path(rel) / file.relative_to(src)))

    def _target(self, rel: str | Path) -> Path:
        target = (self.output_root / rel).resolve()
        if not target.is_relative_to(self.output_root.resolve()):
            raise ValueError(f"refusing to write outside output_root: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def write(self, rel: str | Path, content: str) -> Path:
        target = self._target(rel)
        target.write_text(content, encoding="utf-8")
        return target

    def write_json(self, rel: str | Path, data: dict) -> Path:
        return self.write(rel, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def copy(self, src: Path, rel: str | Path) -> Path:
        target = self._target(rel)
        shutil.copy2(src, target)
        return target

    def emit_skill_copy(
        self,
        skill: SkillSource,
        dest: Path,
        plugins: list[PluginSource],
        result: EmitResult,
        *,
        skill_md: str | None = None,
    ) -> None:
        """Copy a skill directory, rewriting dispatch names in every Markdown file.

        `skill_md` replaces the SKILL.md content when the adapter has already
        transformed it. Other files are copied byte for byte, so scripts keep their
        mode bits and binary assets stay intact.
        """
        for src in skill.files():
            rel = src.relative_to(skill.dir)
            if rel == Path("SKILL.md") and skill_md is not None:
                result.written.append(self.write(dest / rel, skill_md))
            elif src.suffix == ".md":
                result.written.append(
                    self.write(dest / rel, rewrite_dispatch(src.read_text(encoding="utf-8"), plugins))
                )
            else:
                result.written.append(self.copy(src, dest / rel))
