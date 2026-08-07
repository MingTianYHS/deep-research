from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent_contracts import build_synthesis_assignment
from .coordinator_budget import load_limits
from .critic_reviews import approved_reviews_for_run, reviews_for_run
from .io_utils import read_json
from .workflow import derive_workflow as derive_strict_workflow

STRICT_PROFILE = "deep"


def _ready_to_start(result: dict[str, Any], deferred_run_id: str | None) -> dict[str, Any]:
    progress = dict(result.get("progress") or {})
    if deferred_run_id:
        progress["deferred_reflection_run_id"] = deferred_run_id
    return {**result, "phase": "ready_to_start", "next_action": "start_run", "command": "research.py start --mode initial", "agent": None, "blockers": [], "assignments": [], "progress": progress, "coordinator_instruction": "Start the next run. Reflection from the previous run is deferred in lite/standard mode and must not block report delivery."}


def _review_limit_result(result: dict[str, Any], review_count: int, limit: int) -> dict[str, Any]:
    return {**result, "phase": "review_budget_exhausted", "next_action": "choose_partial_finish_or_deep_review", "command": None, "agent": None, "requires_user_input": True, "assignments": [], "blockers": [f"Critic review limit reached ({review_count}/{limit}); automatic full re-review is disabled."], "coordinator_instruction": "Do not invoke another Critic automatically. Ask the user to finish the run as partial with limitations or explicitly upgrade to the deep profile."}


def _direct_synthesis(result: dict[str, Any], root: Path, run_id: str) -> dict[str, Any] | None:
    reviews = approved_reviews_for_run(root, run_id)
    if not reviews:
        return None
    report = root / "reports" / f"{root.name}-final.md"
    return {**result, "phase": "synthesis", "next_action": "invoke_research_synthesizer", "agent": "research_synthesizer", "command": "agentctl.py synthesis-save --file synthesis-result.json", "assignments": [build_synthesis_assignment(root, run_id, report, reviews[-1])], "blockers": [], "progress": {**dict(result.get("progress") or {}), "report": str(report), "scaffold_skipped": True}, "coordinator_instruction": "Invoke the synthesizer once and save its compact six-section report. Do not create a separate report scaffold."}


def derive_workflow(root: Path, skill_dir: Path) -> dict[str, Any]:
    """Apply low-token defaults while preserving the strict deep profile."""
    result = derive_strict_workflow(root, skill_dir)
    state = read_json(root / "state.json", {})
    profile = str(state.get("budget_profile") or "standard")
    if profile == STRICT_PROFILE:
        return result
    limits = load_limits(skill_dir / "config/orchestration.toml", profile)

    if result.get("phase") in {"reflection", "reflection_blocked"}:
        run_id = (result.get("progress") or {}).get("run_id")
        return _ready_to_start(result, str(run_id) if run_id else None)

    if result.get("phase") == "claim_review":
        return {**result, "next_action": "sync_compact_run_claims", "command": "research.py claim-sync", "agent": None, "blockers": [], "coordinator_instruction": "Run the deterministic one-command Claim sync. Do not perform per-Claim create/link/status loops in lite/standard mode."}

    if result.get("phase") == "critic_remediation":
        assignments = list(result.get("assignments") or [])
        maximum = limits["max_targeted_searches"]
        if len(assignments) > maximum:
            result = {**result, "assignments": assignments[:maximum], "progress": {**dict(result.get("progress") or {}), "targeted_searches_requested": len(assignments), "targeted_searches_dispatched": maximum}}

    if result.get("next_action") == "invoke_research_critic":
        run_id = str(state.get("active_run_id") or "")
        previous_id = (result.get("progress") or {}).get("previous_critic_review_id")
        if run_id and previous_id:
            review_count = len(reviews_for_run(root, run_id))
            maximum = limits["max_critic_reviews"]
            if review_count >= maximum:
                return _review_limit_result(result, review_count, maximum)

    if result.get("next_action") == "create_report_scaffold":
        run_id = str(state.get("active_run_id") or "")
        direct = _direct_synthesis(result, root, run_id) if run_id else None
        if direct:
            return direct

    if result.get("next_action") == "initialize_quote_audit":
        report = (result.get("progress") or {}).get("report")
        if report:
            return {**result, "next_action": "run_mechanical_lineage_audit", "agent": None, "command": f'qualityctl.py audit-mechanical --report "{report}"', "blockers": [], "coordinator_instruction": "Run the deterministic Evidence/Source Attempt lineage audit. Do not invoke research_critic for a second post-synthesis pass in lite/standard mode."}
    return result
