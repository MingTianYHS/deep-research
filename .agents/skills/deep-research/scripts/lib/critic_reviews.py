from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .agent_snapshots import build_review_snapshot, snapshot_matches
from .io_utils import atomic_write_json, read_json, utc_now

REVIEW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
APPROVED_STATUSES = {"approved", "approved_with_findings"}
REVIEW_STATUSES = APPROVED_STATUSES | {"changes_required"}
SEVERITIES = {"blocker", "high", "medium", "low", "info"}
TARGET_INTENTS = {
    "primary_source",
    "exact_verification",
    "citation_backtrack",
    "disconfirming",
    "version_check",
}


def validate_review(
    value: dict[str, Any],
    active_run_id: str | None = None,
    expected_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    version = value.get("critic_review_version", 1)
    if version not in {1, 2}:
        errors.append("critic_review_version must be 1 or 2")
    if expected_snapshot is not None and version != 2:
        errors.append("new Critic Reviews require critic_review_version 2")

    review_id = value.get("id")
    if not isinstance(review_id, str) or not REVIEW_ID.fullmatch(review_id):
        errors.append(
            "critic review id must be a safe non-empty string of at most 160 characters"
        )
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        errors.append("critic review run_id must be a non-empty string")
    elif active_run_id is not None and run_id != active_run_id:
        errors.append(
            f"critic review run_id {run_id} does not match active run {active_run_id}"
        )
    if value.get("reviewed_by") != "research_critic":
        errors.append("critic review reviewed_by must be research_critic")
    if value.get("status") not in REVIEW_STATUSES:
        errors.append(f"invalid critic review status: {value.get('status')}")
    for key in ("findings", "targeted_searches", "unresolved"):
        if not isinstance(value.get(key), list):
            errors.append(f"critic review {key} must be a list")

    reviewed_snapshot = value.get("reviewed_snapshot")
    if version == 2 and not isinstance(reviewed_snapshot, dict):
        errors.append("critic review v2 requires reviewed_snapshot")
    if expected_snapshot is not None and not snapshot_matches(
        reviewed_snapshot, expected_snapshot
    ):
        errors.append("critic reviewed_snapshot does not match current run state")

    findings = (
        value.get("findings", []) if isinstance(value.get("findings"), list) else []
    )
    finding_ids: set[str] = set()
    serious_ids: set[str] = set()
    for index, finding in enumerate(findings, 1):
        if not isinstance(finding, dict):
            errors.append(f"critic finding {index} must be an object")
            continue
        if version == 2:
            finding_id = finding.get("id")
            if (
                not isinstance(finding_id, str)
                or not REVIEW_ID.fullmatch(finding_id)
                or finding_id in finding_ids
            ):
                errors.append(f"critic finding {index} requires a unique safe id")
            else:
                finding_ids.add(finding_id)
                if finding.get("severity") in {"blocker", "high"}:
                    serious_ids.add(finding_id)
            if not isinstance(finding.get("evidence_ids"), list):
                errors.append(f"critic finding {index} evidence_ids must be a list")
            if not finding.get("claim_id") and not finding.get("question_id"):
                errors.append(
                    f"critic finding {index} requires claim_id or question_id"
                )
        if finding.get("severity") not in SEVERITIES:
            errors.append(f"critic finding {index} has invalid severity")
        for field in ("issue_type", "explanation", "required_action"):
            if not isinstance(finding.get(field), str) or not finding.get(
                field, ""
            ).strip():
                errors.append(f"critic finding {index} requires {field}")

    targeted = (
        value.get("targeted_searches", [])
        if isinstance(value.get("targeted_searches"), list)
        else []
    )
    if len(targeted) > 3:
        errors.append("critic targeted_searches allows at most 3 items")
    targeted_ids: set[str] = set()
    if version == 2:
        for index, item in enumerate(targeted, 1):
            if not isinstance(item, dict):
                errors.append(f"targeted search {index} must be an object")
                continue
            search_id = item.get("id")
            if (
                not isinstance(search_id, str)
                or not REVIEW_ID.fullmatch(search_id)
                or search_id in targeted_ids
            ):
                errors.append(f"targeted search {index} requires a unique safe id")
            else:
                targeted_ids.add(search_id)
            if item.get("finding_id") not in serious_ids:
                errors.append(
                    f"targeted search {index} must reference a blocker/high finding"
                )
            for field in (
                "question_id",
                "query",
                "required_evidence",
                "stop_condition",
            ):
                if not isinstance(item.get(field), str) or not item.get(
                    field, ""
                ).strip():
                    errors.append(f"targeted search {index} requires {field}")
            if item.get("intent") not in TARGET_INTENTS:
                errors.append(f"targeted search {index} has invalid intent")

    unresolved = (
        value.get("unresolved", [])
        if isinstance(value.get("unresolved"), list)
        else []
    )
    if value.get("status") in APPROVED_STATUSES:
        serious = [
            item
            for item in findings
            if isinstance(item, dict)
            and item.get("severity") in {"blocker", "high"}
        ]
        if serious or unresolved:
            errors.append(
                "approved critic review cannot contain blocker/high findings or unresolved items"
            )
    if value.get("status") == "changes_required" and not findings and not unresolved:
        errors.append("changes_required requires findings or unresolved items")
    if not isinstance(value.get("stop_reason"), str) or not value.get(
        "stop_reason", ""
    ).strip():
        errors.append("critic review requires stop_reason")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "critic_review_version": version,
    }


def save_review(
    root: Path, value: dict[str, Any], active_run_id: str
) -> dict[str, Any]:
    expected = build_review_snapshot(root, active_run_id)
    validation = validate_review(value, active_run_id, expected)
    if not validation["valid"]:
        raise ValueError(
            "invalid critic review: " + "; ".join(validation["errors"])
        )
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
        raise ValueError(
            "stored critic review is invalid: " + "; ".join(validation["errors"])
        )
    return value


def reviews_for_run(root: Path, run_id: str) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    directory = root / "logs/critic_reviews"
    if not directory.is_dir():
        return reviews
    for path in sorted(directory.glob("*.json")):
        value = read_json(path, {})
        if (
            isinstance(value, dict)
            and value.get("run_id") == run_id
            and validate_review(value)["valid"]
        ):
            reviews.append(value)
    return sorted(
        reviews,
        key=lambda item: str(item.get("reviewed_at") or item.get("id") or ""),
    )


def latest_review_for_run(root: Path, run_id: str) -> dict[str, Any] | None:
    reviews = reviews_for_run(root, run_id)
    return reviews[-1] if reviews else None


def review_is_current(root: Path, review: dict[str, Any], run_id: str) -> bool:
    return snapshot_matches(
        review.get("reviewed_snapshot"), build_review_snapshot(root, run_id)
    )


def require_reflection_review(
    root: Path, reflection: dict[str, Any]
) -> dict[str, Any]:
    review_id = reflection.get("critic_review_id")
    if not isinstance(review_id, str) or not review_id.strip():
        raise ValueError("reflection requires critic_review_id")
    review = load_review(root, review_id)
    if review.get("run_id") != reflection.get("run_id"):
        raise ValueError(
            "reflection and Critic Review must reference the same run_id"
        )
    if review.get("status") not in APPROVED_STATUSES:
        raise ValueError("reflection requires an approved Critic Review")
    return review


def approved_reviews_for_run(
    root: Path, run_id: str, current_only: bool = True
) -> list[dict[str, Any]]:
    reviews = [
        value
        for value in reviews_for_run(root, run_id)
        if value.get("status") in APPROVED_STATUSES
    ]
    if current_only:
        current = build_review_snapshot(root, run_id)
        reviews = [
            value
            for value in reviews
            if snapshot_matches(value.get("reviewed_snapshot"), current)
        ]
    return reviews
