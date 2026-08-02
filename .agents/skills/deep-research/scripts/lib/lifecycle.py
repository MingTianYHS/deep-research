from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .claims import materialize
from .evidence import canonical_url, worker_result_id
from .io_utils import atomic_write_json, iter_jsonl, read_json, utc_now
from .research_design import validate_design

RECOMMENDATIONS = {"complete", "partial", "failed"}
LESSON_DECISIONS = {"accept", "reject"}


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")


def validate_critic_review(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for key in ("review_id", "run_id", "status", "findings", "targeted_searches", "unresolved", "lesson_decisions", "completion_recommendation", "stop_reason"):
        if key not in value:
            errors.append(f"missing {key}")
    for key in ("review_id", "run_id", "status", "stop_reason"):
        if not isinstance(value.get(key), str) or not value.get(key, "").strip():
            errors.append(f"{key} must be a non-empty string")
    if value.get("completion_recommendation") not in RECOMMENDATIONS:
        errors.append("completion_recommendation must be complete, partial, or failed")
    for key in ("findings", "targeted_searches", "unresolved", "lesson_decisions"):
        if not isinstance(value.get(key), list):
            errors.append(f"{key} must be a list")
    if isinstance(value.get("targeted_searches"), list) and len(value["targeted_searches"]) > 3:
        errors.append("targeted_searches allows at most 3 items")
    decisions = value.get("lesson_decisions", []) if isinstance(value.get("lesson_decisions"), list) else []
    seen: set[str] = set()
    for index, item in enumerate(decisions, 1):
        if not isinstance(item, dict):
            errors.append(f"lesson_decisions[{index}] must be an object")
            continue
        candidate_id = item.get("candidate_id")
        if not candidate_id or candidate_id in seen:
            errors.append(f"lesson_decisions[{index}] requires a unique candidate_id")
        else:
            seen.add(candidate_id)
        if item.get("decision") not in LESSON_DECISIONS:
            errors.append(f"lesson_decisions[{index}] invalid decision")
        if not item.get("reason"):
            errors.append(f"lesson_decisions[{index}] missing reason")
        if item.get("decision") == "accept":
            for field in ("type", "lesson"):
                if not item.get(field):
                    errors.append(f"lesson_decisions[{index}] accepted lesson missing {field}")
    return {"valid": not errors, "errors": sorted(set(errors))}


def _run_exists(root: Path, run_id: str) -> bool:
    return any(event.get("id") == run_id for _, event in iter_jsonl(root / "logs/runs.jsonl"))


def record_critic_review(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    result = validate_critic_review(value)
    if not result["valid"]:
        raise ValueError("invalid critic review: " + "; ".join(result["errors"]))
    if not _run_exists(root, value["run_id"]):
        raise ValueError(f"critic review references unknown run: {value['run_id']}")
    review_id = _safe_id(value["review_id"])
    if not review_id:
        raise ValueError("invalid critic review id")
    path = root / "logs/critics" / f"{review_id}.json"
    if path.exists():
        existing = read_json(path, {})
        if existing == value:
            return {"path": str(path), "review_id": review_id, "already_recorded": True}
        raise ValueError(f"critic review already exists with different content: {review_id}")
    stored = dict(value)
    stored["review_id"] = review_id
    stored["recorded_at"] = utc_now()
    atomic_write_json(path, stored)
    return {"path": str(path), "review_id": review_id, "already_recorded": False}


def load_critic_review(root: Path, review_id: str) -> dict[str, Any]:
    path = root / "logs/critics" / f"{_safe_id(review_id)}.json"
    if not path.is_file():
        raise ValueError(f"critic review not found: {review_id}")
    value = read_json(path, {})
    result = validate_critic_review(value)
    if not result["valid"]:
        raise ValueError("stored critic review is invalid: " + "; ".join(result["errors"]))
    return value


def validate_reflection_link(root: Path, reflection: dict[str, Any]) -> dict[str, Any]:
    review = load_critic_review(root, str(reflection.get("critic_review_id", "")))
    if review.get("run_id") != reflection.get("run_id"):
        raise ValueError("reflection run_id does not match critic review")
    accepted = {
        str(item["candidate_id"]): item
        for item in review.get("lesson_decisions", [])
        if item.get("decision") == "accept"
    }
    supplied = reflection.get("lesson_candidates", [])
    supplied_ids = {str(item.get("candidate_id")) for item in supplied}
    if supplied_ids != set(accepted):
        raise ValueError("reflection lessons must exactly match critic-accepted lesson candidates")
    for item in supplied:
        decision = accepted[str(item["candidate_id"])]
        for field in ("type", "scope", "lesson"):
            if str(item.get(field, "")).strip() != str(decision.get(field, "")).strip():
                raise ValueError(f"reflection lesson {item['candidate_id']} does not match critic decision")
    return review


def source_attempt_map(root: Path) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for _, attempt in iter_jsonl(root / "logs/source_attempts.jsonl"):
        attempt_id = attempt.get("id")
        if attempt_id:
            values[str(attempt_id)] = attempt
    return values


def validate_provenance(root: Path) -> list[str]:
    errors: list[str] = []
    attempts: dict[str, dict[str, Any]] = {}
    seen_attempts: set[str] = set()
    for number, attempt in iter_jsonl(root / "logs/source_attempts.jsonl"):
        attempt_id = str(attempt.get("id", ""))
        if not attempt_id:
            errors.append(f"source attempt line {number}: missing id")
            continue
        if attempt_id in seen_attempts:
            errors.append(f"source attempt line {number}: duplicate id {attempt_id}")
        seen_attempts.add(attempt_id)
        attempts[attempt_id] = attempt
    for number, card in iter_jsonl(root / "evidence/cards.jsonl"):
        attempt = attempts.get(str(card.get("source_attempt_id", "")))
        if not attempt:
            errors.append(f"evidence line {number}: unknown source_attempt_id")
            continue
        if attempt.get("status") != "accepted" or attempt.get("eligible_for_evidence") is not True:
            errors.append(f"evidence line {number}: source attempt is not accepted")
        try:
            if canonical_url(str(card.get("source", {}).get("url", ""))) != attempt.get("normalized_url"):
                errors.append(f"evidence line {number}: source URL does not match source attempt")
        except ValueError as exc:
            errors.append(f"evidence line {number}: {exc}")
        if card.get("content_sha256") != attempt.get("content_sha256"):
            errors.append(f"evidence line {number}: content hash does not match source attempt")
    return errors


def worker_results(root: Path, run_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for path in (root / "logs/workers").glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("run_id") == run_id:
            values.append(value)
    return values


def has_worker_result(root: Path, result: dict[str, Any]) -> bool:
    expected = worker_result_id(result)
    return any(value.get("_ingestion", {}).get("id") == expected for value in worker_results(root, str(result.get("run_id", ""))))


def completion_check(root: Path, run_id: str, profile: str) -> dict[str, Any]:
    errors: list[str] = []
    design_path = root / "plans/current-design.json"
    design = read_json(design_path, None) if design_path.exists() else None
    if not design:
        errors.append("complete run requires plans/current-design.json")
        open_ids: set[str] = set()
    else:
        checked = validate_design(design, profile)
        errors.extend(f"design: {item}" for item in checked["errors"])
        open_ids = {str(item.get("id")) for item in design.get("questions", []) if item.get("status", "open") == "open"}
    workers = worker_results(root, run_id)
    if not workers:
        errors.append("complete run requires at least one ingested worker result")
    completed_questions = {str(item.get("question_id")) for item in workers if item.get("status") == "complete" and item.get("coverage_status") == "sufficient"}
    missing = sorted(open_ids - completed_questions)
    if missing:
        errors.append(f"open questions without complete worker coverage: {missing}")
    evidence_ids = {str(item.get("id")) for _, item in iter_jsonl(root / "evidence/cards.jsonl") if item.get("id")}
    if not evidence_ids:
        errors.append("complete run requires accepted evidence")
    materialized = materialize(root / "claims.jsonl")
    material = [claim for claim in materialized.values() if claim.get("status") in {"supported", "contested", "unresolved"} and claim.get("relations")]
    if not material:
        errors.append("complete run requires at least one evidence-linked material claim")
    reviews = []
    for path in (root / "logs/critics").glob("*.json"):
        value = read_json(path, {})
        if value.get("run_id") == run_id:
            reviews.append(value)
    if not reviews:
        errors.append("complete run requires a recorded critic review")
    elif not any(value.get("completion_recommendation") == "complete" for value in reviews):
        errors.append("critic did not recommend complete")
    errors.extend(validate_provenance(root))
    return {"valid": not errors, "errors": sorted(set(errors)), "worker_count": len(workers), "completed_questions": sorted(completed_questions), "evidence_count": len(evidence_ids), "material_claim_count": len(material), "critic_reviews": len(reviews)}
