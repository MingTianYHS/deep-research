from __future__ import annotations

import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from .io_utils import append_jsonl, iter_jsonl, utc_now

STATUSES = {"draft", "supported", "contested", "rejected", "unresolved"}
STANCES = {"support", "contradict", "context"}


def materialize(path: Path) -> dict[str, dict[str, Any]]:
    claims: dict[str, dict[str, Any]] = {}
    for _, event in iter_jsonl(path):
        event_type = event.get("type")
        claim_id = event.get("claim_id")
        if event_type == "claim.created":
            claim = deepcopy(event["claim"])
            claims[claim["id"]] = claim
        elif claim_id in claims and event_type == "claim.relation.added":
            relation = deepcopy(event["relation"])
            relations = [item for item in claims[claim_id].setdefault("relations", []) if item.get("evidence_id") != relation["evidence_id"]]
            relations.append(relation)
            claims[claim_id]["relations"] = relations
            claims[claim_id]["updated_at"] = event["at"]
        elif claim_id in claims and event_type == "claim.transition.proposed":
            claims[claim_id]["pending_transition"] = {"to": event["to"], "reason": event.get("reason", ""), "proposed_at": event["at"]}
        elif claim_id in claims and event_type == "claim.status.changed":
            claims[claim_id]["status"] = event["to"]
            claims[claim_id]["updated_at"] = event["at"]
            claims[claim_id].pop("pending_transition", None)
    return claims


def create(path: Path, text: str, confidence: float, is_core: bool) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("claim text must not be empty")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("claim confidence must be between 0 and 1")
    now = utc_now()
    claim = {"id": f"cl-{uuid.uuid4().hex[:12]}", "text": text.strip(), "status": "draft", "confidence": confidence, "is_core": is_core, "relations": [], "created_at": now, "updated_at": now}
    append_jsonl(path, [{"type": "claim.created", "claim_id": claim["id"], "claim": claim, "at": now}])
    return claim


def link(path: Path, claim_id: str, evidence_id: str, stance: str, strength: float) -> dict[str, Any]:
    if claim_id not in materialize(path):
        raise ValueError(f"unknown claim: {claim_id}")
    if stance not in STANCES:
        raise ValueError(f"invalid relation stance: {stance}")
    if not 0.0 <= strength <= 1.0:
        raise ValueError("relation strength must be between 0 and 1")
    event = {"type": "claim.relation.added", "claim_id": claim_id, "relation": {"evidence_id": evidence_id, "stance": stance, "strength": strength}, "at": utc_now()}
    append_jsonl(path, [event])
    return event


def _require_support(claim: dict[str, Any], evidence_ids: set[str] | None) -> None:
    support = [item for item in claim.get("relations", []) if item.get("stance") == "support"]
    if not support:
        raise ValueError("supported claim requires at least one support evidence relation")
    if evidence_ids is not None:
        missing = sorted(item.get("evidence_id") for item in support if item.get("evidence_id") not in evidence_ids)
        if missing:
            raise ValueError(f"supported claim references unknown evidence: {missing}")


def change_status(path: Path, claim_id: str, target: str, reason: str, approve_core: bool, evidence_ids: set[str] | None = None) -> dict[str, Any]:
    claim = materialize(path).get(claim_id)
    if not claim:
        raise ValueError(f"unknown claim: {claim_id}")
    if target not in STATUSES:
        raise ValueError(f"invalid claim status: {target}")
    if claim["status"] == target:
        return {"type": "claim.status.noop", "claim_id": claim_id, "to": target}
    if target == "supported":
        _require_support(claim, evidence_ids)
    if claim.get("is_core"):
        if approve_core:
            pending = claim.get("pending_transition")
            if not pending or pending.get("to") != target:
                raise ValueError("core claim approval requires a matching pending transition")
            event_type = "claim.status.changed"
        else:
            event_type = "claim.transition.proposed"
    else:
        event_type = "claim.status.changed"
    event = {"type": event_type, "claim_id": claim_id, "from": claim["status"], "to": target, "reason": reason, "at": utc_now()}
    append_jsonl(path, [event])
    return event


def validate_events(path: Path, evidence_ids: set[str]) -> list[str]:
    errors: list[str] = []
    known: set[str] = set()
    try:
        for number, event in iter_jsonl(path):
            event_type, claim_id = event.get("type"), event.get("claim_id")
            if event_type == "claim.created":
                claim = event.get("claim", {})
                if not claim.get("id") or not claim.get("text"):
                    errors.append(f"line {number}: invalid claim.created")
                else:
                    known.add(claim["id"])
            elif claim_id not in known:
                errors.append(f"line {number}: event references unknown claim {claim_id}")
            if event_type == "claim.relation.added":
                evidence_id = event.get("relation", {}).get("evidence_id")
                if evidence_id not in evidence_ids:
                    errors.append(f"line {number}: unknown evidence {evidence_id}")
        for claim_id, claim in materialize(path).items():
            if claim.get("status") == "supported":
                try:
                    _require_support(claim, evidence_ids)
                except ValueError as exc:
                    errors.append(f"claim {claim_id}: {exc}")
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
    return errors
