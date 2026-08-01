from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from .citations import CITATION_RE

HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?%?|\$\d[\d,.]*)")


def load_rubric(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle: return tomllib.load(handle)


def section_map(text: str, aliases: dict[str, list[str]]) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(text)); sections = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip().lower(); body = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip()
        for key, values in aliases.items():
            if key not in sections and any(value.lower() in title for value in values): sections[key] = body
    return sections


def material_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for part in re.split(r"\n\s*\n", text):
        value = re.sub(r"^[-*]\s+", "", part.strip())
        if not value or value.startswith("#") or value.startswith("|") or len(value) < 50: continue
        paragraphs.append(value)
    return paragraphs


def evaluate_report(report: Path, evidence: dict[str, dict[str, Any]], rubric: dict[str, Any]) -> dict[str, Any]:
    text = report.read_text(encoding="utf-8"); cited = list(dict.fromkeys(CITATION_RE.findall(text)))
    sections = section_map(text, rubric["section_aliases"]); required = rubric["sections"]["required"]
    paragraphs = material_paragraphs(text); numeric = [item for item in paragraphs if NUMBER_RE.search(item)]
    cited_paragraphs = [item for item in paragraphs if CITATION_RE.search(item)]; cited_numeric = [item for item in numeric if CITATION_RE.search(item)]
    invalid = [item for item in cited if item not in evidence]
    accepted = [evidence[item] for item in cited if item in evidence]
    groups = {card.get("independence_group") or card.get("source", {}).get("publisher") or card["id"] for card in accepted}
    high_risk = [card["id"] for card in accepted if card.get("prompt_injection_risk") == "high"]
    metrics = {
        "required_sections": sum(1 for key in required if key in sections) / len(required),
        "citation_coverage": len(cited_paragraphs) / len(paragraphs) if paragraphs else 0.0,
        "numeric_citation_coverage": len(cited_numeric) / len(numeric) if numeric else 1.0,
        "source_independence": min(1.0, len(groups) / max(1, int(rubric["gates"]["minimum_independence_groups"]))),
        "conflict_treatment": 1.0 if len(sections.get("conflict", "")) >= 60 else 0.0,
        "uncertainty_treatment": 1.0 if len(sections.get("uncertainty", "")) >= 60 else 0.0,
        "citation_validity": 1.0 if not invalid else 0.0,
    }
    score = sum(metrics[key] * float(weight) for key, weight in rubric["weights"].items())
    gates = rubric["gates"]
    gate_results = {
        "minimum_score": score >= float(gates["minimum_score"]),
        "minimum_citation_coverage": metrics["citation_coverage"] >= float(gates["minimum_citation_coverage"]),
        "minimum_numeric_citation_coverage": metrics["numeric_citation_coverage"] >= float(gates["minimum_numeric_citation_coverage"]),
        "minimum_independence_groups": len(groups) >= int(gates["minimum_independence_groups"]),
        "maximum_invalid_citations": len(invalid) <= int(gates["maximum_invalid_citations"]),
        "maximum_high_risk_citations": len(high_risk) <= int(gates["maximum_high_risk_citations"]),
    }
    return {"report": str(report), "score": round(score, 4), "passes_all_gates": all(gate_results.values()), "gates": gate_results, "metrics": {key: round(value, 4) for key, value in metrics.items()}, "missing_sections": [key for key in required if key not in sections], "material_paragraphs": len(paragraphs), "numeric_paragraphs": len(numeric), "cited_evidence": cited, "invalid_citations": invalid, "independence_groups": len(groups), "high_risk_citations": high_risk, "limitations": ["Mechanical rubric only; it does not prove factual correctness, causal validity, or quote fidelity."]}
