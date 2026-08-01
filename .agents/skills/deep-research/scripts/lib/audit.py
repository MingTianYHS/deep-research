from __future__ import annotations

from pathlib import Path
from typing import Any

from .citations import CITATION_RE
from .io_utils import atomic_write_json, read_json, utc_now

ALLOWED_STATUSES = {"pending", "verified", "failed", "unavailable"}


def create_audit(report_path: Path, evidence: dict[str, dict[str, Any]], output: Path) -> dict[str, Any]:
    cited = list(dict.fromkeys(CITATION_RE.findall(report_path.read_text(encoding="utf-8"))))
    items = []
    for evidence_id in cited:
        card = evidence.get(evidence_id)
        if not card:
            items.append({"evidence_id": evidence_id, "status": "failed", "reason": "missing evidence card"})
            continue
        source = card.get("source") or {}
        items.append({
            "evidence_id": evidence_id,
            "status": "pending",
            "url": source.get("url"),
            "statement": card.get("statement"),
            "expected_quote": card.get("quote"),
            "locator": card.get("locator"),
            "checked_at": None,
            "checked_by": None,
            "observed_text": None,
            "reason": "",
            "instructions": "Fetch the source with an available read-only tool, navigate to the locator, compare the expected quote and meaning, then set status to verified, failed, or unavailable.",
        })
    audit = {"report": str(report_path), "created_at": utc_now(), "items": items}
    atomic_write_json(output, audit)
    return audit


def validate_audit(path: Path, require_all_verified: bool = False) -> dict[str, Any]:
    audit = read_json(path, {})
    errors, counts = [], {status: 0 for status in ALLOWED_STATUSES}
    for index, item in enumerate(audit.get("items", []), 1):
        status = item.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"item {index}: invalid status {status}")
            continue
        counts[status] += 1
        if status == "verified" and (not item.get("checked_at") or not item.get("checked_by")):
            errors.append(f"item {index}: verified item requires checked_at and checked_by")
        if status in {"failed", "unavailable"} and not item.get("reason"):
            errors.append(f"item {index}: {status} item requires reason")
    if require_all_verified and any(counts[status] for status in ("pending", "failed", "unavailable")):
        errors.append("final audit requires every citation to be verified")
    return {"audit": str(path), "counts": counts, "errors": errors, "valid": not errors}
