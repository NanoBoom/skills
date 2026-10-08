from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from tools.adapters.base import FrontmatterError, load_plugins, parse_frontmatter, render_frontmatter, rewrite_dispatch
from tools.adapters.codex import split_skill
from tools.generate import generate

PLUGINS = load_plugins()


def test_parse_frontmatter_reads_scalars_lists_and_folded_values():
    fm, body = parse_frontmatter(
        "---\nname: x\ntools: [Read, Grep]\ndisallowedTools: Write, Edit\ndescription: >-\n  one\n  two\n---\n\nBody\n"
    )
    assert fm == {"name": "x", "tools": ["Read", "Grep"], "disallowedTools": "Write, Edit", "description": "one two"}
    assert body == "Body\n"


def test_rendered_frontmatter_reads_back_unchanged():
    fields = {
        "name": "x",
        "description": 'key: value, "quoted", # not a comment',
        "argument-hint": "[--flag] <target>",
        "flag": "yes",
        "version": "1.0",
        "tools": ["read", "- dash"],
        "metadata": {"argument-hint": "<a>"},
        "dropped": None,
    }
    fm, body = parse_frontmatter(render_frontmatter(fields) + "\nBody\n")
    assert fm == {k: v for k, v in fields.items() if v is not None}
    assert body == "Body\n"


def test_invalid_frontmatter_names_the_line():
    with pytest.raises(FrontmatterError, match="not valid YAML at line 3"):
        parse_frontmatter("---\ndescription: one\n  Example: two\n---\nBody\n")


def test_rewrite_dispatch_touches_known_agents_only():
    text = "Use `prp-core:codebase-explorer`, then /prp-core:prp-plan, prp-core:<agent>, prp-core:nope."
    assert rewrite_dispatch(text, PLUGINS) == (
        "Use `prp-core__codebase-explorer`, then /prp-core:prp-plan, prp-core__<agent>, prp-core:nope."
    )


def test_split_skill_keeps_every_section_in_order():
    body = "# T\n\nintro\n" + "".join(f"## S{i}\n\n" + "x" * 900 + "\n" for i in range(12))
    head, overflow = split_skill("---\nname: t\n---\n\n", body, 4000, "o.md")
    assert len(head.encode()) <= 4000
    assert overflow is not None
    kept = head.split("> The rest of this skill")[0]
    assert (kept.rstrip("\n") + "\n" + overflow).count("## S") == 12
    assert overflow.startswith("## S")


def test_split_skill_leaves_small_skills_alone():
    head, overflow = split_skill("---\nname: t\n---\n\n", "# T\n", 4000, "o.md")
    assert overflow is None and head.endswith("# T\n")


def test_codex_agents_are_valid_toml_with_mapped_settings(tmp_path: Path):
    generate("codex", output_root=tmp_path)
    data = tomllib.loads((tmp_path / "build/codex/agents/prp-core/prp-core__root-cause-analyzer.toml").read_text())
    assert data["name"] == "prp-core__root-cause-analyzer"
    assert data["model"] == "gpt-6.1-sol"
    assert data["model_reasoning_effort"] == "xhigh"
    assert data["sandbox_mode"] == "read-only"
    source = next(a for p in PLUGINS for a in p.agents if a.name == "root-cause-analyzer")
    assert data["developer_instructions"].strip() == source.body.strip()


def test_codex_skills_fit_the_cap_and_lose_nothing(tmp_path: Path):
    generate("codex", output_root=tmp_path)
    for plugin in PLUGINS:
        for skill in plugin.skills:
            out = tmp_path / "build/codex/plugins" / plugin.name / "skills" / skill.name
            assert len((out / "SKILL.md").read_bytes()) <= 8000
            overflow = out / "references/codex-overflow.md"
            generated = (out / "SKILL.md").read_text() + (overflow.read_text() if overflow.exists() else "")
            for line in skill.body.splitlines():
                if line.startswith("## "):
                    assert line in generated, f"{skill.name} lost heading {line}"


def test_generated_copies_keep_scripts_executable(tmp_path: Path):
    generate("pi", output_root=tmp_path)
    src = next(s for p in PLUGINS for s in p.skills if s.name == "prp-loop").dir / "scripts/prp_loop.py"
    out = tmp_path / "build/pi/prp-core/skills/prp-loop/scripts/prp_loop.py"
    assert out.read_bytes() == src.read_bytes()
    assert out.stat().st_mode == src.stat().st_mode


def test_codex_marketplace_lists_every_plugin_with_skills(tmp_path: Path):
    generate("codex", output_root=tmp_path)
    marketplace = json.loads((tmp_path / "build/codex/.agents/plugins/marketplace.json").read_text())
    assert marketplace["name"] == "nanoboom"
    assert [p["name"] for p in marketplace["plugins"]] == ["github-project", "prp-core"]
    manifest = json.loads((tmp_path / "build/codex/plugins/prp-core/.codex-plugin/plugin.json").read_text())
    assert manifest["hooks"] == "./hooks/hooks.json" and manifest["skills"] == "./skills/"


def test_pi_agents_get_read_only_tools(tmp_path: Path):
    generate("pi", output_root=tmp_path)
    fm, _ = parse_frontmatter((tmp_path / "build/pi/prp-core/agents/prp-core__seam-analyzer.md").read_text())
    assert fm["name"] == "prp-core__seam-analyzer"
    assert "write" not in fm["tools"] and "edit" not in fm["tools"]
    assert (tmp_path / "build/pi/github-project/skills/github-project-manage/SKILL.md").is_file()


def test_generation_removes_artifacts_of_deleted_sources(tmp_path: Path):
    stale = tmp_path / "build/pi/prp-core/agents/prp-core__removed.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    keep = tmp_path / ".pi/settings.json"
    keep.parent.mkdir()
    keep.write_text("{}")
    generate("pi", output_root=tmp_path)
    assert not stale.exists()
    assert keep.exists()
    assert not (tmp_path / ".pi/agents").exists()
