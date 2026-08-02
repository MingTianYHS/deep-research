from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import append_jsonl, atomic_write_json, read_json, utc_now
from .topic_context import build_brief, render_context

CURRENT_WORKSPACE_FORMAT = 2


def inspect(root: Path) -> dict[str, Any]:
    state = read_json(root / "state.json", {})
    explicit = "workspace_format_version" in state
    version = state.get("workspace_format_version", 1)
    errors: list[str] = []
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        errors.append("workspace_format_version must be a non-negative integer")
    elif version > CURRENT_WORKSPACE_FORMAT:
        errors.append(f"workspace format {version} is newer than runtime {CURRENT_WORKSPACE_FORMAT}")
    for relative in ("topic.toml", "state.json", "evidence/cards.jsonl", "claims.jsonl"):
        if not (root / relative).exists():
            errors.append(f"missing required workspace file: {relative}")
    return {
        "workspace": str(root),
        "version": version,
        "current_version": CURRENT_WORKSPACE_FORMAT,
        "explicit_version": explicit,
        "needs_migration": not errors and (version < CURRENT_WORKSPACE_FORMAT or not explicit),
        "errors": errors,
        "valid": not errors,
    }


def plan(root: Path) -> dict[str, Any]:
    result = inspect(root)
    actions = []
    if result["valid"] and (result["version"] < 2 or not result["explicit_version"]):
        actions = [
            {
                "from": result["version"],
                "to": 2,
                "action": "create canonical topic-expert AGENTS.md while preserving legacy AGENT.md for review",
            },
            {
                "from": result["version"],
                "to": 2,
                "action": "add bounded context and validated reusable lessons",
            },
        ]
    result["actions"] = actions
    return result


def _default_agents(root: Path) -> str:
    return f"""# Topic expert coordinator

This directory is the persistent research workspace. Load the user-level `deep-research` Skill. The main Codex session owns planning, approvals, state, and writes.

Delegate execution only to `topic_researcher`, `research_critic`, and `research_synthesizer`. Subagents are read-only and may not spawn other agents.

Read `{(root / 'context.md').as_posix()}` as a bounded, rebuildable cache, never as evidence. Every material fact must trace to Claim/Evidence and an accepted Source Attempt.

If `AGENT.md` exists, it is preserved only as a legacy migration artifact. Review it manually; `AGENTS.md` is the active coordinator contract.
"""


def apply(root: Path) -> dict[str, Any]:
    migration = plan(root)
    if not migration["valid"]:
        raise ValueError("; ".join(migration["errors"]))
    if not migration["actions"]:
        return {**migration, "applied": False}
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "memory/lessons.jsonl").touch(exist_ok=True)
    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        agents_path.write_text(_default_agents(root), encoding="utf-8")
    state = read_json(root / "state.json", {})
    previous = state.get("workspace_format_version", "implicit-1")
    state["workspace_format_version"] = CURRENT_WORKSPACE_FORMAT
    state.setdefault("baseline_completed", bool(state.get("last_run_at")))
    state.setdefault("research_generation", 1 if state.get("last_run_at") else 0)
    state.setdefault("knowledge_status", "evolving" if state.get("last_run_at") else "empty")
    state.setdefault("context_generated_at", None)
    atomic_write_json(root / "state.json", state)
    render_context(root, build_brief(root))
    event = {
        "type": "workspace.migrated",
        "from": previous,
        "to": CURRENT_WORKSPACE_FORMAT,
        "at": utc_now(),
        "actions": migration["actions"],
        "legacy_agent_preserved": (root / "AGENT.md").exists(),
    }
    append_jsonl(root / "logs/migrations.jsonl", [event])
    return {
        **inspect(root),
        "actions": migration["actions"],
        "applied": True,
        "event": event,
    }
