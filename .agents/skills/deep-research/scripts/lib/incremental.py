"""Deprecated compatibility helper; active briefs are built by topic_context.build_brief."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .claims import materialize
from .topic_context import build_brief


def build_plan(state: dict[str, Any], claims: dict[str, dict[str, Any]], evidence_path: Path) -> dict[str, Any]:
    root = evidence_path.parent.parent
    if not (root / "claims.jsonl").exists() or materialize(root / "claims.jsonl") != claims:
        raise ValueError("legacy build_plan requires the canonical topic workspace")
    return build_brief(root)
