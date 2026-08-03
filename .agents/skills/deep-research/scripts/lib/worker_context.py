from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .io_utils import read_json

WORKER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")


def _questions(design: dict[str, Any]) -> list[dict[str, Any]]:
    value = design.get("questions", [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _version_anchor_matches(result: dict[str, Any], question: dict[str, Any]) -> bool:
    targets = [str(question.get(key, "")).strip().casefold() for key in ("target_version", "target_commit")]
    targets = [value for value in targets if value]
    if not targets:
        return True
    for query in result.get("queries_run", []):
        if not isinstance(query, dict) or query.get("intent") != "version_check":
            continue
        anchor = str(query.get("time_anchor", "")).strip().casefold()
        if anchor and any(target in anchor or anchor in target for target in targets):
            return True
    return False


def validate_ingest_context(topic_root: Path, result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("worker_result_version") != 2:
        errors.append("new worker ingestion requires worker_result_version 2")
    worker_result_id = result.get("worker_result_id")
    if not isinstance(worker_result_id, str) or not WORKER_ID.fullmatch(worker_result_id):
        errors.append("worker_result_id must be a safe non-empty string of at most 160 characters")
    run_id = result.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        errors.append("run_id must be a non-empty string")

    state = read_json(topic_root / "state.json", {})
    active_run_id = state.get("active_run_id")
    if not active_run_id:
        errors.append("worker ingestion requires an active run")
    elif run_id != active_run_id:
        errors.append(f"worker run_id {run_id} does not match active run {active_run_id}")

    topic_profile = state.get("budget_profile", "standard")
    if result.get("budget_profile") != topic_profile:
        errors.append("worker budget_profile does not match topic budget_profile")

    design_path = topic_root / "plans/current-design.json"
    design = read_json(design_path, {})
    if not design_path.is_file() or not isinstance(design, dict):
        errors.append("worker ingestion requires plans/current-design.json")
        question = None
    else:
        question_id = result.get("question_id")
        question = next((item for item in _questions(design) if item.get("id") == question_id), None)
        if not question:
            errors.append(f"worker question_id {question_id} is not in the current Research Design")
        else:
            if question.get("status", "open") != "open":
                errors.append(f"worker question {question_id} is not open")
            if result.get("overlap_key") != question.get("overlap_key"):
                errors.append("worker overlap_key does not match the current Research Design")
            question_profile = question.get("worker_budget_profile", topic_profile)
            if result.get("budget_profile") != question_profile:
                errors.append("worker budget_profile does not match the assigned question")
            if question.get("version_sensitive") and not _version_anchor_matches(result, question):
                errors.append("version-sensitive question requires a matching version_check query anchor")

    if isinstance(worker_result_id, str) and WORKER_ID.fullmatch(worker_result_id):
        worker_path = topic_root / "logs/workers" / f"{worker_result_id}.json"
        if worker_path.exists():
            try:
                existing = json.loads(worker_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
            if existing.get("worker_result_id") == worker_result_id:
                errors.append(f"worker_result_id already ingested: {worker_result_id}")
            else:
                errors.append(f"worker result log path already exists: {worker_result_id}")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "active_run_id": active_run_id,
        "topic_budget_profile": topic_profile,
        "question_id": result.get("question_id"),
        "worker_result_id": worker_result_id,
    }
