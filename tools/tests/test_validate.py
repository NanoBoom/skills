from __future__ import annotations

import json
from pathlib import Path

from helpers import REPO, errors


def test_repository_passes():
    assert errors(REPO) == []


def test_copy_passes(repo_copy: Path):
    assert errors(repo_copy) == []


def test_version_drift_fails(repo_copy: Path):
    path = repo_copy / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text())
    data["plugins"][0]["version"] = "9.9.9"
    path.write_text(json.dumps(data))
    assert any("version drift" in e for e in errors(repo_copy))


def test_skill_name_must_match_directory(repo_copy: Path):
    skill = repo_copy / "plugins/prp-core/skills/prp-bro/SKILL.md"
    skill.write_text(skill.read_text().replace("name: prp-bro", "name: prp-brother", 1))
    assert any("directory is `prp-bro`" in e for e in errors(repo_copy))


def test_dispatch_to_a_missing_agent_fails(repo_copy: Path):
    skill = repo_copy / "plugins/prp-core/skills/prp-bro/SKILL.md"
    skill.write_text(skill.read_text() + "\nUse `prp-core:ghost-agent`.\n")
    assert any("prp-core:ghost-agent" in e for e in errors(repo_copy))


def test_self_contained_plugin_cannot_dispatch_elsewhere(repo_copy: Path):
    skill = repo_copy / "plugins/github-project/skills/github-project-audit/SKILL.md"
    skill.write_text(skill.read_text() + "\nUse `prp-core:code-reviewer`.\n")
    assert any("self-contained" in e for e in errors(repo_copy))


def test_plugin_root_path_in_a_skill_fails(repo_copy: Path):
    skill = repo_copy / "plugins/prp-core/skills/prp-bro/SKILL.md"
    skill.write_text(skill.read_text() + "\nRun ${CLAUDE_PLUGIN_ROOT}/x.\n")
    assert any("CLAUDE_PLUGIN_ROOT" in e for e in errors(repo_copy))


def test_self_contained_plugin_cannot_carry_a_harness_dir(repo_copy: Path):
    (repo_copy / "plugins/github-project/harness/pi/extensions").mkdir(parents=True)
    assert any("no harness/" in e for e in errors(repo_copy))


def test_unpromoted_skill_fails(repo_copy: Path):
    new = repo_copy / "plugins/prp-core/skills/prp-new"
    new.mkdir()
    (new / "SKILL.md").write_text("---\nname: prp-new\ndescription: New. Use when testing.\n---\n\n# New\n")
    found = errors(repo_copy)
    assert any("prp-new: not linked" in e for e in found)
    assert any("prp-new: not in any grouping" in e for e in found)


def test_top_readme_row_must_name_the_skill_exactly(repo_copy: Path):
    readme = repo_copy / "README.md"
    lines = [ln for ln in readme.read_text().splitlines() if not ln.startswith("| `/prp-core:prp-prd` |")]
    readme.write_text("\n".join(lines) + "\n")
    found = errors(repo_copy)
    assert any("skills/prp-prd: not listed in the top-level README.md" in e for e in found)
    assert not any("prp-prd-update: not listed" in e for e in found)
