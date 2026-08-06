from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from .agent_snapshots import build_review_snapshot, canonical_sha256, snapshot_matches
from .critic_reviews import approved_reviews_for_run, load_review
from .io_utils import read_json
from .topic_context import build_brief
from .worker_contract import profile_limits

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
SYNTHESIS_STATUSES = {"complete", "partial", "blocked"}


def _dependency_results(
    root: Path, dependencies: list[str], run_id: str
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    directory = root / "logs/workers"
    if not directory.is_dir():
        return values
    for path in sorted(directory.glob("*.json")):
        worker = read_json(path, {})
        if (
            worker.get("run_id") == run_id
            and worker.get("question_id") in dependencies
            and worker.get("status") == "complete"
        ):
            values.append(
                {
                    "question_id": worker.get("question_id"),
                    "worker_result_id": worker.get("worker_result_id"),
                    "accepted_evidence_ids": (worker.get("ingest_summary") or {}).get(
                        "accepted_evidence_ids", []
                    ),
                    "coverage_status": worker.get("coverage_status"),
                }
            )
    return values


def build_researcher_assignment(
    root: Path,
    run_id: str,
    question: dict[str, Any],
    budgets_file: Path,
    remediation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    brief = build_brief(root, str(question.get("id")))
    profile = str(
        question.get("worker_budget_profile")
        or brief.get("budget_profile")
        or "standard"
    )
    limits = profile_limits(profile, budgets_file)
    dependencies = [str(item) for item in question.get("dependencies", [])]
    return {
        "assignment_version": 1,
        "agent": "topic_researcher",
        "search_policy_version": 1,
        "run_id": run_id,
        "question_id": question.get("id"),
        "question": question.get("question"),
        "question_type": question.get("type"),
        "decision_relevance": question.get("decision_relevance"),
        "scope": brief.get("scope", {}),
        "question_exclusions": question.get("exclusions", []),
        "overlap_key": question.get("overlap_key"),
        "dependencies": dependencies,
        "dependency_results": _dependency_results(root, dependencies, run_id),
        "preferred_source_types": question.get("preferred_source_types", []),
        "acceptance_criteria": question.get("acceptance_criteria", []),
        "disconfirming_query": question.get("disconfirming_query"),
        "alternative_explanations": question.get("alternative_explanations", []),
        "known_urls": brief.get("known_urls", []),
        "version_sensitive": bool(question.get("version_sensitive")),
        "target_version": question.get("target_version"),
        "target_commit": question.get("target_commit"),
        "allow_main_branch_fallback": bool(
            question.get("allow_main_branch_fallback", False)
        ),
        "budget_profile": profile,
        "budget": limits,
        "remediation": remediation,
        "inheritance_notice": (
            "Do not assume the parent Skill prompt is inherited. Follow the named "
            "agent instructions and this explicit assignment contract."
        ),
    }


def build_critic_assignment(
    root: Path, run_id: str, previous_review_id: str | None = None
) -> dict[str, Any]:
    return {
        "assignment_version": 1,
        "agent": "research_critic",
        "run_id": run_id,
        "review_snapshot": build_review_snapshot(root, run_id),
        "previous_review_id": previous_review_id,
        "inheritance_notice": (
            "Review only the supplied snapshot. Do not assume parent Skill context "
            "or silently inspect a different workspace state."
        ),
    }


def _topic_language(root: Path) -> str:
    try:
        with (root / "topic.toml").open("rb") as handle:
            return str(tomllib.load(handle).get("language") or "zh-CN")
    except (OSError, tomllib.TOMLDecodeError):
        return "zh-CN"


def build_synthesis_assignment(
    root: Path, run_id: str, report_path: Path
) -> dict[str, Any]:
    reviews = approved_reviews_for_run(root, run_id)
    if not reviews:
        raise ValueError("synthesis requires a current approved Critic Review")
    review = reviews[-1]
    review_snapshot = build_review_snapshot(root, run_id)
    synthesis_snapshot = {
        **review_snapshot,
        "critic_review_id": review["id"],
        "critic_review_sha256": canonical_sha256(review),
    }
    return {
        "assignment_version": 1,
        "agent": "research_synthesizer",
        "run_id": run_id,
        "critic_review_id": review["id"],
        "input_snapshot": synthesis_snapshot,
        "claim_ids": review_snapshot["claim_ids"],
        "evidence_ids": review_snapshot["evidence_ids"],
        "output_language": _topic_language(root),
        "report_path": str(report_path),
        "search_allowed": False,
        "inheritance_notice": (
            "Do not assume parent Skill search instructions are inherited. Synthesis "
            "is search-free; return blocked when Evidence is missing."
        ),
    }


def validate_synthesis_result(
    root: Path, value: dict[str, Any], active_run_id: str
) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("synthesis_result_version") != 1:
        errors.append("synthesis_result_version must be 1")
    synthesis_id = value.get("id")
    if not isinstance(synthesis_id, str) or not SAFE_ID.fullmatch(synthesis_id):
        errors.append("synthesis id must be a safe non-empty string")
    if value.get("run_id") != active_run_id:
        errors.append("synthesis run_id does not match active run")
    if value.get("status") not in SYNTHESIS_STATUSES:
        errors.append("invalid synthesis status")
    for key in ("claim_ids_used", "evidence_ids_used", "unresolved"):
        if not isinstance(value.get(key), list):
            errors.append(f"synthesis {key} must be a list")
    if not isinstance(value.get("report_markdown"), str) or not value.get(
        "report_markdown", ""
    ).strip():
        errors.append("synthesis report_markdown must be non-empty")
    report_path = value.get("report_path")
    if not isinstance(report_path, str) or not report_path.strip():
        errors.append("synthesis report_path must be non-empty")
    else:
        try:
            Path(report_path).expanduser().resolve().relative_to(
                (root / "reports").resolve()
            )
        except (OSError, ValueError):
            errors.append("synthesis report_path must stay inside topic reports")

    review_id = value.get("critic_review_id")
    review: dict[str, Any] | None = None
    if not isinstance(review_id, str) or not review_id:
        errors.append("synthesis critic_review_id is required")
    else:
        try:
            review = load_review(root, review_id)
        except ValueError as exc:
            errors.append(str(exc))
    current = build_review_snapshot(root, active_run_id)
    expected_snapshot: dict[str, Any] | None = None
    if review is not None:
        if review.get("run_id") != active_run_id:
            errors.append("synthesis Critic Review belongs to another run")
        if review.get("status") not in {"approved", "approved_with_findings"}:
            errors.append("synthesis requires an approved Critic Review")
        if not snapshot_matches(review.get("reviewed_snapshot"), current):
            errors.append("synthesis Critic Review is stale")
        expected_snapshot = {
            **current,
            "critic_review_id": review_id,
            "critic_review_sha256": canonical_sha256(review),
        }
    if expected_snapshot is not None and not snapshot_matches(
        value.get("input_snapshot"), expected_snapshot
    ):
        # snapshot_matches intentionally checks the shared review snapshot fields.
        errors.append("synthesis input snapshot does not match current reviewed state")
    if expected_snapshot is not None:
        supplied = value.get("input_snapshot")
        if not isinstance(supplied, dict) or supplied.get(
            "critic_review_sha256"
        ) != expected_snapshot.get("critic_review_sha256"):
            errors.append("synthesis critic review snapshot hash does not match")
    allowed_claims = set(current["claim_ids"])
    allowed_evidence = set(current["evidence_ids"])
    used_claims = set(value.get("claim_ids_used", [])) if isinstance(
        value.get("claim_ids_used"), list
    ) else set()
    used_evidence = set(value.get("evidence_ids_used", [])) if isinstance(
        value.get("evidence_ids_used"), list
    ) else set()
    if not used_claims <= allowed_claims:
        errors.append("synthesis used Claims outside the reviewed snapshot")
    if not used_evidence <= allowed_evidence:
        errors.append("synthesis used Evidence outside the reviewed snapshot")
    if value.get("status") == "complete" and (
        not used_claims or not used_evidence or value.get("unresolved")
    ):
        errors.append(
            "complete synthesis requires Claims, Evidence, and no unresolved items"
        )
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "current_snapshot": current,
    }
