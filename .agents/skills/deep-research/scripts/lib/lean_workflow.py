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
    if deferred_run_id: progress["deferred_reflection_run_id"] = deferred_run_id
    return {**result, "phase": "ready_to_start", "next_action": "start_run", "command": "research.py start --mode initial", "agent": None, "blockers": [], "assignments": [], "progress": progress, "coordinator_instruction": "The previous reflection is optional. Wait for explicit user approval; use research.py continue after a completed baseline."}


def _review_limit_result(result: dict[str, Any], review_count: int, limit: int) -> dict[str, Any]:
    return {**result, "phase": "review_budget_exhausted", "next_action": "choose_partial_finish", "command": None, "agent": None, "requires_user_input": True, "assignments": [], "blockers": [f"Bounded Critic cycle reached its limit ({review_count}/{limit})."], "coordinator_instruction": "Do not invoke another Critic automatically. Present unresolved findings and ask whether to finish partial."}


def _direct_synthesis(result: dict[str, Any], root: Path, run_id: str) -> dict[str, Any] | None:
    reviews = approved_reviews_for_run(root, run_id)
    if not reviews: return None
    report = root / "reports" / f"{root.name}-final.md"
    return {**result, "phase": "synthesis", "next_action": "invoke_research_synthesizer", "agent": "research_synthesizer", "command": "agentctl.py synthesis-save --file synthesis-result.json", "assignments": [build_synthesis_assignment(root, run_id, report, reviews[-1])], "blockers": [], "progress": {**dict(result.get("progress") or {}), "report": str(report), "scaffold_skipped": True}, "coordinator_instruction": "Invoke the synthesizer once; save its six-section report, bounded knowledge delta, and follow-up backlog. Do not create a scaffold."}


def _run_has_disconfirmation(root: Path, run_id: str) -> bool:
    for path in (root / "logs/workers").glob("*.json"):
        worker = read_json(path, {})
        if worker.get("run_id") == run_id and any(isinstance(query, dict) and query.get("intent") == "disconfirming" for query in worker.get("queries_run", [])): return True
    return False


def _needs_new_search(assignment: dict[str, Any]) -> bool:
    return (assignment.get("reuse_plan") or {}).get("recommended_action") != "reuse_existing_evidence_before_search"


def _compact_assignments(result: dict[str, Any], root: Path, run_id: str, profile: str) -> dict[str, Any]:
    assignments = [dict(item) for item in (result.get("assignments") or [])]
    if not assignments or result.get("agent") != "topic_researcher" or not any(item.get("question_id") for item in assignments): return result
    already_done = _run_has_disconfirmation(root, run_id); first_standard = None
    if profile == "standard" and not already_done:
        candidates = [item for item in assignments if item.get("question_id") and not item.get("remediation") and _needs_new_search(item)]
        if candidates: first_standard = min(candidates, key=lambda item: str(item["question_id"]))
    compacted = []
    for item in assignments:
        if not item.get("question_id"): compacted.append(item); continue
        remediation = item.get("remediation") or {}; required = remediation.get("intent") == "disconfirming" or item is first_standard; item["disconfirming_required"] = bool(required)
        if not required: item["disconfirming_query"] = None
        item["worker_result_contract"] = "compact_v2"; compacted.append(item)
    return {**result, "assignments": compacted, "progress": {**dict(result.get("progress") or {}), "run_level_disconfirmation_already_done": already_done, "run_level_disconfirmation_dispatched": bool(first_standard)}}


def _targeted_recheck(result: dict[str, Any], reviews: list[dict[str, Any]], previous_id: str) -> dict[str, Any]:
    previous = next((item for item in reviews if item.get("id") == previous_id), None)
    assignments = [dict(item) for item in (result.get("assignments") or [])]
    finding_ids = [str(item.get("id")) for item in (previous or {}).get("findings", []) if isinstance(item, dict) and item.get("id")]
    for assignment in assignments:
        assignment.update(review_mode="targeted_recheck", allowed_finding_ids=finding_ids, recheck_constraints=["Check only whether the previous findings are resolved.", "Do not introduce new findings.", "Return resolved or unresolved for each allowed finding ID."])
    return {**result, "assignments": assignments, "progress": {**dict(result.get("progress") or {}), "critic_cycle": "targeted_recheck", "allowed_finding_ids": finding_ids}, "coordinator_instruction": "Invoke one compact targeted recheck. It may resolve only the previous findings and may not open a new review cycle."}


def derive_workflow(root: Path, skill_dir: Path) -> dict[str, Any]:
    result = derive_strict_workflow(root, skill_dir); state = read_json(root / "state.json", {}); profile = str(state.get("budget_profile") or "standard")
    if profile == STRICT_PROFILE: return result
    limits = load_limits(skill_dir / "config/orchestration.toml", profile); run_id = str(state.get("active_run_id") or "")
    if result.get("phase") in {"reflection", "reflection_blocked"}:
        prior = (result.get("progress") or {}).get("run_id"); return _ready_to_start(result, str(prior) if prior else None)
    if result.get("phase") == "claim_review": return {**result, "next_action": "sync_compact_run_claims", "command": "research.py claim-sync", "agent": None, "blockers": [], "coordinator_instruction": "Run one deterministic Claim sync. Do not perform per-Claim loops."}
    if result.get("agent") == "topic_researcher" and run_id: result = _compact_assignments(result, root, run_id, profile)
    if result.get("phase") == "critic_remediation":
        assignments = list(result.get("assignments") or []); maximum = limits["max_targeted_searches"]
        if len(assignments) > maximum: result = {**result, "assignments": assignments[:maximum], "progress": {**dict(result.get("progress") or {}), "targeted_searches_requested": len(assignments), "targeted_searches_dispatched": maximum}}
    if result.get("next_action") == "invoke_research_critic":
        previous_id = (result.get("progress") or {}).get("previous_critic_review_id")
        if run_id:
            reviews = reviews_for_run(root, run_id); base_limit = limits["max_critic_reviews"]; allowed = base_limit + (1 if previous_id else 0)
            if len(reviews) >= allowed: return _review_limit_result(result, len(reviews), allowed)
            if previous_id: result = _targeted_recheck(result, reviews, str(previous_id))
    if result.get("next_action") == "create_report_scaffold":
        direct = _direct_synthesis(result, root, run_id) if run_id else None
        if direct: return direct
    if result.get("next_action") == "initialize_quote_audit":
        report = (result.get("progress") or {}).get("report")
        if report: return {**result, "next_action": "run_mechanical_lineage_audit", "agent": None, "command": f'qualityctl.py audit-mechanical --report "{report}"', "blockers": [], "coordinator_instruction": "Run deterministic Evidence/Source Attempt lineage audit; do not invoke a second full Critic."}
    return result
