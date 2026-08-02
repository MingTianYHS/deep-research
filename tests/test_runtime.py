import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.budget import BudgetExceeded, apply_delta, report
from lib.evidence import canonical_url, ingest_worker_result
from lib.tool_registry import load_registry, resolve, validate_registry


def worker_result():
    return {"run_id":"run-1","status":"complete","question_id":"q-001","overlap_key":"fact","budget_profile":"standard","coverage_status":"sufficient","queries_run":["q"],"source_clusters":[],"source_attempts":[{"id":"src-1","url":"https://example.com/a","normalized_url":"https://example.com/a","status":"accepted","eligible_for_evidence":True,"tool":"direct_fetch","access_mode":"public_static","content_sha256":"a"*64}],"evidence_cards":[{"source_attempt_id":"src-1","source":{"url":"https://example.com/a?utm_source=x","title":"A","publisher":"Example","source_type":"official"},"statement":"A fact","quote":"A fact","stance":"support","confidence":0.8,"independence_group":"origin-a","prompt_injection_risk":"low","version_compatibility":"not_applicable"}],"rejected_sources":[],"contradictions":[],"gaps":[],"suggested_followups":[],"budget_used":{"tool_calls":1,"search_queries":1,"source_pages":1,"duration_minutes":1,"same_url_attempts_max":1,"output_reserve_ratio":0.25,"estimated_input_tokens":1000,"estimated_output_tokens":200},"stop_reason":"acceptance_criteria_met"}


def test_budget_rejects_overspend():
    state={"usage":{"queries":7}}; profile={"max_queries":8,"max_pages":10,"max_evidence_cards":10,"estimated_input_tokens":100,"estimated_output_tokens":100}
    try: apply_delta(state,profile,{"queries":2}); assert False
    except BudgetExceeded: pass
    assert state["usage"]["queries"]==7


def test_budget_report():
    assert report({"usage":{"queries":2}}, {"max_queries":8,"max_pages":10,"max_evidence_cards":10,"estimated_input_tokens":100,"estimated_output_tokens":100})["remaining"]["queries"]==6


def test_canonical_url_removes_tracking(): assert canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2#top")=="https://example.com/a?b=2"


def test_ingest_binds_provenance_is_idempotent_and_returns_budget(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("")
    result=worker_result(); result["evidence_cards"].append(dict(result["evidence_cards"][0])); outcome=ingest_worker_result(path,result,max_new=3)
    assert outcome["accepted"]==1 and outcome["duplicates"]==1
    assert outcome["budget_delta"]["queries"]==1
    stored=json.loads(path.read_text().splitlines()[0]); assert stored["content_sha256"]=="a"*64
    again=ingest_worker_result(path,result,max_new=3); assert again["already_ingested"] and again["budget_delta"]=={}


def test_ingest_rejects_mismatched_source_url(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("")
    result=worker_result(); result["evidence_cards"][0]["source"]["url"]="https://other.example/b"
    try: ingest_worker_result(path,result,3); assert False
    except ValueError as exc: assert "does not match source attempt" in str(exc)


def test_ingest_rejects_legacy_worker(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("")
    try: ingest_worker_result(path,{"question_id":"q-1","evidence_cards":[]},3); assert False
    except ValueError as exc: assert "budget_profile" in str(exc)


def test_tool_registry_valid():
    registry=load_registry(SCRIPT_DIR.parent/"config/tools.toml"); assert validate_registry(registry)==[]; assert resolve(registry,"repo_read")[0]["name"]=="github_mcp"; assert resolve(registry,"authenticated_page")[0]["name"]=="web_access"
