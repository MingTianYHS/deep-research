import json
import sys
from copy import deepcopy
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.budget import BudgetExceeded, apply_delta, report
from lib.evidence import canonical_url, ingest_worker_result
from lib.tool_registry import load_registry, resolve, validate_registry


def worker_result():
    return {"worker_result_version":2,"worker_result_id":"worker-1","run_id":"run-1","status":"complete","question_id":"q-001","overlap_key":"fact","budget_profile":"standard","coverage_status":"sufficient","queries_run":[{"id":"query-1","query":"site:example.com fact","intent":"primary_source","provider":"native_web","language":"en","time_anchor":None,"fallback_of":None,"outcome":"primary_candidate_found"},{"id":"query-2","query":"example fact limitations","intent":"disconfirming","provider":"native_web","language":"en","time_anchor":None,"fallback_of":None,"outcome":"candidate_found"}],"source_clusters":[],"source_attempts":[{"id":"src-1","url":"https://example.com/a","normalized_url":"https://example.com/a","status":"accepted","eligible_for_evidence":True,"tool":"direct_fetch","access_mode":"public_static","content_sha256":"a"*64,"query_id":"query-1","discovery_method":"search","discovered_via_source_attempt_id":None}],"evidence_cards":[{"source_attempt_id":"src-1","source":{"url":"https://example.com/a?utm_source=x","title":"A","publisher":"Example","source_type":"official"},"statement":"A fact","quote":"A fact","stance":"support","confidence":0.8,"independence_group":"origin-a","prompt_injection_risk":"low","version_compatibility":"not_applicable"}],"rejected_sources":[],"contradictions":[],"gaps":[],"suggested_followups":[],"budget_used":{"tool_calls":2,"search_queries":2,"source_pages":1,"duration_minutes":1,"same_url_attempts_max":1,"output_reserve_ratio":0.25},"stop_reason":"acceptance_criteria_met"}


def prepare_topic(path):
    topic=path.parent.parent;(topic/"plans").mkdir(parents=True,exist_ok=True);(topic/"logs/workers").mkdir(parents=True,exist_ok=True)
    (topic/"state.json").write_text(json.dumps({"workspace_format_version":3,"active_run_id":"run-1","active_run_scope":{"run_id":"run-1","assigned_question_ids":["q-001"]},"budget_profile":"standard"}),encoding="utf-8")
    (topic/"plans/current-design.json").write_text(json.dumps({"questions":[{"id":"q-001","status":"open","overlap_key":"fact","worker_budget_profile":"standard","version_sensitive":False}]}),encoding="utf-8")


def test_budget_rejects_overspend():
    state={"usage":{"queries":7}}; profile={"max_queries":8,"max_pages":10,"max_evidence_cards":10,"estimated_input_tokens":100,"estimated_output_tokens":100}
    try: apply_delta(state,profile,{"queries":2}); assert False
    except BudgetExceeded: pass
    assert state["usage"]["queries"]==7


def test_budget_report(): assert report({"usage":{"queries":2}}, {"max_queries":8,"max_pages":10,"max_evidence_cards":10,"estimated_input_tokens":100,"estimated_output_tokens":100})["remaining"]["queries"]==6
def test_canonical_url_removes_tracking(): assert canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2#top")=="https://example.com/a?b=2"


def test_ingest_worker_deduplicates_and_persists_source_attempts(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("");prepare_topic(path)
    result=worker_result(); result["evidence_cards"].append(dict(result["evidence_cards"][0])); outcome=ingest_worker_result(path,result,max_new=3)
    assert outcome["accepted"]==1 and outcome["duplicates"]==1; assert (tmp_path/"topic/logs/source_attempts.jsonl").exists(); assert Path(outcome["worker_result_log"]).exists(); assert outcome["ingest_context_validation"]["active_run_id"]=="run-1"


def test_ingest_rejects_legacy_worker(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("");prepare_topic(path); result=worker_result();result.pop("worker_result_version")
    try: ingest_worker_result(path,result,3); assert False
    except ValueError as exc: assert "worker_result_version" in str(exc)


def test_ingest_rejects_wrong_run_or_design_boundary(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("");prepare_topic(path); result=worker_result();result["run_id"]="run-other";result["overlap_key"]="other"
    try: ingest_worker_result(path,result,3); assert False
    except ValueError as exc: message=str(exc);assert "active run" in message and "overlap_key" in message


def test_ingest_rejects_duplicate_worker_result_id(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("");prepare_topic(path); ingest_worker_result(path,worker_result(),3)
    try: ingest_worker_result(path,worker_result(),3); assert False
    except ValueError as exc: assert "already ingested" in str(exc)


def test_version_sensitive_question_requires_full_target_anchor(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl"; path.parent.mkdir(parents=True); path.write_text("");prepare_topic(path)
    design=json.loads((tmp_path/"topic/plans/current-design.json").read_text(encoding="utf-8"));design["questions"][0].update(version_sensitive=True,target_version="v1.2.3");(tmp_path/"topic/plans/current-design.json").write_text(json.dumps(design),encoding="utf-8")
    result=worker_result();result["queries_run"].append({"id":"query-3","query":"example v1.2.3 release","intent":"version_check","provider":"native_web","language":"en","time_anchor":"v","fallback_of":None,"outcome":"candidate_found"});result["budget_used"]["tool_calls"]=3;result["budget_used"]["search_queries"]=3
    try: ingest_worker_result(path,result,3); assert False
    except ValueError as exc: assert "matching version_check query anchor" in str(exc)
    result["queries_run"][-1]["time_anchor"]="release v1.2.3";outcome=ingest_worker_result(path,result,3);assert outcome["accepted"]==1


def test_tool_registry_valid_and_honors_default_orders():
    registry=load_registry(SCRIPT_DIR.parent/"config/tools.toml"); assert validate_registry(registry)==[]; assert [item["name"] for item in resolve(registry,"web_search")]==["native_web","tavily","exa"]; assert resolve(registry,"repo_read")[0]["name"]=="github_mcp"; assert [item["name"] for item in resolve(registry,"authenticated_page")]==["web_access","browser"]; assert registry["tools"]["firecrawl"]["enabled"]; assert "firecrawl" not in registry["defaults"]["search_order"]; assert registry["defaults"]["free_quota_only"]; assert not registry["defaults"]["allow_paid_overage"]


def test_tool_registry_rejects_paid_overage_and_duplicate_order():
    registry=load_registry(SCRIPT_DIR.parent/"config/tools.toml"); invalid=deepcopy(registry); invalid["defaults"]["allow_paid_overage"]=True; invalid["defaults"]["search_order"].append("native_web"); errors=validate_registry(invalid); assert "free_quota_only cannot allow paid overage" in errors; assert "defaults.search_order must not contain duplicates" in errors
