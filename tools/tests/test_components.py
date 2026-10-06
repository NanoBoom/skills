"""Every plugin component through every adapter, the validator, and the installer.

The kitchen-sink fixture carries one of each: skills (one over the Codex limit,
one with a script and a reference), a read-only agent and a writing agent, a
command, Claude Code hooks and MCP server, Codex hooks and MCP server under
`harness/codex/`, and Pi extensions under `harness/pi/`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from helpers import errors

from tools.adapters.base import load_plugins, parse_frontmatter
from tools.generate import generate
from tools.install import install, uninstall
from tools.validate import validate

PLUGIN = Path("build/codex/plugins/kitchen-sink")


def test_fixture_repository_validates(kitchen_repo: Path):
    findings = validate(kitchen_repo)
    assert findings.errors == []


def test_fixture_loads_every_component(kitchen_repo: Path):
    (plugin,) = load_plugins(kitchen_repo)
    assert [s.name for s in plugin.skills] == ["kitchen-long", "kitchen-skill"]
    assert [a.name for a in plugin.agents] == ["kitchen-reviewer", "kitchen-writer"]
    assert [c.name for c in plugin.commands] == ["kitchen-run"]
    assert set(plugin.hooks["hooks"]) == {"Stop", "PreToolUse"}
    assert set(plugin.mcp_servers["mcpServers"]) == {"kitchen-echo"}
    assert {p.name for p in plugin.native_files("codex")} == {"hooks.json", "codex-stop.sh", ".mcp.json"}
    assert plugin.load_errors == []


# ── Codex ────────────────────────────────────────────────────────────────────


def test_codex_marketplace_lists_the_plugin(kitchen_repo: Path):
    marketplace = json.loads((kitchen_repo / "build/codex/.agents/plugins/marketplace.json").read_text())
    assert marketplace["name"] == "kitchen"
    assert marketplace["plugins"][0]["source"] == {"source": "local", "path": "./plugins/kitchen-sink"}


def test_codex_plugin_takes_hooks_and_mcp_from_harness_codex_only(kitchen_repo: Path):
    root = kitchen_repo / PLUGIN
    manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
    assert manifest["skills"] == "./skills/"
    assert manifest["hooks"] == "./hooks/hooks.json"
    assert manifest["mcpServers"] == "./.mcp.json"
    source = kitchen_repo / "plugins/kitchen-sink/harness/codex"
    assert (root / "hooks/hooks.json").read_bytes() == (source / "hooks/hooks.json").read_bytes()
    assert (root / ".mcp.json").read_bytes() == (source / ".mcp.json").read_bytes()
    assert (root / "hooks/codex-stop.sh").stat().st_mode & 0o111
    # The Claude Code script is not copied: Codex gets only what harness/codex/ holds.
    assert not (root / "hooks/stop.sh").exists()


def test_codex_without_harness_dir_gets_no_hooks_or_mcp(kitchen_repo: Path):
    shutil.rmtree(kitchen_repo / "plugins/kitchen-sink/harness/codex")
    result = generate("codex", output_root=kitchen_repo, repo_root=kitchen_repo)
    root = kitchen_repo / PLUGIN
    manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
    assert "hooks" not in manifest and "mcpServers" not in manifest
    assert not (root / "hooks").exists() and not (root / ".mcp.json").exists()
    assert any("hooks/hooks.json and .mcp.json are Claude Code only" in s for s in result.notes)


def test_codex_turns_commands_into_skills(kitchen_repo: Path):
    skill = kitchen_repo / PLUGIN / "skills/kitchen-run/SKILL.md"
    fm, body = parse_frontmatter(skill.read_text())
    assert fm["name"] == "kitchen-run"
    assert fm["description"].startswith("Fixture command")
    assert fm["metadata"] == {"argument-hint": "<target>"}
    assert "`kitchen-sink__kitchen-writer`" in body and "kitchen-sink:" not in body


def test_codex_agents_map_read_only_and_writable(kitchen_repo: Path):
    reviewer = tomllib.loads(
        (kitchen_repo / "build/codex/agents/kitchen-sink/kitchen-sink__kitchen-reviewer.toml").read_text()
    )
    writer = tomllib.loads(
        (kitchen_repo / "build/codex/agents/kitchen-sink/kitchen-sink__kitchen-writer.toml").read_text()
    )
    assert reviewer["sandbox_mode"] == "read-only"
    assert reviewer["model"] == "gpt-6.1-sol" and reviewer["model_reasoning_effort"] == "high"
    assert "sandbox_mode" not in writer and "model" not in writer
    assert "kitchen-sink__kitchen-reviewer" in writer["developer_instructions"]


def test_codex_splits_the_long_skill_and_rewrites_references(kitchen_repo: Path):
    out = kitchen_repo / PLUGIN / "skills"
    assert len((out / "kitchen-long/SKILL.md").read_bytes()) <= 8000
    assert (out / "kitchen-long/references/codex-overflow.md").is_file()
    assert "kitchen-sink__kitchen-writer" in (out / "kitchen-skill/references/notes.md").read_text()
    script = out / "kitchen-skill/scripts/run.sh"
    assert script.stat().st_mode & 0o111


# ── Pi ───────────────────────────────────────────────────────────────────────


def test_pi_emits_prompts_and_maps_tools(kitchen_repo: Path):
    fm, body = parse_frontmatter((kitchen_repo / "build/pi/kitchen-sink/prompts/kitchen-run.md").read_text())
    assert fm["description"].startswith("Fixture command") and fm["argument-hint"] == "<target>"
    assert "$ARGUMENTS" in body
    writer, _ = parse_frontmatter(
        (kitchen_repo / "build/pi/kitchen-sink/agents/kitchen-sink__kitchen-writer.md").read_text()
    )
    assert writer["tools"] == "read, write, bash"
    reviewer, _ = parse_frontmatter(
        (kitchen_repo / "build/pi/kitchen-sink/agents/kitchen-sink__kitchen-reviewer.md").read_text()
    )
    assert "write" not in reviewer["tools"] and reviewer["model"] == "anthropic/claude-opus-5-5"


def test_pi_copies_extensions_unread_under_the_plugin_prefix(kitchen_repo: Path):
    out = kitchen_repo / "build/pi/kitchen-sink/extensions"
    source = kitchen_repo / "plugins/kitchen-sink/harness/pi/extensions"
    assert sorted(p.name for p in out.iterdir()) == ["kitchen-sink__kitchen-guard.ts", "kitchen-sink__kitchen-mcp"]
    assert (out / "kitchen-sink__kitchen-guard.ts").read_bytes() == (source / "kitchen-guard.ts").read_bytes()
    assert sorted(p.name for p in (out / "kitchen-sink__kitchen-mcp").iterdir()) == ["index.ts", "server.ts"]


def test_pi_without_harness_dir_reports_claude_only_hooks(kitchen_repo: Path):
    shutil.rmtree(kitchen_repo / "plugins/kitchen-sink/harness/pi")
    result = generate("pi", output_root=kitchen_repo, repo_root=kitchen_repo)
    assert not (kitchen_repo / "build/pi/kitchen-sink/extensions").exists()
    assert any("Claude Code only" in s for s in result.notes)


# ── Installer ────────────────────────────────────────────────────────────────


def test_install_pi_links_every_kind(kitchen_repo: Path, tmp_path: Path):
    home = tmp_path / "home"
    report = install("pi", repo_root=kitchen_repo, env={}, home=home)
    assert report.errors == []
    for rel in (
        ".pi/agent/prompts/kitchen-run.md",
        ".pi/agent/skills/kitchen-long/SKILL.md",
        ".pi/agent/agents/kitchen-sink__kitchen-writer.md",
        ".pi/agent/extensions/kitchen-sink__kitchen-guard.ts",
        ".pi/agent/extensions/kitchen-sink__kitchen-mcp/index.ts",
    ):
        assert (home / rel).is_file(), rel
    removed = uninstall("pi", repo_root=kitchen_repo, env={}, home=home)
    assert removed.removed == report.linked
    assert not (home / ".pi/agent/extensions").exists()


def test_install_codex_links_agents_and_installs_plugins(kitchen_repo: Path, tmp_path: Path, fake_codex):
    home = tmp_path / "home"
    codex = fake_codex()
    report = install("codex", repo_root=kitchen_repo, env={}, home=home, run=codex)
    assert report.errors == [] and report.plugins == 1
    assert (home / ".codex/agents/kitchen-sink__kitchen-writer.toml").is_symlink()
    build = str((kitchen_repo / "build/codex").resolve())
    assert codex.calls[:2] == [["plugin", "marketplace", "add", build], ["plugin", "add", "kitchen-sink@kitchen"]]


def test_install_codex_removes_plugins_no_longer_built(kitchen_repo: Path, tmp_path: Path, fake_codex):
    build = str((kitchen_repo / "build/codex").resolve())
    stale = {"pluginId": "gone@kitchen", "marketplaceSource": {"source": build}}
    other = {"pluginId": "theirs@elsewhere", "marketplaceSource": {"source": "/somewhere/else"}}
    codex = fake_codex(installed=[stale, other])
    report = install("codex", repo_root=kitchen_repo, env={}, home=tmp_path, only="plugins", run=codex)
    assert report.errors == [] and report.removed == 1
    assert ["plugin", "remove", "gone@kitchen"] in codex.calls
    assert ["plugin", "remove", "theirs@elsewhere"] not in codex.calls


def test_uninstall_codex_removes_only_this_checkouts_plugins(kitchen_repo: Path, tmp_path: Path, fake_codex):
    build = str((kitchen_repo / "build/codex").resolve())
    codex = fake_codex(
        installed=[
            {"pluginId": "kitchen-sink@kitchen", "marketplaceSource": {"source": build}},
            {"pluginId": "theirs@kitchen", "marketplaceSource": {"source": "/a/github/clone"}},
        ],
        marketplaces=[{"name": "kitchen", "root": build}, {"name": "other", "root": "/elsewhere"}],
    )
    report = uninstall("codex", repo_root=kitchen_repo, env={}, home=tmp_path, run=codex)
    assert report.errors == []
    assert ["plugin", "remove", "kitchen-sink@kitchen"] in codex.calls
    assert ["plugin", "marketplace", "remove", "kitchen"] in codex.calls
    assert not any(c[-1] in ("theirs@kitchen", "other") for c in codex.calls if "remove" in c)


def test_install_codex_explains_a_marketplace_name_clash(kitchen_repo: Path, tmp_path: Path):
    def clash(args, env):
        return subprocess.CompletedProcess(
            args, 1, "", "Error: marketplace 'kitchen' is already added from a different source"
        )

    report = install("codex", repo_root=kitchen_repo, env={}, home=tmp_path, only="plugins", run=clash)
    assert any("codex plugin marketplace remove kitchen" in e for e in report.errors)


@pytest.mark.skipif(shutil.which("codex") is None, reason="needs the Codex CLI")
def test_codex_cli_installs_and_removes_the_plugin(kitchen_repo: Path, tmp_path: Path, real_codex):
    """End to end against the real Codex CLI, in a throwaway CODEX_HOME."""
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    env = {**os.environ, "CODEX_HOME": str(codex_home)}
    report = install("codex", repo_root=kitchen_repo, env=env, home=tmp_path, run=real_codex)
    assert report.errors == [] and report.plugins == 1
    (cached,) = (codex_home / "plugins/cache/kitchen/kitchen-sink").iterdir()
    for rel in ("hooks/hooks.json", ".mcp.json", "skills/kitchen-run/SKILL.md", ".codex-plugin/plugin.json"):
        assert (cached / rel).is_file(), rel
    assert 'plugins."kitchen-sink@kitchen"' in (codex_home / "config.toml").read_text()

    removed = uninstall("codex", repo_root=kitchen_repo, env=env, home=tmp_path, run=real_codex)
    assert removed.errors == []
    config = (codex_home / "config.toml").read_text()
    assert "kitchen-sink@kitchen" not in config and "marketplaces.kitchen" not in config
    assert not (codex_home / "agents/kitchen-sink__kitchen-writer.toml").exists()


# ── Validator ────────────────────────────────────────────────────────────────


def test_command_without_description_fails(kitchen_repo: Path):
    cmd = kitchen_repo / "plugins/kitchen-sink/commands/kitchen-run.md"
    cmd.write_text(cmd.read_text().replace("description: Fixture command", "summary: Fixture command"))
    assert any("kitchen-run.md: frontmatter is missing `description`" in e for e in errors(kitchen_repo))


def test_command_named_like_a_skill_fails(kitchen_repo: Path):
    commands = kitchen_repo / "plugins/kitchen-sink/commands"
    (commands / "kitchen-run.md").rename(commands / "kitchen-skill.md")
    assert any("also a skill" in e for e in errors(kitchen_repo))


def test_command_dispatching_a_missing_agent_fails(kitchen_repo: Path):
    cmd = kitchen_repo / "plugins/kitchen-sink/commands/kitchen-run.md"
    cmd.write_text(cmd.read_text() + "\nThen `kitchen-sink:kitchen-ghost`.\n")
    assert any("kitchen-sink:kitchen-ghost" in e for e in errors(kitchen_repo))


def test_broken_hooks_json_fails(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/hooks/hooks.json").write_text("{not json")
    assert any("hooks/hooks.json: cannot parse" in e for e in errors(kitchen_repo))


def test_malformed_hook_group_fails(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/hooks/hooks.json").write_text(json.dumps({"hooks": {"Stop": [{}]}}))
    assert any("`Stop` must be a list" in e for e in errors(kitchen_repo))


def test_mcp_server_without_command_fails(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/.mcp.json").write_text(json.dumps({"mcpServers": {"x": {}}}))
    assert any("server `x` needs a `command` or a `url`" in e for e in errors(kitchen_repo))


def test_nested_command_fails(kitchen_repo: Path):
    nested = kitchen_repo / "plugins/kitchen-sink/commands/sub"
    nested.mkdir()
    (nested / "deep.md").write_text("---\ndescription: Deep\n---\n\nBody\n")
    assert any("commands must sit directly in commands/" in e for e in errors(kitchen_repo))


def test_codex_hooks_are_checked_against_the_codex_plugin_root(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/harness/codex/hooks/codex-stop.sh").unlink()
    assert any(
        "does not exist: plugins/kitchen-sink/harness/codex/hooks/codex-stop.sh" in e for e in errors(kitchen_repo)
    )


def test_broken_codex_mcp_json_fails(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/harness/codex/.mcp.json").write_text("[]")
    assert any("harness/codex/.mcp.json: must be a JSON object" in e for e in errors(kitchen_repo))


@pytest.mark.parametrize(
    ("make", "message"),
    [
        (lambda h: (h / "cursor").mkdir(), "not a harness directory"),
        (lambda h: (h / "codex/skills").mkdir(), "the Codex adapter writes this path"),
        (lambda h: (h / "pi/hooks").mkdir(), "harness/pi/ holds only extensions/"),
        (lambda h: (h / "pi/extensions/empty-dir").mkdir(), "needs index.ts or index.js"),
        (lambda h: (h / "pi/extensions/notes.md").write_text("x"), "a .ts or .js file"),
    ],
)
def test_misplaced_harness_files_fail(kitchen_repo: Path, make, message: str):
    make(kitchen_repo / "plugins/kitchen-sink/harness")
    assert any(message in e for e in errors(kitchen_repo))


def test_empty_hooks_object_fails(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/hooks/hooks.json").write_text("{}")
    assert any("needs a non-empty `hooks` object" in e for e in errors(kitchen_repo))


def test_hook_script_must_be_executable(kitchen_repo: Path):
    (kitchen_repo / "plugins/kitchen-sink/harness/codex/hooks/codex-stop.sh").chmod(0o644)
    assert any("hook script is not executable" in e for e in errors(kitchen_repo))


def test_block_list_at_key_indentation_keeps_an_agent_read_only(kitchen_repo: Path):
    agent = kitchen_repo / "plugins/kitchen-sink/agents/kitchen-reviewer.md"
    text = agent.read_text()
    fm_end = text.index("\n---", 3)
    lines = [ln for ln in text[:fm_end].splitlines() if not ln.startswith(("disallowedTools", "tools"))]
    agent.write_text("\n".join([*lines, "disallowedTools:", "- Write", "- Edit"]) + text[fm_end:])
    generate("codex", output_root=kitchen_repo, repo_root=kitchen_repo)
    generate("pi", output_root=kitchen_repo, repo_root=kitchen_repo)
    toml = tomllib.loads(
        (kitchen_repo / "build/codex/agents/kitchen-sink/kitchen-sink__kitchen-reviewer.toml").read_text()
    )
    assert toml["sandbox_mode"] == "read-only"
    pi, _ = parse_frontmatter(
        (kitchen_repo / "build/pi/kitchen-sink/agents/kitchen-sink__kitchen-reviewer.md").read_text()
    )
    assert "write" not in pi["tools"]


def test_frontmatter_that_is_not_yaml_is_one_error(kitchen_repo: Path):
    """`Example: ...` inside a plain scalar is a YAML error; report it, do not crash."""
    skill = kitchen_repo / "plugins/kitchen-sink/skills/kitchen-skill/SKILL.md"
    skill.write_text(skill.read_text().replace("\n---", "\n  Example: when the user asks for the fixture\n---", 1))
    found = errors(kitchen_repo)
    assert [e for e in found if "kitchen-skill" in e] == [
        "plugins/kitchen-sink: skills/kitchen-skill/SKILL.md: frontmatter is not valid YAML at line 4: "
        "mapping values are not allowed here"
    ]


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        (
            lambda b: (b / "codex/agents/kitchen-sink/kitchen-sink__kitchen-writer.toml").write_text(
                'name = "wrong"\ndescription = "d"\ndeveloper_instructions = "x"\n'
            ),
            "`name` must equal the file name",
        ),
        (lambda b: (b / "codex/plugins/kitchen-sink/.mcp.json").unlink(), "`mcpServers` names ./.mcp.json"),
        (
            lambda b: (b / "codex/plugins/kitchen-sink/skills/kitchen-skill/SKILL.md").write_text("x" * 8100),
            "Codex truncates at 8000",
        ),
        (
            lambda b: (b / "pi/kitchen-sink/skills/kitchen-skill/SKILL.md").write_text(
                "Use `kitchen-sink:kitchen-writer`."
            ),
            "still dispatches `kitchen-sink:kitchen-writer`",
        ),
        (lambda b: (b / "pi/kitchen-sink/prompts/kitchen-run.md").write_text("no frontmatter"), "needs a description"),
        (
            lambda b: (b / "pi/kitchen-sink/agents/kitchen-sink__kitchen-writer.md").write_text("---\nname: x\n---\n"),
            "needs `name` equal to the file name",
        ),
    ],
)
def test_generated_artifact_checks_catch_corruption(kitchen_repo: Path, corrupt, message: str):
    from tools.validate import Findings, check_codex, check_pi, check_rewritten

    corrupt(kitchen_repo / "build")
    files = {h: [p for p in (kitchen_repo / "build" / h).rglob("*") if p.is_file()] for h in ("codex", "pi")}
    f = Findings()
    check_codex(kitchen_repo, files["codex"], f)
    check_pi(kitchen_repo, files["pi"], f)
    check_rewritten(kitchen_repo, files["codex"] + files["pi"], load_plugins(kitchen_repo), f)
    assert any(message in e for e in f.errors), f.errors
