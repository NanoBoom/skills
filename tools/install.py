#!/usr/bin/env python3
"""Install generated harness artifacts into the user's or a project's configuration.

    uv run tools/install.py install codex|pi [--plugin NAME ...] [--project [PATH]]
                                             [--only KIND] [--copy] [--force]
    uv run tools/install.py uninstall codex|pi [--plugin NAME ...] [--project [PATH]]

Run `tools/generate.py` first; `make install-<harness>` does both. Each adapter
says what it installs and where (`install_kinds`, `user_env`, `project_dir`).
Entries are symlinks into this checkout's `build/`, or copies with --copy, which
`.nanoboom-install.json` at the configuration root records. At user level, Codex
plugins go through the Codex CLI. docs/harnesses.md#install-options describes
every option and what install and uninstall may replace.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.adapters import ADAPTERS
from tools.adapters.base import REPO_ROOT, HarnessAdapter, InstallKind, read_marketplace
from tools.adapters.codex import CodexAdapter

RECEIPT = ".nanoboom-install.json"

# Runs `codex <args>` with the given environment. Tests substitute a fake.
CodexRunner = Callable[[list[str], Mapping[str, str]], subprocess.CompletedProcess]


# `plugins` is not a kind of file: it is the Codex CLI step at user level.
ALL_KINDS = sorted(
    {k.name for a in ADAPTERS.values() for project in (False, True) for k in a.install_kinds(project)} | {"plugins"}
)


def kind_names(adapter: type[HarnessAdapter], project: bool) -> list[str]:
    names = [k.name for k in adapter.install_kinds(project)]
    return [*names, "plugins"] if adapter.cli_plugins and not project else names


def config_root(adapter: type[HarnessAdapter], env: Mapping[str, str], home: Path, project: Path | None) -> Path:
    if project is not None:
        return project / adapter.project_dir
    if env.get(adapter.user_env):
        return Path(env[adapter.user_env]).expanduser()
    return home / adapter.user_default


def available_plugins(repo_root: Path) -> list[str]:
    return [p["name"] for p in read_marketplace(repo_root).get("plugins", [])]


@dataclass
class Report:
    linked: int = 0
    copied: int = 0
    unchanged: int = 0
    removed: int = 0
    plugins: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _points_into(link: Path, root: Path) -> bool:
    return link.resolve(strict=False).is_relative_to(root.resolve(strict=False))


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


# ── Receipt of copies ────────────────────────────────────────────────────────


class Receipt:
    """`.nanoboom-install.json`: the copies --copy made under one configuration root."""

    def __init__(self, root: Path) -> None:
        self.path = root / RECEIPT
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        self.entries: dict[str, dict] = {e["path"]: e for e in data.get("entries", [])}

    def owns(self, rel: str) -> bool:
        return rel in self.entries

    def add(self, rel: str, plugin: str, kind: str) -> None:
        self.entries[rel] = {"path": rel, "plugin": plugin, "kind": kind}

    def discard(self, rel: str) -> None:
        self.entries.pop(rel, None)

    def save(self) -> None:
        if self.entries:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            entries = [self.entries[k] for k in sorted(self.entries)]
            self.path.write_text(json.dumps({"entries": entries}, indent=2) + "\n", encoding="utf-8")
        elif self.path.is_file():
            self.path.unlink()


# ── Codex CLI ────────────────────────────────────────────────────────────────


class CodexError(Exception):
    pass


def run_codex(args: list[str], env: Mapping[str, str]) -> subprocess.CompletedProcess:
    exe = shutil.which("codex", path=env.get("PATH"))
    if exe is None:
        raise CodexError("`codex` is not on PATH; install the Codex CLI, or rerun with ONLY=agents")
    return subprocess.run([exe, *args], env=dict(env), capture_output=True, text=True, check=False)


def _codex(run: CodexRunner, args: list[str], env: Mapping[str, str]) -> str:
    """Run a Codex CLI command and return its stdout, raising CodexError on failure."""
    proc = run(args, env)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise CodexError(f"`codex {' '.join(args)}` failed: {detail[-1] if detail else proc.returncode}")
    return proc.stdout


def _same_path(a: str, b: Path) -> bool:
    """True when `a` names `b`. An empty `a`, from a missing JSON field, names nothing."""
    return bool(a) and Path(a).resolve(strict=False) == b.resolve(strict=False)


def _installed_from(build: Path, run: CodexRunner, env: Mapping[str, str]) -> list[str]:
    """IDs of installed Codex plugins whose marketplace is this checkout's build/codex/."""
    listing = json.loads(_codex(run, ["plugin", "list", "--json"], env))
    return [
        p["pluginId"]
        for p in listing.get("installed", [])
        if _same_path((p.get("marketplaceSource") or {}).get("source", ""), build)
    ]


def _codex_manifest(repo_root: Path, plugin: str) -> dict:
    path = repo_root / CodexAdapter.plugin_root(plugin) / ".codex-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def install_codex_plugins(
    repo_root: Path, selected: list[str], env: Mapping[str, str], run: CodexRunner, report: Report
) -> None:
    build = repo_root / CodexAdapter.build()
    marketplace = json.loads((repo_root / CodexAdapter.marketplace_path()).read_text(encoding="utf-8"))
    name = marketplace["name"]
    built = [p["name"] for p in marketplace.get("plugins", [])]
    try:
        _codex(run, ["plugin", "marketplace", "add", str(build.resolve())], env)
    except CodexError as e:
        hint = ""
        if "different source" in str(e):
            hint = f"; another `{name}` marketplace is registered: `codex plugin marketplace remove {name}` first"
        report.errors.append(f"{e}{hint}")
        return
    for plugin in (p for p in selected if p in built):
        try:
            _codex(run, ["plugin", "add", f"{plugin}@{name}"], env)
            report.plugins += 1
        except CodexError as e:
            report.errors.append(str(e))
    try:
        for plugin_id in _installed_from(build, run, env):
            if plugin_id.split("@", 1)[0] not in built:
                _codex(run, ["plugin", "remove", plugin_id], env)
                report.removed += 1
    except CodexError as e:
        report.errors.append(str(e))
    if report.plugins and any("hooks" in _codex_manifest(repo_root, p) for p in selected):
        report.notes.append("Codex asks you to review new or changed plugin hooks the next time it starts")


def uninstall_codex_plugins(
    repo_root: Path, selected: list[str] | None, env: Mapping[str, str], run: CodexRunner, report: Report
) -> None:
    build = repo_root / CodexAdapter.build()
    try:
        remaining = []
        for plugin_id in _installed_from(build, run, env):
            if selected is None or plugin_id.split("@", 1)[0] in selected:
                _codex(run, ["plugin", "remove", plugin_id], env)
                report.removed += 1
            else:
                remaining.append(plugin_id)
        if remaining:
            return  # other plugins from this marketplace stay installed
        listing = json.loads(_codex(run, ["plugin", "marketplace", "list", "--json"], env))
        for marketplace in listing.get("marketplaces", []):
            if _same_path(marketplace.get("root", ""), build):
                _codex(run, ["plugin", "marketplace", "remove", marketplace["name"]], env)
    except CodexError as e:
        report.errors.append(str(e))


# ── Install and uninstall ────────────────────────────────────────────────────


@dataclass
class _Placer:
    """Installs entries under one configuration root and records what it copied."""

    root: Path
    build: Path  # this checkout's build/<harness>/
    receipt: Receipt
    report: Report
    copy: bool = False
    force: bool = False

    def place(self, src: Path, rel: str, plugin: str, kind: InstallKind) -> None:
        """Install one entry as a symlink or a copy, replacing only what this checkout put there."""
        dst = self.root / rel
        if dst.is_symlink():
            if not self.copy and dst.resolve(strict=False) == src.resolve():
                self.receipt.discard(rel)
                self.report.unchanged += 1
                return
            if not (_points_into(dst, self.build) or self.receipt.owns(rel) or self.force):
                self.report.errors.append(f"{dst} is a symlink to {os.readlink(dst)}; rerun with FORCE=1 to replace it")
                return
            dst.unlink()
        elif dst.exists():
            if not self.receipt.owns(rel):
                hint = f" (a copy from `npx skills`: npx skills remove {src.name})" if kind.name == "skills" else ""
                self.report.errors.append(f"{dst} exists and was not installed from this checkout; remove it{hint}")
                return
            _remove(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if self.copy:
            if src.is_dir():
                shutil.copytree(src, dst, symlinks=False)
            else:
                shutil.copy2(src, dst)
            self.receipt.add(rel, plugin, kind.name)
            self.report.copied += 1
        else:
            dst.symlink_to(src.resolve(), target_is_directory=src.is_dir())
            self.receipt.discard(rel)
            self.report.linked += 1

    def prune(self, kind: InstallKind, sources: dict[str, Path]) -> None:
        """Remove this kind's entries whose source is no longer generated.

        `sources` maps every plugin in the marketplace to its source directory for
        this kind. Dangling symlinks into build/ go, and so do recorded copies of a
        file that is gone or of a plugin no longer in the marketplace.
        """
        dest = self.root / kind.dest
        for dst in sorted(dest.iterdir()) if dest.is_dir() else []:
            if dst.is_symlink() and not dst.exists() and _points_into(dst, self.build):
                dst.unlink()
                self.report.removed += 1
        for rel, entry in list(self.receipt.entries.items()):
            if entry["kind"] != kind.name:
                continue
            source_dir = sources.get(entry["plugin"])
            if source_dir is None or not (source_dir / Path(rel).name).exists():
                if (self.root / rel).exists():
                    _remove(self.root / rel)
                self.receipt.discard(rel)
                self.report.removed += 1


def _resolve_selection(available: list[str], plugins: list[str] | None, report: Report) -> list[str] | None:
    """The plugins to act on: all of `available` when none are named, else the named ones."""
    if not plugins:
        return available
    unknown = [p for p in plugins if p not in available]
    if unknown:
        report.errors.append(f"unknown plugin(s) {', '.join(unknown)}; choose from {', '.join(available)}")
        return None
    return list(dict.fromkeys(plugins))


def _check_project(repo_root: Path, project: Path | None, report: Report) -> bool:
    if project is None:
        return True
    if not project.is_dir():
        report.errors.append(f"project directory {project} does not exist")
        return False
    if project.resolve().is_relative_to(repo_root.resolve()):
        report.errors.append(f"{project} is inside this checkout; install into another project")
        return False
    return True


def install(
    harness: str,
    *,
    repo_root: Path = REPO_ROOT,
    env: Mapping[str, str] = os.environ,
    home: Path | None = None,
    plugins: list[str] | None = None,
    project: Path | None = None,
    only: str | None = None,
    copy: bool = False,
    force: bool = False,
    run: CodexRunner | None = None,
) -> Report:
    """`run` defaults to the real Codex CLI, looked up at call time so tests can replace it."""
    run = run or run_codex
    adapter = ADAPTERS[harness]
    report = Report()
    in_project = project is not None
    if only and only not in kind_names(adapter, in_project):
        scope = "a project" if in_project else "the user configuration"
        report.errors.append(
            f"{harness} has no `{only}` for {scope}; choose from {', '.join(kind_names(adapter, in_project))}"
        )
        return report
    available = available_plugins(repo_root)
    selected = _resolve_selection(available, plugins, report)
    if selected is None or not _check_project(repo_root, project, report):
        return report
    build = repo_root / adapter.build()
    if not build.is_dir():
        report.errors.append(f"nothing generated in {adapter.build()}; run `make generate HARNESS={harness}` first")
        return report

    root = config_root(adapter, env, home or Path.home(), project)
    placer = _Placer(root, build, Receipt(root), report, copy=copy, force=force)
    try:
        for kind in adapter.install_kinds(in_project):
            if only and kind.name != only:
                continue
            placer.prune(kind, {p: repo_root / kind.source.format(plugin=p) for p in available})
            for plugin in selected:
                source_dir = repo_root / kind.source.format(plugin=plugin)
                for src in sorted(source_dir.glob(kind.pattern)) if source_dir.is_dir() else []:
                    placer.place(src, f"{kind.dest}/{src.name}", plugin, kind)
    finally:
        # Even when a copy fails midway, record the copies already made, or a
        # later install or uninstall could not tell them from the user's files.
        placer.receipt.save()

    if adapter.cli_plugins and not in_project and only in (None, "plugins"):
        install_codex_plugins(repo_root, selected, env, run, report)
    if adapter.cli_plugins and in_project:
        native = [p for p in selected if {"hooks", "mcpServers"} & set(_codex_manifest(repo_root, p))]
        if native:
            report.notes.append(
                f"{', '.join(native)}: {adapter.display_name} hooks and MCP servers come only with its "
                "plugin, which is not installed into a project; install without PROJECT to get them"
            )
    if in_project:
        report.notes.append(
            f"{adapter.display_name} loads <project>/{adapter.project_dir}/ only after you trust the project"
        )
    return report


def uninstall(
    harness: str,
    *,
    repo_root: Path = REPO_ROOT,
    env: Mapping[str, str] = os.environ,
    home: Path | None = None,
    plugins: list[str] | None = None,
    project: Path | None = None,
    run: CodexRunner | None = None,
) -> Report:
    run = run or run_codex
    adapter = ADAPTERS[harness]
    report = Report()
    in_project = project is not None
    selected = _resolve_selection(available_plugins(repo_root), plugins, report) if plugins else None
    if report.errors or not _check_project(repo_root, project, report):
        return report
    root = config_root(adapter, env, home or Path.home(), project)
    kinds = adapter.install_kinds(in_project)
    for kind in kinds:
        dest = root / kind.dest
        if selected is None:
            sources = [repo_root / adapter.build()]
        else:
            sources = [repo_root / kind.source.format(plugin=p) for p in selected]
        for dst in sorted(dest.iterdir()) if dest.is_dir() else []:
            if dst.is_symlink() and any(_points_into(dst, s) for s in sources):
                dst.unlink()
                report.removed += 1
    receipt = Receipt(root)
    try:
        for rel, entry in list(receipt.entries.items()):
            if selected is None or entry["plugin"] in selected:
                if (root / rel).exists() or (root / rel).is_symlink():
                    _remove(root / rel)
                    report.removed += 1
                receipt.discard(rel)
    finally:
        receipt.save()
    for kind in kinds:
        dest = root / kind.dest
        if dest.is_dir() and not any(dest.iterdir()):
            dest.rmdir()
    if adapter.cli_plugins and not in_project:
        uninstall_codex_plugins(repo_root, selected, env, run, report)
    return report


def _plugin_names(values: list[str] | None) -> list[str] | None:
    names = [n.strip() for v in values or [] for n in v.split(",") if n.strip()]
    return names or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("harness", choices=list(ADAPTERS))
    parser.add_argument("--plugin", action="append", help="plugin to take, repeated or comma-separated; default all")
    parser.add_argument("--project", nargs="?", const=".", type=Path, help="install into a project (default: .)")
    parser.add_argument("--only", choices=ALL_KINDS, help="one kind of artifact")
    parser.add_argument("--copy", action="store_true", help="copy files instead of symlinking them")
    parser.add_argument("--force", action="store_true", help="replace symlinks into another checkout")
    args = parser.parse_args()

    plugins = _plugin_names(args.plugin)
    project = args.project.expanduser().resolve() if args.project else None
    if args.action == "install":
        report = install(
            args.harness, plugins=plugins, project=project, only=args.only, copy=args.copy, force=args.force
        )
    else:
        report = uninstall(args.harness, plugins=plugins, project=project)
    where = f" into {project}" if project and args.action == "install" else f" from {project}" if project else ""
    if args.action == "install":
        summary = f"linked={report.linked} copied={report.copied} unchanged={report.unchanged} removed={report.removed}"
        if ADAPTERS[args.harness].cli_plugins and not project:
            summary += f" plugins={report.plugins}"
    else:
        summary = f"removed={report.removed}"
    print(f"{args.action} {args.harness}{where}: {summary} errors={len(report.errors)}")
    for e in report.errors:
        print(f"error {e}")
    for note in report.notes:
        print(f"note  {note}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
