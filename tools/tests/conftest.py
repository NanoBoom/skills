from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import FIXTURE, REPO, FakeCodex, generate_all  # noqa: E402

import tools.install  # noqa: E402

_REAL_RUN_CODEX = tools.install.run_codex


@pytest.fixture(autouse=True)
def _no_real_codex(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Keep every test away from the developer's real Codex and Pi configuration.

    A test that does not pass `run=` would otherwise run the real Codex CLI against
    ~/.codex. Calling it now fails the test; `real_codex` opts back in.
    """

    def refuse(args, env):
        raise AssertionError(f"a test ran the real Codex CLI: codex {' '.join(args)}; pass run= or use real_codex")

    monkeypatch.setattr(tools.install, "run_codex", refuse)
    sandbox = tmp_path_factory.mktemp("sandbox-home")
    monkeypatch.setenv("CODEX_HOME", str(sandbox / ".codex"))
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(sandbox / ".pi/agent"))


@pytest.fixture
def real_codex():
    """The real Codex CLI runner. Only for tests that also set a throwaway CODEX_HOME."""
    return _REAL_RUN_CODEX


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    """A copy of the parts of the repository that validate.py reads."""
    root = tmp_path / "repo"
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(REPO / "plugins", root / "plugins", ignore=ignore)
    shutil.copytree(REPO / ".claude-plugin", root / ".claude-plugin")
    for rel in ("README.md", "skills.sh.json"):
        shutil.copy2(REPO / rel, root / rel)
    return root


@pytest.fixture
def kitchen_repo(tmp_path: Path) -> Path:
    """A one-plugin repository around the kitchen-sink fixture, with every harness generated."""
    root = tmp_path / "kitchen-repo"
    shutil.copytree(FIXTURE, root / "plugins" / "kitchen-sink")
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "kitchen",
                "owner": {"name": "NanoBoom"},
                "plugins": [{"name": "kitchen-sink", "source": "./plugins/kitchen-sink", "version": "0.1.0"}],
            }
        )
    )
    (root / "README.md").write_text(
        "# Kitchen\n\n| `/kitchen-sink:kitchen-skill` |\n| `/kitchen-sink:kitchen-long` |\n"
    )
    (root / "skills.sh.json").write_text(
        json.dumps({"groupings": [{"title": "Kitchen", "skills": ["kitchen-skill", "kitchen-long"]}]})
    )
    generate_all(root, repo_root=root)
    return root


@pytest.fixture
def fake_codex() -> type[FakeCodex]:
    return FakeCodex


def _checkout(root: Path) -> Path:
    """The real plugins' marketplace with every harness generated: what install reads."""
    shutil.copytree(REPO / ".claude-plugin", root / ".claude-plugin")
    generate_all(root)
    return root


@pytest.fixture(scope="session")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One generated checkout shared by every test that only installs from it."""
    return _checkout(tmp_path_factory.mktemp("checkout"))


@pytest.fixture
def fresh_generated(tmp_path: Path) -> Path:
    """A generated checkout of this test's own, for tests that change build/ or the marketplace."""
    return _checkout(tmp_path / "checkout")
