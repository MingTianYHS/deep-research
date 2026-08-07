from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .claims import change_status, create, link, materialize
from .io_utils import iter_jsonl, read_json


def _workers(root: Path, run_id: str) -> list[dict[str, Any]]:
    values = []
    for path in sorted((root / "logs/workers").glob("*.json")):
        value = read_json(path, {})
        if isinstance(value, dict) and value.get("run_id") == run_id:
            values.append(value)
    return values


def sync_run_claims(root: Path, run_id: str) -> dict[str, Any]:
    """Materialize one compact Claim per question from accepted run Evidence.

    This is the lite/standard fast path. It replaces repeated coordinator
    claim-create/link/status calls with one deterministic, idempotent command.
    Deep runs retain manual Claim review.
    """
    accepted = {
        evidence_id
        for worker in _workers(root, run_id)
        for evidence_id in (worker.get("ingest_summary") or {}).get("accepted_evidence_ids", [])
        if isinstance(evidence_id, str)
    }
    cards = {
        str(card["id"]): card
        for _, card in iter_jsonl(root / "evidence/cards.jsonl")
        if card.get("id") in accepted
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in cards.values():
        grouped[str(card.get("question_id") or "unscoped")].append(card)

    path = root / "claims.jsonl"
    claims = materialize(path)
    relation_owner = {
        str(relation.get("evidence_id")): claim_id
        for claim_id, claim in claims.items()
        for relation in claim.get("relations", [])
        if isinstance(relation, dict) and relation.get("evidence_id")
    }
    created_ids: list[str] = []
    linked = 0
    for question_id, group in sorted(grouped.items()):
        claim_id = next((relation_owner.get(str(card["id"])) for card in group if relation_owner.get(str(card["id"]))), None)
        if not claim_id:
            lead = next((card for card in group if card.get("stance", "support") == "support"), group[0])
            text = str(lead.get("statement") or "").strip()
            if not text:
                continue
            raw_confidence = lead.get("confidence", 0.7)
            confidence = float(raw_confidence) if isinstance(raw_confidence, (int, float)) else 0.7
            claim = create(path, text, max(0.0, min(1.0, confidence)), False)
            claim_id = claim["id"]
            created_ids.append(claim_id)
        current = materialize(path).get(claim_id, {})
        existing = {str(item.get("evidence_id")) for item in current.get("relations", []) if isinstance(item, dict)}
        has_contradiction = False
        for card in group:
            evidence_id = str(card["id"])
            stance = str(card.get("stance") or "support")
            if stance not in {"support", "contradict", "context"}:
                stance = "context"
            has_contradiction = has_contradiction or stance == "contradict"
            if evidence_id not in existing:
                link(path, claim_id, evidence_id, stance, 0.8)
                linked += 1
        target = "contested" if has_contradiction else "supported"
        change_status(path, claim_id, target, f"automatic lean claim sync for {question_id}", False)

    return {
        "run_id": run_id,
        "accepted_evidence": len(accepted),
        "questions_grouped": len(grouped),
        "claims_created": len(created_ids),
        "claim_ids_created": created_ids,
        "relations_added": linked,
        "mode": "deterministic_question_claims",
    }
