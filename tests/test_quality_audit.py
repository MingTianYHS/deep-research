from datetime import date
from pathlib import Path
import sys,json
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts"; sys.path.insert(0,str(SCRIPT_DIR))
from lib.audit import create_audit,validate_audit
from lib.io_utils import atomic_write_json
from lib.quality import evaluate,freshness_score,load_policy
POLICY=SCRIPT_DIR.parent/"config/source_policy.toml"

def card(evidence_id="ev-1",source_type="official",published_at="2026-07-25"):
    return {"id":evidence_id,"question_id":"q-1","source_attempt_id":"src-1","source":{"url":"https://example.com","publisher":"Example","source_type":source_type,"published_at":published_at},"statement":"Fact","quote":"Exact quote","locator":"Section 1","stance":"support","independence_group":"example","prompt_injection_risk":"low"}

def attempt(): return {"id":"src-1","status":"accepted","eligible_for_evidence":True,"content_sha256":"a"*64}

def test_freshness_is_source_type_specific(): assert freshness_score("paper","2026-07-25",load_policy(POLICY),date(2026,8,1))>freshness_score("news","2026-07-25",load_policy(POLICY),date(2026,8,1))

def test_quality_report_is_transparent_and_bounded():
    result=evaluate([card()],load_policy(POLICY),date(2026,8,1)); assert result["primary_source_ratio"]==1.0
    invalid=card("ev-2"); invalid["quality"]={"authority":2.0}
    try: evaluate([invalid],load_policy(POLICY),date(2026,8,1)); assert False
    except ValueError: pass

def test_audit_requires_frozen_source_identity_and_real_quote_match(tmp_path):
    report=tmp_path/"report.md"; report.write_text("Fact [[ev-1]]"); output=tmp_path/"audit.json"; create_audit(report,{"ev-1":card()},output,{"src-1":attempt()})
    audit=json.loads(output.read_text()); item=audit["items"][0];assert item["expected_source_attempt_id"]=="src-1" and item["expected_content_sha256"]=="a"*64
    item.update(status="verified",checked_at="2026-08-01T00:00:00Z",checked_by="research_critic",observed_text="Wrong quote",content_sha256="a"*64,match_type="exact"); atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
    item.update(observed_text="Exact quote",checked_at="not-a-date");atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
    item.update(checked_at="2026-08-01T00:00:00Z",checked_by="any-string");atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
    item.update(checked_by="research_critic");atomic_write_json(output,audit);assert validate_audit(output,True)["valid"]
    item.update(match_type="semantic");atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
    item.update(match_type="normalized",observed_text="  Exact   quote ");atomic_write_json(output,audit);assert validate_audit(output,True)["valid"]
    item.update(source_attempt_id="src-other");atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
    report.write_text("Changed [[ev-1]]"); assert not validate_audit(output,True)["valid"]
