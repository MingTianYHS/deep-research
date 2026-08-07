from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import iter_jsonl, utc_now


def build_plan(
    state: dict[str, Any], claims: dict[str, dict[str, Any]], evidence_path: Path
) -> dict[str, Any]:
    known_urls = set()
    for _, card in iter_jsonl(evidence_path):
        source = card.get("source") or {}
        url = source.get("canonical_url") or source.get("url")
        if url:
            known_urls.add(url)
    priority_claims = [
        claim["id"]
        for claim in claims.values()
        if claim.get("status") in {"contested", "unresolved"} or claim.get("pending_transition")
    ]
    return {
        "type": "incremental",
        "created_at": utc_now(),
        "since": state.get("last_run_at"),
        "open_questions": state.get("open_questions", []),
        "priority_claims": priority_claims,
        "known_urls": sorted(known_urls),
        "instructions": [
            "Search only unresolved questions, priority claims, and material changes since the time anchor.",
            "Exclude known URLs unless verifying an update or contradiction.",
            "Stop after two low-yield queries or the configured budget limit.",
        ],
    }
