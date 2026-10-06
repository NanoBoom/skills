from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from helpers import REPO

from tools.install import RECEIPT, install, uninstall


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "app"
    path.mkdir()
    return path


# ── User configuration ───────────────────────────────────────────────────────


def test_codex_install_links_agents(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    report = install("codex", repo_root=generated, env={}, home=home, only="agents")
    assert not report.errors
    agent = home / ".codex/agents/prp-core__code-reviewer.toml"
    assert agent.is_symlink()
    assert agent.resolve() == (generated / "build/codex/agents/prp-core" / agent.name).resolve()

    again = install("codex", repo_root=generated, env={}, home=home, only="agents")
    assert again.linked == 0 and again.unchanged == report.linked


def test_codex_home_is_respected(generated: Path, tmp_path: Path):
    install("codex", repo_root=generated, env={"CODEX_HOME": str(tmp_path / "ch")}, home=tmp_path, only="agents")
    assert (tmp_path / "ch/agents/prp-core__web-researcher.toml").is_symlink()


def test_codex_without_the_cli_says_so(generated: Path, tmp_path: Path, real_codex):
    env = {"PATH": str(tmp_path)}
    report = install("codex", repo_root=generated, env=env, home=tmp_path, only="plugins", run=real_codex)
    assert any("`codex` is not on PATH" in e for e in report.errors)


def test_a_kind_the_harness_lacks_is_an_error(generated: Path, tmp_path: Path, project: Path):
    assert install("codex", repo_root=generated, env={}, home=tmp_path, only="skills").errors
    assert install("pi", repo_root=generated, env={}, home=tmp_path, only="plugins").errors
    assert install("codex", repo_root=generated, env={}, home=tmp_path, project=project, only="plugins").errors


def test_install_refuses_to_replace_a_real_directory(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    existing = home / ".pi/agent/skills/prp-plan"
    existing.mkdir(parents=True)
    report = install("pi", repo_root=generated, env={}, home=home, only="skills")
    assert any("prp-plan" in e and "not installed from this checkout" in e for e in report.errors)
    assert existing.is_dir() and not existing.is_symlink()


def test_foreign_symlink_needs_force(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    link = home / ".pi/agent/agents/prp-core__code-reviewer.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(tmp_path)
    assert install("pi", repo_root=generated, env={}, home=home, only="agents").errors
    assert not install("pi", repo_root=generated, env={}, home=home, only="agents", force=True).errors
    assert link.resolve() == (generated / "build/pi/prp-core/agents" / link.name).resolve()


def test_uninstall_removes_only_this_checkouts_links(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    env = {"PI_CODING_AGENT_DIR": str(home / "pi")}
    install("pi", repo_root=generated, env=env, home=home)
    mine = home / "pi/skills/other"
    mine.symlink_to(tmp_path)
    report = uninstall("pi", repo_root=generated, env=env, home=home)
    assert report.removed > 0
    assert mine.is_symlink()
    assert not (home / "pi/agents/prp-core__code-reviewer.md").exists()


def test_install_skips_kinds_with_nothing_generated(generated: Path, tmp_path: Path):
    """The real repository has no commands and no Pi extensions; installing must not fail."""
    home = tmp_path / "home"
    report = install("pi", repo_root=generated, env={}, home=home)
    assert report.errors == []
    assert not (home / ".pi/agent/prompts").exists()
    assert not (home / ".pi/agent/extensions").exists()


def test_install_without_generation_reports_it(tmp_path: Path):
    report = install("pi", repo_root=tmp_path, env={}, home=tmp_path / "home")
    assert any("make generate" in e for e in report.errors)


def test_install_removes_entries_whose_source_is_gone(fresh_generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    install("pi", repo_root=fresh_generated, env={}, home=home)
    shutil.rmtree(fresh_generated / "build/pi/prp-core/skills/prp-bro")
    report = install("pi", repo_root=fresh_generated, env={}, home=home)
    assert report.errors == [] and report.removed == 1
    assert not (home / ".pi/agent/skills/prp-bro").is_symlink()


# ── Some plugins ─────────────────────────────────────────────────────────────


def test_install_takes_only_the_named_plugins(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    report = install("pi", repo_root=generated, env={}, home=home, plugins=["github-project"])
    assert report.errors == []
    skills = sorted(p.name for p in (home / ".pi/agent/skills").iterdir())
    assert skills == ["github-project-audit", "github-project-manage", "github-project-setup"]
    assert not (home / ".pi/agent/agents").exists()


def test_unknown_plugin_is_an_error(generated: Path, tmp_path: Path):
    report = install("pi", repo_root=generated, env={}, home=tmp_path, plugins=["prp-cor"])
    assert any("unknown plugin(s) prp-cor; choose from prp-core, github-project" in e for e in report.errors)
    assert uninstall("pi", repo_root=generated, env={}, home=tmp_path, plugins=["prp-cor"]).errors


def test_uninstall_takes_only_the_named_plugins(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    install("pi", repo_root=generated, env={}, home=home)
    uninstall("pi", repo_root=generated, env={}, home=home, plugins=["github-project"])
    assert not (home / ".pi/agent/skills/github-project-manage").exists()
    assert (home / ".pi/agent/skills/prp-plan").is_symlink()
    assert (home / ".pi/agent/agents/prp-core__code-reviewer.md").is_symlink()


def test_codex_adds_only_the_named_plugins(generated: Path, tmp_path: Path, fake_codex):
    codex = fake_codex()
    report = install("codex", repo_root=generated, env={}, home=tmp_path, plugins=["github-project"], run=codex)
    assert report.errors == [] and report.plugins == 1
    added = [c[-1] for c in codex.calls if c[:2] == ["plugin", "add"]]
    assert added == ["github-project@nanoboom"]
    assert not (tmp_path / ".codex/agents").exists()


def test_codex_keeps_the_marketplace_while_other_plugins_use_it(generated: Path, tmp_path: Path, fake_codex):
    build = str((generated / "build/codex").resolve())
    codex = fake_codex(
        installed=[
            {"pluginId": "prp-core@nanoboom", "marketplaceSource": {"source": build}},
            {"pluginId": "github-project@nanoboom", "marketplaceSource": {"source": build}},
        ],
        marketplaces=[{"name": "nanoboom", "root": build}],
    )
    uninstall("codex", repo_root=generated, env={}, home=tmp_path, plugins=["github-project"], run=codex)
    assert codex.removed() == ["github-project@nanoboom"]
    uninstall("codex", repo_root=generated, env={}, home=tmp_path, run=codex)
    assert codex.removed() == ["github-project@nanoboom", "prp-core@nanoboom", "nanoboom"]


# ── Project ──────────────────────────────────────────────────────────────────


def test_pi_project_install(generated: Path, tmp_path: Path, project: Path):
    report = install("pi", repo_root=generated, env={}, home=tmp_path / "home", project=project)
    assert report.errors == []
    assert (project / ".pi/skills/prp-plan/SKILL.md").is_file()
    assert (project / ".pi/agents/prp-core__code-reviewer.md").is_symlink()
    assert not (tmp_path / "home").exists()
    assert any("trust the project" in n for n in report.notes)
    uninstall("pi", repo_root=generated, env={}, home=tmp_path / "home", project=project)
    assert not (project / ".pi/skills").exists() and not (project / ".pi/agents").exists()


def test_codex_project_install_links_skills_and_agents_without_the_cli(generated: Path, tmp_path: Path, project: Path):
    report = install("codex", repo_root=generated, env={}, home=tmp_path, project=project)
    assert report.errors == []
    skill = project / ".codex/skills/prp-plan"
    assert skill.is_symlink()
    assert skill.resolve() == (generated / "build/codex/plugins/prp-core/skills/prp-plan").resolve()
    assert (project / ".codex/agents/prp-core__code-reviewer.toml").is_symlink()
    assert uninstall("codex", repo_root=generated, env={}, home=tmp_path, project=project).removed


def test_codex_project_reports_hooks_it_cannot_install(kitchen_repo: Path, tmp_path: Path, project: Path):
    report = install("codex", repo_root=kitchen_repo, env={}, home=tmp_path, project=project)
    assert report.errors == []
    assert (project / ".codex/skills/kitchen-run/SKILL.md").is_file()
    assert any("kitchen-sink: Codex hooks and MCP servers come only with its plugin" in n for n in report.notes)


def test_project_must_exist_and_be_outside_the_checkout(generated: Path, tmp_path: Path):
    missing = install("pi", repo_root=generated, env={}, home=tmp_path, project=tmp_path / "nope")
    assert any("does not exist" in e for e in missing.errors)
    inside = install("pi", repo_root=generated, env={}, home=tmp_path, project=generated / "build")
    assert any("inside this checkout" in e for e in inside.errors)


# ── Copies ───────────────────────────────────────────────────────────────────


def test_copy_installs_real_files_and_records_them(generated: Path, tmp_path: Path, project: Path):
    report = install("pi", repo_root=generated, env={}, home=tmp_path, project=project, copy=True)
    assert report.errors == [] and report.copied > 0 and report.linked == 0
    skill = project / ".pi/skills/prp-loop"
    assert skill.is_dir() and not skill.is_symlink()
    source = generated / "build/pi/prp-core/skills/prp-loop/scripts/prp_loop.py"
    script = skill / "scripts/prp_loop.py"
    assert script.read_bytes() == source.read_bytes() and script.stat().st_mode == source.stat().st_mode
    receipt = json.loads((project / ".pi" / RECEIPT).read_text())
    assert {"path": "skills/prp-loop", "plugin": "prp-core", "kind": "skills"} in receipt["entries"]

    again = install("pi", repo_root=generated, env={}, home=tmp_path, project=project, copy=True)
    assert again.errors == [] and again.copied == report.copied


def test_switching_between_copy_and_symlink(generated: Path, tmp_path: Path, project: Path):
    install("pi", repo_root=generated, env={}, home=tmp_path, project=project, copy=True)
    linked = install("pi", repo_root=generated, env={}, home=tmp_path, project=project)
    assert linked.errors == []
    assert (project / ".pi/skills/prp-plan").is_symlink()
    assert not (project / ".pi" / RECEIPT).exists()
    copied = install("pi", repo_root=generated, env={}, home=tmp_path, project=project, copy=True)
    assert copied.errors == [] and not (project / ".pi/skills/prp-plan").is_symlink()


def test_uninstall_removes_recorded_copies_only(generated: Path, tmp_path: Path, project: Path):
    install("pi", repo_root=generated, env={}, home=tmp_path, project=project, copy=True)
    theirs = project / ".pi/skills/their-skill"
    theirs.mkdir()
    uninstall("pi", repo_root=generated, env={}, home=tmp_path, project=project, plugins=["github-project"])
    assert not (project / ".pi/skills/github-project-manage").exists()
    assert (project / ".pi/skills/prp-plan").is_dir()
    uninstall("pi", repo_root=generated, env={}, home=tmp_path, project=project)
    assert sorted(p.name for p in (project / ".pi/skills").iterdir()) == ["their-skill"]
    assert not (project / ".pi" / RECEIPT).exists()


def test_copy_prunes_a_copy_whose_source_is_gone(fresh_generated: Path, tmp_path: Path, project: Path):
    install("pi", repo_root=fresh_generated, env={}, home=tmp_path, project=project, copy=True)
    shutil.rmtree(fresh_generated / "build/pi/prp-core/skills/prp-bro")
    report = install("pi", repo_root=fresh_generated, env={}, home=tmp_path, project=project, copy=True)
    assert report.errors == [] and report.removed == 1
    assert not (project / ".pi/skills/prp-bro").exists()
    receipt = json.loads((project / ".pi" / RECEIPT).read_text())
    assert "skills/prp-bro" not in {e["path"] for e in receipt["entries"]}


# ── Failure paths ────────────────────────────────────────────────────────────


def test_force_never_replaces_a_real_directory(generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    existing = home / ".pi/agent/skills/prp-plan"
    existing.mkdir(parents=True)
    (existing / "mine.md").write_text("mine")
    for copy in (False, True):
        report = install("pi", repo_root=generated, env={}, home=home, only="skills", force=True, copy=copy)
        assert any("prp-plan" in e for e in report.errors)
        assert (existing / "mine.md").read_text() == "mine" and not existing.is_symlink()


def test_a_failed_copy_keeps_the_record_of_what_it_copied(generated: Path, tmp_path: Path, project: Path):
    """Skills install before agents; an agents path that is a file makes the run fail midway."""
    (project / ".pi").mkdir()
    (project / ".pi/agents").write_text("in the way")
    with pytest.raises(OSError):
        install("pi", repo_root=generated, env={}, home=tmp_path, project=project, copy=True)
    receipt = json.loads((project / ".pi" / RECEIPT).read_text())
    assert "skills/prp-plan" in {e["path"] for e in receipt["entries"]}

    (project / ".pi/agents").unlink()
    report = uninstall("pi", repo_root=generated, env={}, home=tmp_path, project=project)
    assert report.errors == []
    assert not (project / ".pi/skills").exists()


def test_uninstall_checks_the_project_too(generated: Path, tmp_path: Path):
    report = uninstall("pi", repo_root=generated, env={}, home=tmp_path, project=tmp_path / "typo")
    assert any("does not exist" in e for e in report.errors)


def test_install_removes_a_plugin_dropped_from_the_marketplace(fresh_generated: Path, tmp_path: Path, project: Path):
    home = tmp_path / "home"
    install("pi", repo_root=fresh_generated, env={}, home=home)
    install("pi", repo_root=fresh_generated, env={}, home=tmp_path, project=project, copy=True)
    marketplace = fresh_generated / ".claude-plugin/marketplace.json"
    data = json.loads(marketplace.read_text())
    data["plugins"] = [p for p in data["plugins"] if p["name"] != "github-project"]
    marketplace.write_text(json.dumps(data))
    shutil.rmtree(fresh_generated / "build/pi/github-project")

    linked = install("pi", repo_root=fresh_generated, env={}, home=home)
    copied = install("pi", repo_root=fresh_generated, env={}, home=tmp_path, project=project, copy=True)
    assert linked.errors == [] and copied.errors == []
    assert linked.removed == 3 and copied.removed == 3
    assert not (home / ".pi/agent/skills/github-project-manage").is_symlink()
    assert not (project / ".pi/skills/github-project-manage").exists()


def test_uninstall_after_build_is_gone(fresh_generated: Path, tmp_path: Path):
    home = tmp_path / "home"
    install("pi", repo_root=fresh_generated, env={}, home=home)
    shutil.rmtree(fresh_generated / "build")
    assert uninstall("pi", repo_root=fresh_generated, env={}, home=home, plugins=["github-project"]).removed == 3
    assert uninstall("pi", repo_root=fresh_generated, env={}, home=home).removed > 0
    assert not [p for p in (home / ".pi/agent").rglob("*") if p.is_symlink()]


def test_codex_subset_install_keeps_the_other_plugins(generated: Path, tmp_path: Path, fake_codex):
    build = str((generated / "build/codex").resolve())
    codex = fake_codex(installed=[{"pluginId": "prp-core@nanoboom", "marketplaceSource": {"source": build}}])
    report = install("codex", repo_root=generated, env={}, home=tmp_path, plugins=["github-project"], run=codex)
    assert report.errors == [] and report.removed == 0
    assert codex.removed() == []


def test_an_entry_without_a_marketplace_source_is_not_ours(generated: Path, tmp_path: Path, fake_codex, monkeypatch):
    """An empty source must not match: Path("") is the current directory."""
    monkeypatch.chdir(generated / "build/codex")
    codex = fake_codex(installed=[{"pluginId": "theirs@other"}], marketplaces=[{"name": "other"}])
    uninstall("codex", repo_root=generated, env={}, home=tmp_path, run=codex)
    assert codex.removed() == []


# ── Command line and make ────────────────────────────────────────────────────


def test_main_forwards_every_option(monkeypatch, project: Path):
    import sys

    import tools.install as cli

    seen = {}

    def record(name):
        def fake(harness, **kwargs):
            seen[name] = (harness, kwargs)
            return cli.Report(errors=["boom"] if name == "uninstall" else [])

        return fake

    monkeypatch.setattr(cli, "install", record("install"))
    monkeypatch.setattr(cli, "uninstall", record("uninstall"))
    argv = ["install.py", "install", "pi", "--plugin", "a,b", "--plugin", "c", "--project", str(project)]
    monkeypatch.setattr(sys, "argv", [*argv, "--only", "skills", "--copy", "--force"])
    assert cli.main() == 0
    assert seen["install"] == (
        "pi",
        {"plugins": ["a", "b", "c"], "project": project.resolve(), "only": "skills", "copy": True, "force": True},
    )
    monkeypatch.setattr(sys, "argv", ["install.py", "uninstall", "codex", "--plugin", "a", "--project", str(project)])
    assert cli.main() == 1
    assert seen["uninstall"] == ("codex", {"plugins": ["a"], "project": project.resolve()})


@pytest.mark.skipif(shutil.which("make") is None, reason="needs make")
@pytest.mark.parametrize(
    ("target", "variables", "expected"),
    [
        (
            "install-codex",
            ["PLUGINS=a,b", "PROJECT=/p", "ONLY=agents", "COPY=1", "FORCE=1"],
            "install.py install codex --plugin a --plugin b --project /p --only agents --copy --force",
        ),
        ("install-pi", ["COPY=0", "FORCE=no"], "install.py install pi"),
        ("uninstall-pi", ["PLUGINS=a,b", "PROJECT=/p"], "install.py uninstall pi --plugin a --plugin b --project /p"),
        ("validate", ["STRICT=1"], "validate.py --strict"),
        ("validate", ["STRICT=0"], "validate.py"),
    ],
)
def test_make_passes_variables_through(target: str, variables: list[str], expected: str):
    out = subprocess.run(
        ["make", "-n", "-C", str(REPO), target, *variables], capture_output=True, text=True, check=True
    )
    lines = [
        " ".join(line.split()) for line in out.stdout.splitlines() if "install.py" in line or "validate.py" in line
    ]
    assert lines[-1].endswith(expected), lines
