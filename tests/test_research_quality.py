from pathlib import Path
import json
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.report_rubric import evaluate_report, load_rubric
from lib.research_design import validate_design


def evidence(card_id, group):
    return {"id": card_id, "source": {"publisher": group}, "independence_group": group, "prompt_injection_risk": "low"}


def test_research_design_validates_parallel_boundaries():
    design = json.loads((Path(__file__).parents[1] / "examples/evaluation/research-design.json").read_text())
    result = validate_design(design)
    assert result["valid"]
    assert result["parallel_groups"] == [["q-001"], ["q-002"]]
    design["questions"][1]["overlap_key"] = "primary-outcomes"
    assert not validate_design(design)["valid"]


def test_report_rubric_distinguishes_quality(tmp_path):
    rubric = load_rubric(SCRIPT_DIR.parent / "config/report_rubric.toml")
    cards = {"ev-1": evidence("ev-1", "origin-a"), "ev-2": evidence("ev-2", "origin-b")}
    good = tmp_path / "good.md"
    good.write_text("""# Report

## Executive conclusion
The evidence supports a limited conclusion, but the result remains sensitive to scope and measurement. [[ev-1]]

## Scope and method
The review covers the defined 2026 window and excludes anonymous speculation.

## Supported findings
The primary source reports a 20% outcome under its stated denominator and population. [[ev-1]]

## Conflicting or weakening evidence
An independent analysis identifies measurement limitations that weaken broad generalization and reduce confidence. [[ev-2]]

## Risks, uncertainty, and limitations
The result may not transfer to other populations, and inaccessible underlying records could materially change confidence. [[ev-1]][[ev-2]]

## Unresolved questions and next actions
Obtain the underlying records only if the decision depends on generalization.

## Sources
- [[ev-1]]
- [[ev-2]]
""", encoding="utf-8")
    result = evaluate_report(good, cards, rubric)
    assert result["passes_all_gates"]
    bad = tmp_path / "bad.md"; bad.write_text("# Report\n\n## Findings\nA 99% result proves universal success.\n", encoding="utf-8")
    assert not evaluate_report(bad, cards, rubric)["passes_all_gates"]
