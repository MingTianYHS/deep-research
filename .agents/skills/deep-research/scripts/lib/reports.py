from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import utc_now

SECTIONS = [
    "Executive conclusion",
    "Scope and assumptions",
    "Supported findings",
    "Conflicting or weakening evidence",
    "New information this run",
    "Risks and uncertainty",
    "Unresolved questions and next actions",
    "Sources",
]


def scaffold(path: Path, title: str, report_type: str, claims: dict[str, dict[str, Any]], since: str | None) -> None:
    lines = [f"# {title}", "", f"- Report type: {report_type}", f"- Generated: {utc_now()}", f"- Since: {since or 'initial baseline'}", "", "> Use `[[ev-ID]]` after each material statement. Only cite accepted evidence cards.", ""]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims.values():
        grouped.setdefault(claim.get("status", "draft"), []).append(claim)
    for section in SECTIONS:
        lines += [f"## {section}", ""]
        if section == "Supported findings":
            for claim in grouped.get("supported", []):
                citations = " ".join(f"[[{item['evidence_id']}]]" for item in claim.get("relations", []) if item.get("stance") == "support")
                lines.append(f"- {claim['text']} {citations}".rstrip())
        elif section == "Conflicting or weakening evidence":
            for status in ("contested", "rejected"):
                for claim in grouped.get(status, []):
                    citations = " ".join(f"[[{item['evidence_id']}]]" for item in claim.get("relations", []))
                    lines.append(f"- **{status}:** {claim['text']} {citations}".rstrip())
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
