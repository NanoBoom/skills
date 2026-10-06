"""Per-harness adapters. Each one reads plugins/ and writes one harness's artifacts."""

from __future__ import annotations

from tools.adapters.base import HarnessAdapter
from tools.adapters.codex import CodexAdapter
from tools.adapters.pi import PiAdapter

# Every harness with an adapter. Claude Code is the source format, not a target.
ADAPTERS: dict[str, type[HarnessAdapter]] = {a.harness_id: a for a in (CodexAdapter, PiAdapter)}


def generated_harnesses() -> list[str]:
    return list(ADAPTERS)


def get_adapter(harness_id: str, **kwargs) -> HarnessAdapter:
    if harness_id not in ADAPTERS:
        raise ValueError(f"unknown harness: {harness_id}")
    return ADAPTERS[harness_id](**kwargs)
