from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.claims import change_status, create, link, materialize
from lib.citations import verify_report
from lib.incremental import build_plan
from lib.io_utils import append_jsonl
from lib.reports import scaffold


def sample_card(evidence_id="ev-1"):
    return {"id": evidence_id, "question_id": "q-001", "source": {"url": "https://example.com", "canonical_url": "https://example.com"}, "statement": "Fact", "quote": "Exact quote", "stance": "support", "confidence": 0.8}


def test_core_claim_requires_transition_approval(tmp_path):
    path = tmp_path / "claims.jsonl"
    claim = create(path, "Core claim", 0.7, True)
    event = change_status(path, claim["id"], "supported", "evidence", False)
    assert event["type"] == "claim.transition.proposed"
    current = materialize(path)[claim["id"]]
    assert current["status"] == "draft"
    assert current["pending_transition"]["to"] == "supported"


def test_claim_link_and_approved_status(tmp_path):
    path = tmp_path / "claims.jsonl"
    claim = create(path, "Claim", 0.7, False)
    link(path, claim["id"], "ev-1", "support", 0.9)
    change_status(path, claim["id"], "supported", "verified", False)
    current = materialize(path)[claim["id"]]
    assert current["status"] == "supported"
    assert current["relations"][0]["evidence_id"] == "ev-1"


def test_citation_verification(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("A fact [[ev-1]] and missing [[ev-404]].", encoding="utf-8")
    result = verify_report(report, {"ev-1": sample_card()})
    assert result["missing_evidence"] == ["ev-404"]
    assert not result["valid"]


def test_incremental_plan_uses_state_claims_and_known_urls(tmp_path):
    cards = tmp_path / "cards.jsonl"
    append_jsonl(cards, [sample_card()])
    plan = build_plan({"last_run_at": "2026-08-01T00:00:00Z", "open_questions": ["q-2"]}, {"cl-1": {"id": "cl-1", "status": "contested"}}, cards)
    assert plan["since"] == "2026-08-01T00:00:00Z"
    assert plan["priority_claims"] == ["cl-1"]
    assert plan["known_urls"] == ["https://example.com"]


def test_report_scaffold_includes_evidence_marker(tmp_path):
    report = tmp_path / "report.md"
    claims = {"cl-1": {"id": "cl-1", "text": "Supported claim", "status": "supported", "relations": [{"evidence_id": "ev-1", "stance": "support", "strength": 0.8}]}}
    scaffold(report, "Research report", "initial", claims, None)
    assert "[[ev-1]]" in report.read_text(encoding="utf-8")
