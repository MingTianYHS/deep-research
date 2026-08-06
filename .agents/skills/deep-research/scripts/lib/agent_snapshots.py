from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .claims import materialize
from .io_utils import iter_jsonl, read_json

SNAPSHOT_VERSION = 1


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _workers(root: Path, run_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    directory = root / "logs/workers"
    if not directory.is_dir():
        return values
    for path in sorted(directory.glob("*.json")):
        value = read_json(path, {})
        if isinstance(value, dict) and value.get("run_id") == run_id:
            values.append(value)
    return sorted(
        values,
        key=lambda item: str(
            item.get("worker_result_id") or item.get("question_id") or ""
        ),
    )


def _evidence(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(item["id"]): item
        for _, item in iter_jsonl(root / "evidence/cards.jsonl")
        if item.get("id")
    }


def build_review_snapshot(root: Path, run_id: str) -> dict[str, Any]:
    design = read_json(root / "plans/current-design.json", {})
    workers = _workers(root, run_id)
    accepted_ids = sorted(
        {
            evidence_id
            for worker in workers
            for evidence_id in (worker.get("ingest_summary") or {}).get(
                "accepted_evidence_ids", []
            )
            if isinstance(evidence_id, str)
        }
    )
    evidence_map = _evidence(root)
    evidence = [evidence_map[item] for item in accepted_ids if item in evidence_map]
    claims = materialize(root / "claims.jsonl")
    run_claims = [
        claim
        for claim in claims.values()
        if any(
            isinstance(relation, dict)
            and relation.get("evidence_id") in accepted_ids
            for relation in claim.get("relations", [])
        )
    ]
    run_claims = sorted(run_claims, key=lambda item: str(item.get("id", "")))
    worker_ids = sorted(
        str(item.get("worker_result_id"))
        for item in workers
        if item.get("worker_result_id")
    )
    claim_ids = sorted(
        str(item.get("id")) for item in run_claims if item.get("id")
    )
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "run_id": run_id,
        "design_sha256": canonical_sha256(design),
        "worker_results_sha256": canonical_sha256(workers),
        "evidence_sha256": canonical_sha256(evidence),
        "claims_sha256": canonical_sha256(run_claims),
        "worker_result_ids": worker_ids,
        "evidence_ids": accepted_ids,
        "claim_ids": claim_ids,
    }


def snapshot_matches(stored: Any, current: dict[str, Any]) -> bool:
    if not isinstance(stored, dict):
        return False
    keys = (
        "snapshot_version",
        "run_id",
        "design_sha256",
        "worker_results_sha256",
        "evidence_sha256",
        "claims_sha256",
        "worker_result_ids",
        "evidence_ids",
        "claim_ids",
    )
    return all(stored.get(key) == current.get(key) for key in keys)
