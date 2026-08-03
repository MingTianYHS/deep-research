from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, read_json, utc_now

REVIEW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
APPROVED_STATUSES = {"approved", "approved_with_findings"}
REVIEW_STATUSES = APPROVED_STATUSES | {"changes_required"}
SEVERITIES = {"blocker", "high", "medium", "low", "info"}


def validate_review(value: dict[str, Any], active_run_id: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    review_id = value.get("id")
    if not isinstance(review_id, str) or not REVIEW_ID.fullmatch(review_id):
        errors.append("critic review id must be a safe non-empty string of at most 160 characters")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        errors.append("critic review run_id must be a non-empty string")
    elif active_run_id is not None and run_id != active_run_id:
        errors.append(f"critic review run_id {run_id} does not match active run {active_run_id}")
    if value.get("reviewed_by") != "research_critic":
        errors.append("critic review reviewed_by must be research_critic")
    if value.get("status") not in REVIEW_STATUSES:
        errors.append(f"invalid critic review status: {value.get('status')}")
    for key in ("findings", "targeted_searches", "unresolved"):
        if not isinstance(value.get(key), list):
            errors.append(f"critic review {key} must be a list")
    findings = value.get("findings", []) if isinstance(value.get("findings"), list) else []
    for index, finding in enumerate(findings, 1):
        if not isinstance(finding, dict):
            errors.append(f"critic finding {index} must be an object")
            continue
        if finding.get("severity") not in SEVERITIES:
            errors.append(f"critic finding {index} has invalid severity")
        for field in ("issue_type", "explanation", "required_action"):
            if not isinstance(finding.get(field), str) or not finding.get(field, "").strip():
                errors.append(f"critic finding {index} requires {field}")
    unresolved = value.get("unresolved", []) if isinstance(value.get("unresolved"), list) else []
    if value.get("status") in APPROVED_STATUSES:
        serious = [item for item in findings if isinstance(item, dict) and item.get("severity") in {"blocker", "high"}]
        if serious or unresolved:
            errors.append("approved critic review cannot contain blocker/high findings or unresolved items")
    if not isinstance(value.get("stop_reason"), str) or not value.get("stop_reason", "").strip():
        errors.append("critic review requires stop_reason")
    return {"valid": not errors, "errors": sorted(set(errors))}


def save_review(root: Path, value: dict[str, Any], active_run_id: str) -> dict[str, Any]:
    validation = validate_review(value, active_run_id)
    if not validation["valid"]:
        raise ValueError("invalid critic review: " + "; ".join(validation["errors"]))
    stored = dict(value)
    stored.setdefault("reviewed_at", utc_now())
    path = root / "logs/critic_reviews" / f"{stored['id']}.json"
    if path.exists():
        raise ValueError(f"critic review already exists: {stored['id']}")
    atomic_write_json(path, stored)
    return {"critic_review": stored, "path": str(path)}


def load_review(root: Path, review_id: str) -> dict[str, Any]:
    if not REVIEW_ID.fullmatch(review_id):
        raise ValueError("invalid critic_review_id")
    path = root / "logs/critic_reviews" / f"{review_id}.json"
    value = read_json(path, None)
    if not isinstance(value, dict):
        raise ValueError(f"critic review not found: {review_id}")
    validation = validate_review(value)
    if not validation["valid"]:
        raise ValueError("stored critic review is invalid: " + "; ".join(validation["errors"]))
    return value


def require_reflection_review(root: Path, reflection: dict[str, Any]) -> dict[str, Any]:
    review_id = reflection.get("critic_review_id")
    if not isinstance(review_id, str) or not review_id.strip():
        raise ValueError("reflection requires critic_review_id")
    review = load_review(root, review_id)
    if review.get("run_id") != reflection.get("run_id"):
        raise ValueError("reflection and Critic Review must reference the same run_id")
    if review.get("status") not in APPROVED_STATUSES:
        raise ValueError("reflection requires an approved Critic Review")
    return review


def approved_reviews_for_run(root: Path, run_id: str) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    directory = root / "logs/critic_reviews"
    if not directory.is_dir():
        return reviews
    for path in sorted(directory.glob("*.json")):
        value = read_json(path, {})
        if isinstance(value, dict) and value.get("run_id") == run_id and value.get("status") in APPROVED_STATUSES and validate_review(value)["valid"]:
            reviews.append(value)
    return reviews
