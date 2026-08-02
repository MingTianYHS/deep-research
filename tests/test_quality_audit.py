from datetime import date
from pathlib import Path
import sys,json
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
from lib.audit import create_audit,validate_audit
from lib.io_utils import atomic_write_json
from lib.quality import evaluate,freshness_score,load_policy
POLICY=SCRIPT_DIR.parent/"config/source_policy.toml"
def card(evidence_id="ev-1",source_type="official",published_at="2026-07-25"):
 return {"id":evidence_id,"question_id":"q-1","source_attempt_id":"src-1","source":{"url":"https://example.com","publisher":"Example","source_type":source_type,"published_at":published_at},"statement":"Fact","quote":"Exact quote","locator":"Section 1","stance":"support","independence_group":"example","prompt_injection_risk":"low","content_sha256":"a"*64}
def test_freshness_is_source_type_specific():assert freshness_score("paper","2026-07-25",load_policy(POLICY),date(2026,8,1))>freshness_score("news","2026-07-25",load_policy(POLICY),date(2026,8,1))
def test_quality_report_is_transparent_and_bounded():
 result=evaluate([card()],load_policy(POLICY),date(2026,8,1));assert result["primary_source_ratio"]==1.0
 invalid=card("ev-2");invalid["quality"]={"authority":2.0}
 try:evaluate([invalid],load_policy(POLICY),date(2026,8,1));assert False
 except ValueError:pass
def test_audit_requires_observed_source_proof(tmp_path):
 report=tmp_path/"report.md";report.write_text("Fact [[ev-1]]");output=tmp_path/"audit.json";create_audit(report,{"ev-1":card()},output);audit=json.loads(output.read_text());audit["items"][0].update(status="verified",checked_at="2026-08-01T00:00:00Z",checked_by="codex/reviewer");atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
 audit["items"][0].update(observed_text="Exact quote",source_attempt_id="src-1",content_sha256="a"*64,match_type="exact");atomic_write_json(output,audit);assert validate_audit(output,True)["valid"]
 audit["items"][0]["source_attempt_id"]="src-other";atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
 audit["items"][0]["source_attempt_id"]="src-1";audit["items"][0]["content_sha256"]="b"*64;atomic_write_json(output,audit);assert not validate_audit(output,True)["valid"]
 audit["items"][0]["content_sha256"]="a"*64;atomic_write_json(output,audit);report.write_text("Changed [[ev-1]]");assert not validate_audit(output,True)["valid"]
