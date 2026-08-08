from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json

CURRENT_WORKSPACE_FORMAT = 3


def inspect(root: Path) -> dict[str, Any]:
    state = read_json(root / "state.json", {})
    version = state.get("workspace_format_version")
    errors: list[str] = []
    if version != CURRENT_WORKSPACE_FORMAT:
        errors.append(
            f"workspace format {version!r} is unsupported by this development runtime; create a new format-{CURRENT_WORKSPACE_FORMAT} workspace"
        )
    for relative in ("topic.toml", "state.json", "evidence/cards.jsonl", "claims.jsonl"):
        if not (root / relative).exists():
            errors.append(f"missing required workspace file: {relative}")
    return {
        "workspace": str(root),
        "version": version,
        "current_version": CURRENT_WORKSPACE_FORMAT,
        "explicit_version": "workspace_format_version" in state,
        "needs_migration": False,
        "errors": errors,
        "valid": not errors,
    }


def plan(root: Path) -> dict[str, Any]:
    return {**inspect(root), "actions": []}


def apply(root: Path) -> dict[str, Any]:
    result = plan(root)
    if not result["valid"]:
        raise ValueError("; ".join(result["errors"]))
    return {**result, "applied": False}
