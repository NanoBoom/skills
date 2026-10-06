#!/usr/bin/env python3
"""Check the repository contract in AGENTS.md, then every generated artifact.

    uv run tools/validate.py [--strict]

Source checks cover manifests, skills, agents, hooks, MCP servers, each plugin's
`harness/` directory, and the three places a skill is promoted. When the source
passes, generated checks run every adapter into a temporary directory and check
the files it wrote, so they never depend on what is in the working tree.

Exits non-zero on any error, and with --strict on any warning too.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.adapters import ADAPTERS, generated_harnesses
from tools.adapters.base import (
    HARNESS_DIR,
    REPO_ROOT,
    SCOPED_NAME,
    FrontmatterError,
    PluginSource,
    field_text,
    load_plugins,
    parse_frontmatter,
    read_json_object,
    read_marketplace,
    split_frontmatter,
)
from tools.adapters.capabilities import EFFORTS, SOURCE_MODELS
from tools.adapters.codex import CodexAdapter
from tools.adapters.pi import PiAdapter
from tools.generate import generate

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Plugins that promise `npx skills` users a single copied SKILL.md still works: no
# agents, no hooks, no plugin root paths, no dispatch into another plugin.
SELF_CONTAINED = {"github-project"}


class Findings:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


# ── Source ───────────────────────────────────────────────────────────────────


def check_marketplace(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    marketplace = read_marketplace(root)
    entries = {e.get("name"): e for e in marketplace.get("plugins", [])}
    for plugin in plugins:
        where = f"plugins/{plugin.name}/.claude-plugin/plugin.json"
        if not KEBAB.match(plugin.name):
            f.err(f"plugins/{plugin.name}", "plugin directory name must be kebab-case")
        if plugin.manifest.get("name") != plugin.name:
            f.err(where, f"`name` must equal the directory name `{plugin.name}`; scoped names resolve by it")
        if "skills" in plugin.manifest:
            f.err(where, "remove `skills`: Claude Code discovers skills/ on its own, and a list drifts")
        entry = entries.pop(plugin.name, None)
        if entry is None:
            f.err(".claude-plugin/marketplace.json", f"no entry for plugin `{plugin.name}`")
            continue
        if entry.get("source") != f"./plugins/{plugin.name}":
            f.err(".claude-plugin/marketplace.json", f"`source` for `{plugin.name}` must be `./plugins/{plugin.name}`")
        if entry.get("version") != plugin.version:
            f.err(
                ".claude-plugin/marketplace.json",
                f"version drift for `{plugin.name}`: entry {entry.get('version')} vs plugin.json {plugin.version}",
            )
    for name in entries:
        f.err(".claude-plugin/marketplace.json", f"entry `{name}` has no plugins/{name}/.claude-plugin/plugin.json")


def check_skills(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    owners: dict[str, str] = {}
    for plugin in plugins:
        for skill in plugin.skills:
            where = rel(skill.dir, root)
            if skill.name in owners:
                f.err(where, f"skill name also used in plugin `{owners[skill.name]}`; installs use the bare name")
            owners[skill.name] = plugin.name
            skill_md = skill.dir / "SKILL.md"
            if not skill_md.is_file():
                f.err(where, "directory has no SKILL.md")
                continue
            fm = skill.frontmatter
            if not fm:
                if not split_frontmatter(skill_md.read_text(encoding="utf-8"))[0]:
                    f.err(where, "SKILL.md has no frontmatter")
                continue  # otherwise it does not parse, which load_errors reports
            name = field_text(fm, "name")
            if not name:
                f.err(where, "frontmatter is missing `name`")
            elif name != skill.name:
                f.err(where, f"frontmatter `name` is `{name}` but the directory is `{skill.name}`")
            elif not KEBAB.match(name) or len(name) > 64:
                f.err(where, "`name` must be kebab-case and at most 64 characters")
            if not skill.description:
                f.err(where, "frontmatter is missing `description`")
            elif len(skill.description) > 1024:
                f.err(where, f"`description` is {len(skill.description)} characters; the Agent Skills spec allows 1024")
            lines = skill_md.read_text(encoding="utf-8").count("\n")
            if lines > 500:
                f.warn(where, f"SKILL.md is {lines} lines; move detail into references/")

            for file in skill.files():
                try:
                    text = file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                check_portable_text(text, rel(file, root), plugin, plugins, f)


def check_portable_text(text: str, at: str, plugin: PluginSource, plugins: list[PluginSource], f: Findings) -> None:
    """Rules for any text a non-Claude harness receives: skills, references, commands."""
    if "${CLAUDE_PLUGIN_ROOT}/" in text:
        f.err(at, 'uses ${CLAUDE_PLUGIN_ROOT}, which only Claude Code resolves; say "this skill\'s directory" instead')
    plugin_names = {p.name for p in plugins}
    for m in SCOPED_NAME.finditer(text):
        target_plugin, target = m.groups()
        if target_plugin not in plugin_names:
            continue
        if plugin.name in SELF_CONTAINED and target_plugin != plugin.name:
            f.err(at, f"dispatches `{m.group(0)}` from another plugin; {plugin.name} is self-contained")
            continue
        other = next(p for p in plugins if p.name == target_plugin)
        known = other.agent_names() | {s.name for s in other.skills} | {c.name for c in other.commands} | {"<agent>"}
        if target not in known:
            f.err(at, f"`{m.group(0)}` is neither an agent, a skill, nor a command in plugins/{target_plugin}")


def check_commands(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    """Codex installs a command as a skill of the same name, so the two share one namespace."""
    taken = {s.name: f"skill in {p.name}" for p in plugins for s in p.skills}
    for plugin in plugins:
        commands_dir = plugin.dir / "commands"
        for path in sorted(commands_dir.rglob("*.md")) if commands_dir.is_dir() else []:
            if path.parent != commands_dir:
                f.err(rel(path, root), "commands must sit directly in commands/; adapters do not read subdirectories")
        for command in plugin.commands:
            where = rel(command.path, root)
            if not KEBAB.match(command.name):
                f.err(where, "command file name must be kebab-case")
            if command.name in taken:
                f.err(where, f"command name is also a {taken[command.name]}; Codex installs commands as skills")
            taken[command.name] = f"command in {plugin.name}"
            if not command.description:
                f.err(where, "frontmatter is missing `description`")
            if not command.body.strip():
                f.err(where, "command has no body")
            check_portable_text(command.path.read_text(encoding="utf-8"), where, plugin, plugins, f)


def check_agents(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    for plugin in plugins:
        if plugin.name in SELF_CONTAINED and (
            plugin.agents or (plugin.dir / "hooks").exists() or (plugin.dir / HARNESS_DIR).exists()
        ):
            f.err(f"plugins/{plugin.name}", "a self-contained plugin ships no agents, no hooks, and no harness/")
        for agent in plugin.agents:
            where = rel(agent.path, root)
            if not KEBAB.match(agent.name):
                f.err(where, "agent file name must be kebab-case; generated names join plugin and agent with `__`")
            if agent.frontmatter.get("name") != agent.name:
                f.err(where, "frontmatter `name` must equal the file name")
            if not agent.description:
                f.err(where, "frontmatter is missing `description`")
            if agent.model not in SOURCE_MODELS:
                f.err(where, f"`model: {agent.model}` is not one of {sorted(SOURCE_MODELS)}; adapters cannot map it")
            if agent.effort and agent.effort not in EFFORTS:
                f.err(where, f"`effort: {agent.effort}` is not one of {sorted(EFFORTS)}")
            if not agent.body.strip():
                f.err(where, "agent has no prompt body")


def check_hooks(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    """Claude Code's hooks/hooks.json, and Codex's in harness/codex/, share one shape."""
    for plugin in plugins:
        if plugin.hooks is not None:
            check_hooks_file(plugin.hooks_path, plugin.hooks, plugin.dir, root, f)
        codex = plugin.native_dir("codex")
        if (data := _json_file(codex / "hooks" / "hooks.json", root, f)) is not None:
            check_hooks_file(codex / "hooks" / "hooks.json", data, codex, root, f)


def check_hooks_file(path: Path, data: dict, plugin_root: Path, root: Path, f: Findings) -> None:
    """`plugin_root` is what ${CLAUDE_PLUGIN_ROOT} resolves to when the hooks run."""
    events = data.get("hooks")
    if not isinstance(events, dict) or not events:
        f.err(rel(path, root), "needs a non-empty `hooks` object keyed by event name")
        return
    for event, groups in events.items():
        if not isinstance(groups, list) or not all(
            isinstance(g, dict) and isinstance(g.get("hooks"), list) and g["hooks"] for g in groups
        ):
            f.err(rel(path, root), f"`{event}` must be a list of {{matcher?, hooks: [...]}} groups")
            continue
        for hook in (h for g in groups for h in g["hooks"]):
            if hook.get("type") == "command" and not hook.get("command"):
                f.err(rel(path, root), f"a `{event}` command hook has no `command`")
    for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"'\s\\]+)", path.read_text(encoding="utf-8")):
        target = plugin_root / m.group(1)
        if not target.is_file():
            f.err(rel(path, root), f"command path does not exist: {rel(target, root)}")
        elif not target.stat().st_mode & 0o111:
            f.err(rel(target, root), "hook script is not executable")


def check_mcp(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    for plugin in plugins:
        if plugin.mcp_servers is not None:
            check_mcp_file(plugin.mcp_path, plugin.mcp_servers, root, f)
        path = plugin.native_dir("codex") / ".mcp.json"
        if (data := _json_file(path, root, f)) is not None:
            check_mcp_file(path, data, root, f)


def check_mcp_file(path: Path, data: dict, root: Path, f: Findings) -> None:
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        f.err(rel(path, root), "needs a non-empty `mcpServers` object")
        return
    for name, server in servers.items():
        if not isinstance(server, dict) or not (server.get("command") or server.get("url")):
            f.err(rel(path, root), f"server `{name}` needs a `command` or a `url`")


def _json_file(path: Path, root: Path, f: Findings) -> dict | None:
    if not path.is_file():
        return None
    data, error = read_json_object(path)
    if error:
        f.err(rel(path, root), error)
    return data


def check_harness_dirs(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    """Where files sit in `harness/`. Each adapter owns the rules for its own directory."""
    for plugin in plugins:
        base = plugin.dir / HARNESS_DIR
        for entry in sorted(base.iterdir()) if base.is_dir() else []:
            if entry.name not in ADAPTERS or not entry.is_dir():
                f.err(rel(entry, root), f"not a harness directory; use one of {', '.join(generated_harnesses())}")
        for adapter in ADAPTERS.values():
            for path, problem in adapter.check_native(plugin):
                f.err(rel(path, root), problem)


def check_promotion(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    top_readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").is_file() else ""
    skills_sh = json.loads((root / "skills.sh.json").read_text(encoding="utf-8"))
    grouped = {name for g in skills_sh.get("groupings", []) for name in g.get("skills", [])}
    all_skills = set()
    for plugin in plugins:
        readme_path = plugin.dir / "README.md"
        readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
        if not readme:
            f.err(f"plugins/{plugin.name}", "plugin has no README.md")
        for skill in plugin.skills:
            all_skills.add(skill.name)
            where = rel(skill.dir, root)
            if f"(./skills/{skill.name}/SKILL.md)" not in readme:
                f.err(where, f"not linked from plugins/{plugin.name}/README.md")
            if not re.search(rf"[:`/]{re.escape(skill.name)}`", top_readme):
                f.err(where, "not listed in the top-level README.md")
            if skill.name not in grouped:
                f.err(where, "not in any grouping in skills.sh.json")
    for name in sorted(grouped - all_skills):
        f.err("skills.sh.json", f"groups `{name}`, which is not a skill in plugins/")


# ── Generated ────────────────────────────────────────────────────────────────


def check_generated(plugins: list[PluginSource], root: Path, f: Findings) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp).resolve()
        written: dict[str, list[Path]] = {}
        for harness in generated_harnesses():
            try:
                result = generate(harness, output_root=out, repo_root=root)
            except Exception as e:  # noqa: BLE001 - report the adapter failure as a finding
                f.err(f"generate {harness}", f"{type(e).__name__}: {e}")
                continue
            written[harness] = result.written
            for w in result.warnings:
                f.warn(f"generate {harness}", w)

        check_codex(out, written.get("codex", []), f)
        check_pi(out, written.get("pi", []), f)
        check_rewritten(out, [p for files in written.values() for p in files], plugins, f)


def _rel(path: Path, out: Path) -> str:
    return str(path.resolve().relative_to(out.resolve()))


def check_rewritten(out: Path, files: list[Path], plugins: list[PluginSource], f: Findings) -> None:
    """No generated skill or prompt may still name an agent by its Claude Code scoped name."""
    agents = {(p.name, a) for p in plugins for a in p.agent_names()}
    for path in sorted(files):
        if not {"skills", "prompts"} & set(path.resolve().relative_to(out.resolve()).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if m := next((m for m in SCOPED_NAME.finditer(text) if m.groups() in agents), None):
            f.err(_rel(path, out), f"still dispatches `{m.group(0)}` after rewriting")


def check_codex(out: Path, files: list[Path], f: Findings) -> None:
    """The files the Codex adapter wrote: agent TOML, skill sizes, plugin manifests."""
    for toml_path in sorted(p for p in files if p.suffix == ".toml"):
        where = _rel(toml_path, out)
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            f.err(where, f"invalid TOML: {e}")
            continue
        for key in ("name", "description", "developer_instructions"):
            if not data.get(key):
                f.err(where, f"missing `{key}`")
        if data.get("name") != toml_path.stem:
            f.err(where, "`name` must equal the file name")
        if "model_reasoning_effort" in data and data["model_reasoning_effort"] not in EFFORTS:
            f.err(where, f"invalid model_reasoning_effort `{data['model_reasoning_effort']}`")
    cap = CodexAdapter.PROMPT_CAP
    for skill_md in sorted(p for p in files if p.name == "SKILL.md"):
        if (size := len(skill_md.read_bytes())) > cap:
            f.err(_rel(skill_md.parent, out), f"SKILL.md is {size} bytes; Codex truncates at {cap}")
    for manifest_path in sorted(p for p in files if p.parent.name == ".codex-plugin"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("skills", "hooks", "mcpServers"):
            if key in manifest and not (manifest_path.parent.parent / manifest[key]).exists():
                f.err(_rel(manifest_path, out), f"`{key}` names {manifest[key]}, which was not generated")


def check_pi(out: Path, files: list[Path], f: Findings) -> None:
    """The prompt templates and agents the Pi adapter wrote."""
    build = out.resolve() / PiAdapter.build()
    # Only `build/pi/<plugin>/{prompts,agents}/`; a skill may have its own `agents/`.
    for path in sorted(p for p in files if p.suffix == ".md" and p.resolve().parent.parent.parent == build):
        try:
            fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except FrontmatterError as e:
            f.err(_rel(path, out), str(e))
            continue
        if path.parent.name == "prompts" and (not fm.get("description") or not body.strip()):
            f.err(_rel(path, out), "needs a description and a body")
        if path.parent.name == "agents" and (
            fm.get("name") != path.stem or not fm.get("description") or not body.strip()
        ):
            f.err(_rel(path, out), "needs `name` equal to the file name, a description, and a body")


# ── Entry point ──────────────────────────────────────────────────────────────


def validate(root: Path = REPO_ROOT) -> Findings:
    f = Findings()
    plugins = load_plugins(root)
    if not plugins:
        f.err("plugins/", "no plugin found")
        return f
    for plugin in plugins:
        for message in plugin.load_errors:
            f.err(f"plugins/{plugin.name}", message)
    check_marketplace(plugins, root, f)
    check_skills(plugins, root, f)
    check_commands(plugins, root, f)
    check_agents(plugins, root, f)
    check_hooks(plugins, root, f)
    check_mcp(plugins, root, f)
    check_harness_dirs(plugins, root, f)
    check_promotion(plugins, root, f)
    if not f.errors:
        # Generated output of a broken source repeats its errors; check it once the source passes.
        check_generated(plugins, root, f)
    return f


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args()

    f = validate()
    for w in f.warnings:
        print(f"warn  {w}", file=sys.stderr)
    for e in f.errors:
        print(f"error {e}", file=sys.stderr)

    plugins = load_plugins()
    counted = (
        f"{sum(len(p.skills) for p in plugins)} skill(s) and {sum(len(p.agents) for p in plugins)} agent(s) "
        f"in {len(plugins)} plugin(s), {len(generated_harnesses())} generated harness(es)"
    )
    if f.errors or (args.strict and f.warnings):
        print(f"\nFAIL  {len(f.errors)} error(s), {len(f.warnings)} warning(s) across {counted}", file=sys.stderr)
        return 1
    print(f"OK    {counted}, {len(f.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
