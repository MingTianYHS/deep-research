from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import utc_now

SECTIONS = ["Executive conclusion", "Scope and method", "Findings by research question", "Conflicting or weakening evidence", "Implications", "Risks, uncertainty, and limitations", "Unresolved questions and next actions", "Sources", "Core claim–evidence table"]


def refs(claim: dict[str, Any], stance: str | None = None) -> str:
    return " ".join(f"[[{item['evidence_id']}]]" for item in claim.get("relations", []) if stance is None or item.get("stance") == stance)


def scaffold(path: Path, title: str, report_type: str, claims: dict[str, dict[str, Any]], since: str | None) -> None:
    lines = [f"# {title}", "", f"- Report type: {report_type}", f"- Generated: {utc_now()}", f"- Evidence cut-off / since: {since or 'initial baseline'}", "", "> Cite every material factual paragraph with `[[ev-ID]]`. Label inference, causal interpretation, forecast, and recommendation. Preserve dates, units, denominators, population, and geography.", ""]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims.values(): grouped.setdefault(claim.get("status", "draft"), []).append(claim)
    for section in SECTIONS:
        lines += [f"## {section}", ""]
        if section == "Findings by research question":
            for claim in grouped.get("supported", []): lines.append(f"- **Observed fact or supported interpretation:** {claim['text']} {refs(claim, 'support')}".rstrip())
        elif section == "Conflicting or weakening evidence":
            for status in ("contested", "rejected", "unresolved"):
                for claim in grouped.get(status, []): lines.append(f"- **{status}:** {claim['text']} {refs(claim)}".rstrip())
        elif section == "Core claim–evidence table":
            lines += ["| Claim | Epistemic type | Status | Supporting evidence | Contradicting evidence | Confidence / caveat |", "|---|---|---|---|---|---|"]
            for claim in claims.values():
                if claim.get("is_core"):
                    support = refs(claim, "support") or "—"; contradict = refs(claim, "contradict") or "—"
                    lines.append(f"| {claim['text']} | TODO | {claim.get('status', 'draft')} | {support} | {contradict} | {claim.get('confidence', 'TODO')} / TODO |")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(lines), encoding="utf-8")
