from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .io_utils import iter_jsonl, read_json
from .migrations import CURRENT_WORKSPACE_FORMAT
from .research_memory import evidence_freshness, latest_verifications

WORKER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
REPEAT_REASONS = {"stale_refresh", "scope_changed", "version_changed", "critic_remediation", "previous_low_yield"}


def _questions(design: dict[str, Any]) -> list[dict[str, Any]]:
    value = design.get("questions", []); return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _normalized_query(value: Any) -> str: return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _version_anchor_matches(result: dict[str, Any], question: dict[str, Any]) -> bool:
    targets = [str(question.get(key, "")).strip().casefold() for key in ("target_version", "target_commit")]; targets = [value for value in targets if value]
    if not targets: return True
    for query in result.get("queries_run", []):
        if not isinstance(query, dict) or query.get("intent") != "version_check": continue
        anchor = str(query.get("time_anchor", "")).strip().casefold()
        if anchor and any(target in anchor for target in targets): return True
    return False


def _persisted_query_keys(topic_root: Path, worker_result_id: str | None) -> set[tuple[str, str]]:
    values: set[tuple[str, str]] = set(); directory = topic_root / "logs/workers"
    if not directory.is_dir(): return values
    for path in directory.glob("*.json"):
        worker = read_json(path, {})
        if not isinstance(worker, dict) or worker.get("worker_result_id") == worker_result_id: continue
        for query in worker.get("queries_run", []) if isinstance(worker.get("queries_run"), list) else []:
            if isinstance(query, dict) and _normalized_query(query.get("query")): values.add((_normalized_query(query.get("query")), str(query.get("intent") or "")))
    return values


def validate_ingest_context(topic_root: Path, result: dict[str, Any], *, allow_existing_worker: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("worker_result_version") != 2: errors.append("new worker ingestion requires worker_result_version 2")
    worker_result_id = result.get("worker_result_id")
    if not isinstance(worker_result_id, str) or not WORKER_ID.fullmatch(worker_result_id): errors.append("worker_result_id must be a safe non-empty string of at most 160 characters")
    run_id = result.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip(): errors.append("run_id must be a non-empty string")
    state = read_json(topic_root / "state.json", {}); active_run_id = state.get("active_run_id")
    if state.get("workspace_format_version") != CURRENT_WORKSPACE_FORMAT: errors.append(f"workspace_format_version must be {CURRENT_WORKSPACE_FORMAT}")
    if not active_run_id: errors.append("worker ingestion requires an active run")
    elif run_id != active_run_id: errors.append(f"worker run_id {run_id} does not match active run {active_run_id}")
    scope = state.get("active_run_scope"); assigned: set[str] = set()
    if active_run_id:
        if not isinstance(scope, dict) or scope.get("run_id") != active_run_id: errors.append("worker ingestion requires a matching active_run_scope")
        else:
            values = scope.get("assigned_question_ids")
            if not isinstance(values, list) or not values: errors.append("active_run_scope requires assigned_question_ids")
            else: assigned = set(map(str, values))
    topic_profile = state.get("budget_profile", "standard")
    if result.get("budget_profile") != topic_profile: errors.append("worker budget_profile does not match topic budget_profile")
    design_path = topic_root / "plans/current-design.json"; design = read_json(design_path, {}); question_id = result.get("question_id")
    if assigned and str(question_id) not in assigned: errors.append(f"worker question_id {question_id} is outside the active run scope")
    if not design_path.is_file() or not isinstance(design, dict): errors.append("worker ingestion requires plans/current-design.json")
    else:
        question = next((item for item in _questions(design) if item.get("id") == question_id), None)
        if not question: errors.append(f"worker question_id {question_id} is not in the current Research Design")
        else:
            if question.get("status", "open") != "open": errors.append(f"worker question {question_id} is not open")
            if result.get("overlap_key") != question.get("overlap_key"): errors.append("worker overlap_key does not match the current Research Design")
            if result.get("budget_profile") != question.get("worker_budget_profile", topic_profile): errors.append("worker budget_profile does not match the assigned question")
            if question.get("version_sensitive") and not _version_anchor_matches(result, question): errors.append("version-sensitive question requires a matching version_check query anchor")
    evidence = {str(item.get("id")): item for _, item in iter_jsonl(topic_root / "evidence/cards.jsonl") if item.get("id")}; reused = result.get("reused_evidence_ids", []); rationale = result.get("reuse_rationale", {}); verifications = latest_verifications(topic_root); reuse_freshness: dict[str, str] = {}
    if isinstance(reused, list):
        for evidence_id in reused:
            card = evidence.get(str(evidence_id))
            if not card: errors.append(f"reused Evidence does not exist: {evidence_id}")
            elif card.get("prompt_injection_risk") == "high": errors.append(f"high-risk Evidence cannot be reused: {evidence_id}")
            else:
                reuse_freshness[str(evidence_id)] = evidence_freshness(topic_root, card, verifications=verifications)
                if card.get("question_id") != question_id and (not isinstance(rationale, dict) or not str(rationale.get(str(evidence_id)) or "").strip()): errors.append(f"cross-question reused Evidence requires reuse_rationale: {evidence_id}")
    reuse_only = bool(reused) and not result.get("queries_run") and not result.get("source_attempts") and not result.get("evidence_cards")
    if result.get("status") == "complete" and reuse_only:
        stale = sorted(evidence_id for evidence_id, freshness in reuse_freshness.items() if freshness != "fresh")
        if stale: errors.append(f"reuse-only completion requires fresh Evidence; refresh known URLs for {stale}")
    persisted = _persisted_query_keys(topic_root, str(worker_result_id) if isinstance(worker_result_id, str) else None)
    for index, query in enumerate(result.get("queries_run", []) if isinstance(result.get("queries_run"), list) else [], 1):
        if not isinstance(query, dict): continue
        reason = query.get("repeat_reason")
        if reason is not None and reason not in REPEAT_REASONS: errors.append(f"queries_run[{index}] has invalid repeat_reason")
        key = (_normalized_query(query.get("query")), str(query.get("intent") or ""))
        if key in persisted and reason not in REPEAT_REASONS: errors.append(f"queries_run[{index}] repeats a persisted query without an allowed repeat_reason")
    if isinstance(worker_result_id, str) and WORKER_ID.fullmatch(worker_result_id) and not allow_existing_worker:
        worker_path = topic_root / "logs/workers" / f"{worker_result_id}.json"
        if worker_path.exists():
            try: existing = json.loads(worker_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): existing = {}
            if existing.get("worker_result_id") == worker_result_id: errors.append(f"worker_result_id already ingested: {worker_result_id}")
            else: errors.append(f"worker result log path already exists: {worker_result_id}")
    return {"valid": not errors, "errors": sorted(set(errors)), "active_run_id": active_run_id, "topic_budget_profile": topic_profile, "question_id": result.get("question_id"), "worker_result_id": worker_result_id, "reuse_freshness": reuse_freshness}
