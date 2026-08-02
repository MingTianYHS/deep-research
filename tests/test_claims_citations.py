from pathlib import Path
import sys
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts"; sys.path.insert(0,str(SCRIPT_DIR))
from lib.claims import change_status,create,link,materialize
from lib.citations import verify_report
from lib.incremental import build_plan
from lib.io_utils import append_jsonl
from lib.reports import scaffold

def sample_card(evidence_id="ev-1"):
    return {"id":evidence_id,"question_id":"q-001","source_attempt_id":"src-1","source":{"url":"https://example.com","canonical_url":"https://example.com"},"statement":"Fact","quote":"Exact quote","stance":"support","confidence":0.8}

def test_core_claim_requires_support_and_two_step_approval(tmp_path):
    path=tmp_path/"claims.jsonl"; claim=create(path,"Core claim",0.7,True)
    try: change_status(path,claim["id"],"supported","direct",False); assert False
    except ValueError as exc: assert "support evidence" in str(exc)
    link(path,claim["id"],"ev-1","support",0.9)
    assert change_status(path,claim["id"],"supported","evidence",False)["type"]=="claim.transition.proposed"; assert change_status(path,claim["id"],"supported","reviewed",True,{"ev-1"})["type"]=="claim.status.changed"

def test_claim_link_and_noncore_status(tmp_path):
    path=tmp_path/"claims.jsonl"; claim=create(path,"Claim",0.7,False); link(path,claim["id"],"ev-1","support",0.9); change_status(path,claim["id"],"supported","verified",False,{"ev-1"}); assert materialize(path)[claim["id"]]["status"]=="supported"

def test_citation_verification_and_zero_citation_failure(tmp_path):
    report=tmp_path/"report.md"; report.write_text("A fact [[ev-1]] and missing [[ev-404]].",encoding="utf-8"); result=verify_report(report,{"ev-1":sample_card()}); assert result["missing_evidence"]==["ev-404"] and not result["valid"]
    report.write_text("No citations.",encoding="utf-8"); assert not verify_report(report,{"ev-1":sample_card()})["valid"]

def test_incremental_plan_uses_state_claims_and_known_urls(tmp_path):
    cards=tmp_path/"cards.jsonl"; append_jsonl(cards,[sample_card()]); plan=build_plan({"last_run_at":"2026-08-01T00:00:00Z","open_questions":["q-2"]},{"cl-1":{"id":"cl-1","status":"contested"}},cards); assert plan["priority_claims"]==["cl-1"]

def test_report_scaffold_includes_evidence_marker(tmp_path):
    report=tmp_path/"r.md"; scaffold(report,"Research report","initial",{"cl-1":{"id":"cl-1","text":"Supported","status":"supported","relations":[{"evidence_id":"ev-1","stance":"support"}]}},None); assert "[[ev-1]]" in report.read_text(encoding="utf-8")
