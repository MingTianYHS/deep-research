from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json
from .workflow import derive_workflow as derive_strict_workflow


STRICT_PROFILE = "deep"


def _ready_to_start(result: dict[str, Any], deferred_run_id: str | None) -> dict[str, Any]:
    progress = dict(result.get("progress") or {})
    if deferred_run_id:
        progress["deferred_reflection_run_id"] = deferred_run_id
    return {
        **result,
        "phase": "ready_to_start",
        "next_action": "start_run",
        "command": "research.py start --mode initial",
        "agent": None,
        "blockers": [],
        "assignments": [],
        "progress": progress,
        "coordinator_instruction": (
            "Start the next run. Reflection from the previous run is deferred in "
            "lite/standard mode and must not block report delivery."
        ),
    }


def derive_workflow(root: Path, skill_dir: Path) -> dict[str, Any]:
    """Apply low-token defaults while preserving the strict deep profile.

    lite/standard defer post-run Reflection and replace the second semantic
    Critic pass for quote auditing with a deterministic lineage audit. The deep
    profile keeps the original audit-grade workflow unchanged.
    """
    result = derive_strict_workflow(root, skill_dir)
    state = read_json(root / "state.json", {})
    if str(state.get("budget_profile") or "standard") == STRICT_PROFILE:
        return result

    if result.get("phase") in {"reflection", "reflection_blocked"}:
        run_id = (result.get("progress") or {}).get("run_id")
        return _ready_to_start(result, str(run_id) if run_id else None)

    if result.get("next_action") == "initialize_quote_audit":
        report = (result.get("progress") or {}).get("report")
        if report:
            return {
                **result,
                "next_action": "run_mechanical_lineage_audit",
                "agent": None,
                "command": f'qualityctl.py audit-mechanical --report "{report}"',
                "blockers": [],
                "coordinator_instruction": (
                    "Run the deterministic Evidence/Source Attempt lineage audit. "
                    "Do not invoke research_critic for a second post-synthesis pass "
                    "in lite/standard mode."
                ),
            }
    return result
