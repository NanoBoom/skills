"""Shared test helpers. pytest puts this directory on sys.path, so tests import it directly."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.adapters import generated_harnesses
from tools.generate import generate
from tools.validate import validate

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "kitchen-sink"


def errors(root: Path) -> list[str]:
    return validate(root).errors


def generate_all(output_root: Path, repo_root: Path = REPO) -> None:
    for harness in generated_harnesses():
        generate(harness, output_root=output_root, repo_root=repo_root)


class FakeCodex:
    """Records Codex CLI calls and plays back what `codex plugin` would print.

    `plugin remove <id>` drops the plugin from `installed`, as Codex does.
    """

    def __init__(self, installed: list[dict] | None = None, marketplaces: list[dict] | None = None):
        self.calls: list[list[str]] = []
        self.installed = list(installed or [])
        self.marketplaces = list(marketplaces or [])

    def __call__(self, args: list[str], env) -> subprocess.CompletedProcess:
        self.calls.append(args)
        out = ""
        if args == ["plugin", "list", "--json"]:
            out = json.dumps({"installed": self.installed, "available": []})
        elif args == ["plugin", "marketplace", "list", "--json"]:
            out = json.dumps({"marketplaces": self.marketplaces})
        elif args[:2] == ["plugin", "remove"]:
            self.installed = [p for p in self.installed if p["pluginId"] != args[2]]
        return subprocess.CompletedProcess(args, 0, out, "")

    def removed(self) -> list[str]:
        return [c[-1] for c in self.calls if "remove" in c]
