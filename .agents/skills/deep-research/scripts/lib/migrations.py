from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import append_jsonl, atomic_write_json, read_json, utc_now

CURRENT_WORKSPACE_FORMAT = 1


def inspect(root: Path) -> dict[str, Any]:
    state_path = root / "state.json"
    state = read_json(state_path, {})
    explicit = "workspace_format_version" in state
    version = state.get("workspace_format_version", 1)
    errors = []
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        errors.append("workspace_format_version must be a non-negative integer")
    elif version > CURRENT_WORKSPACE_FORMAT:
        errors.append(f"workspace format {version} is newer than runtime {CURRENT_WORKSPACE_FORMAT}")
    for relative in ("topic.toml", "state.json", "evidence/cards.jsonl", "claims.jsonl"):
        if not (root / relative).exists():
            errors.append(f"missing required workspace file: {relative}")
    return {"workspace": str(root), "version": version, "current_version": CURRENT_WORKSPACE_FORMAT, "explicit_version": explicit, "needs_migration": not errors and (version < CURRENT_WORKSPACE_FORMAT or not explicit), "errors": errors, "valid": not errors}


def plan(root: Path) -> dict[str, Any]:
    result = inspect(root)
    actions = []
    if result["valid"] and not result["explicit_version"]:
        actions.append({"from": 1, "to": 1, "action": "stamp explicit workspace format version"})
    elif result["valid"] and result["version"] == 0:
        actions.append({"from": 0, "to": 1, "action": "adopt append-only claims/evidence workspace contract"})
    result["actions"] = actions
    return result


def apply(root: Path) -> dict[str, Any]:
    migration = plan(root)
    if not migration["valid"]:
        raise ValueError("; ".join(migration["errors"]))
    if not migration["actions"]:
        return {**migration, "applied": False}
    state_path = root / "state.json"
    state = read_json(state_path, {})
    previous = state.get("workspace_format_version", "implicit-1")
    state["workspace_format_version"] = CURRENT_WORKSPACE_FORMAT
    atomic_write_json(state_path, state)
    event = {"type": "workspace.migrated", "from": previous, "to": CURRENT_WORKSPACE_FORMAT, "at": utc_now(), "actions": migration["actions"]}
    append_jsonl(root / "logs/migrations.jsonl", [event])
    return {**inspect(root), "actions": migration["actions"], "applied": True, "event": event}
