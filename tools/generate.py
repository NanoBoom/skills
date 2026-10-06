#!/usr/bin/env python3
"""Generate harness artifacts from plugins/.

    uv run tools/generate.py                     # every harness
    uv run tools/generate.py --harness codex     # one harness
    uv run tools/generate.py --clean             # remove generated trees only

Each run wipes the harness's generated tree under build/ first, so a renamed or
deleted source leaves nothing behind, then writes it again.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.adapters import ADAPTERS, generated_harnesses, get_adapter
from tools.adapters.base import REPO_ROOT, EmitResult, load_plugins


def clean(harness_id: str, output_root: Path) -> None:
    shutil.rmtree(output_root / ADAPTERS[harness_id].build(), ignore_errors=True)


def generate(harness_id: str, output_root: Path = REPO_ROOT, repo_root: Path = REPO_ROOT) -> EmitResult:
    clean(harness_id, output_root)
    adapter = get_adapter(harness_id, output_root=output_root, repo_root=repo_root)
    return adapter.emit(load_plugins(repo_root))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness", choices=[*generated_harnesses(), "all"], default="all")
    parser.add_argument("--clean", action="store_true", help="remove generated trees and stop")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any warning")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    harnesses = generated_harnesses() if args.harness == "all" else [args.harness]

    if args.clean:
        for h in harnesses:
            clean(h, output_root)
            print(f"cleaned {h}")
        return 0

    warnings = 0
    for h in harnesses:
        result = generate(h, output_root)
        print(f"{h}: {len(result.written)} file(s)")
        for note in result.notes:
            print(f"  note {note}")
        for w in result.warnings:
            print(f"  warn {w}", file=sys.stderr)
        warnings += len(result.warnings)
    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
