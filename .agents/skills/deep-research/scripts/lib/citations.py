from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CITATION_RE = re.compile(r"\[\[(ev-[A-Za-z0-9_-]+)\]\]")


def verify_report(report_path: Path, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    text = report_path.read_text(encoding="utf-8")
    cited = list(dict.fromkeys(CITATION_RE.findall(text)))
    missing = [item for item in cited if item not in evidence]
    incomplete = []
    for evidence_id in cited:
        card = evidence.get(evidence_id)
        if not card:
            continue
        source = card.get("source") or {}
        if not source.get("url") or not card.get("statement") or not (card.get("quote") or card.get("locator")):
            incomplete.append(evidence_id)
    return {
        "report": str(report_path),
        "citation_count": len(cited),
        "cited_evidence": cited,
        "missing_evidence": missing,
        "incomplete_evidence": incomplete,
        "valid": not missing and not incomplete,
    }
