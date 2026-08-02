from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .citations import CITATION_RE
from .io_utils import atomic_write_json, read_json, utc_now

ALLOWED_STATUSES = {"pending", "verified", "failed", "unavailable"}
MATCH_TYPES = {"exact", "normalized", "semantic", "locator_only"}


def file_sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def create_audit(report_path: Path, evidence: dict[str, dict[str, Any]], output: Path) -> dict[str, Any]:
    report_text = report_path.read_text(encoding="utf-8"); cited = list(dict.fromkeys(CITATION_RE.findall(report_text))); items = []
    for evidence_id in cited:
        card = evidence.get(evidence_id)
        if not card: items.append({"evidence_id": evidence_id, "status": "failed", "reason": "missing evidence card"}); continue
        source = card.get("source") or {}
        items.append({"evidence_id": evidence_id, "status": "pending", "url": source.get("url"), "source_attempt_id": card.get("source_attempt_id"), "content_sha256": None, "statement": card.get("statement"), "expected_quote": card.get("quote"), "locator": card.get("locator"), "match_type": None, "checked_at": None, "checked_by": None, "observed_text": None, "reason": "", "instructions": "Fetch with a read-only route (web-access for authorized login/anti-bot pages), compare the observed text and locator, record the accepted source attempt/hash, then set status."})
    audit = {"report": str(report_path), "report_sha256": file_sha256(report_path), "created_at": utc_now(), "items": items}; atomic_write_json(output, audit); return audit


def validate_audit(path: Path, require_all_verified: bool = False) -> dict[str, Any]:
    audit = read_json(path, {}); errors, counts = [], {status: 0 for status in ALLOWED_STATUSES}; report = Path(audit.get("report", ""))
    if not report.exists(): errors.append("audited report no longer exists")
    elif audit.get("report_sha256") != file_sha256(report): errors.append("report changed after audit creation; create a new audit")
    for index, item in enumerate(audit.get("items", []), 1):
        status = item.get("status")
        if status not in ALLOWED_STATUSES: errors.append(f"item {index}: invalid status {status}"); continue
        counts[status] += 1
        if status == "verified":
            for field in ("checked_at", "checked_by", "observed_text", "source_attempt_id", "content_sha256", "match_type"):
                if not item.get(field): errors.append(f"item {index}: verified item requires {field}")
            if item.get("match_type") not in MATCH_TYPES: errors.append(f"item {index}: invalid match_type")
        if status in {"failed", "unavailable"} and not item.get("reason"): errors.append(f"item {index}: {status} item requires reason")
    if require_all_verified and any(counts[status] for status in ("pending", "failed", "unavailable")): errors.append("final audit requires every citation to be verified")
    return {"audit": str(path), "counts": counts, "errors": errors, "valid": not errors}
