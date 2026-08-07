import json
import sys
from pathlib import Path

SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts"; sys.path.insert(0,str(SCRIPT_DIR))
from lib.research_design import template,validate_design
from lib.rollout_audit import audit_rollout
from lib.runtime_preflight import REQUIRED_SKILL_FILES,diagnose
from lib.source_attempts import assess_response,build_attempt,may_attempt
from lib.worker_contract import profile_limits,validate_worker_result


def make_user_install(tmp_path:Path):
    skill=tmp_path/".agents/skills/deep-research"
    for relative in REQUIRED_SKILL_FILES:
        path=skill/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text("x",encoding="utf-8")
    agents=tmp_path/".codex/agents"; agents.mkdir(parents=True)
    values={"topic-researcher.toml":"topic_researcher","research-critic.toml":"research_critic","research-synthesizer.toml":"research_synthesizer"}
    for filename,name in values.items(): (agents/filename).write_text(f'name="{name}"\ndescription="x"\nsandbox_mode="read-only"\ndeveloper_instructions="x"\n',encoding="utf-8")
    workspace=tmp_path/"研究工作区"; workspace.mkdir(); return skill,workspace


def test_user_level_preflight_passes(tmp_path):
    skill,workspace=make_user_install(tmp_path); result=diagnose(skill,workspace,home=tmp_path,python_version=(3,11)); assert result["valid"]; assert result["warning_count"]==1


def test_invalid_agent_toml_is_rejected(tmp_path):
    skill,workspace=make_user_install(tmp_path); (tmp_path/".codex/agents/topic-researcher.toml").write_text("x")
    assert not diagnose(skill,workspace,home=tmp_path,python_version=(3,11))["valid"]


def test_version_sensitive_design_requires_version_or_commit():
    design=template("Codex"); design["questions"][0]["version_sensitive"]=True; assert not validate_design(design)["valid"]; design["questions"][0]["target_version"]="0.146.0"; assert validate_design(design)["valid"]


def valid_worker():
    return {
        "worker_result_version":2,"status":"complete","question_id":"q-001","overlap_key":"x","budget_profile":"standard","coverage_status":"sufficient",
        "queries_run":[{"id":"query-1","query":"site:example.com fact","intent":"primary_source","provider":"native_web","language":"en","time_anchor":None,"fallback_of":None,"outcome":"primary_candidate_found"}],
        "source_attempts":[{"id":"src-1","url":"https://example.com","normalized_url":"https://example.com/","status":"accepted","eligible_for_evidence":True,"tool":"direct_fetch","access_mode":"public_static","content_sha256":"a"*64,"query_id":"query-1","discovery_method":"search","discovered_via_source_attempt_id":None}],
        "evidence_cards":[{"id":"ev-1","statement":"Fact","quote":"Fact","stance":"support","confidence":0.8,"independence_group":"origin","source_attempt_id":"src-1","prompt_injection_risk":"low","version_compatibility":"not_applicable","source":{"url":"https://example.com","title":"Fact","publisher":"Example","source_type":"official"}}],
        "gaps":[],"budget_used":{"tool_calls":2,"search_queries":1,"source_pages":1},"stop_reason":"acceptance_criteria_met"
    }


def test_worker_contract_enforces_compact_observable_budget():
    result=valid_worker(); assert validate_worker_result(result,profile_limits("standard"))["valid"]
    result["budget_used"]["search_queries"]=7
    assert not validate_worker_result(result,profile_limits("standard"))["valid"]


def test_http_error_page_is_not_evidence(): assert not assess_response(200,"<title>404: Not Found</title>")["eligible_for_evidence"]


def test_source_attempt_limit_and_reuse(tmp_path):
    log=tmp_path/"a.jsonl"; attempt=build_attempt("https://example.com/doc?utm_source=x","docs",200,"valid"); log.write_text(json.dumps(attempt)+"\n"); assert may_attempt(log,"https://example.com/doc")["reason"]=="already_accepted"


def write_rollout(path,agent_path,final_message):
    rows=[{"type":"session_meta","payload":{"thread_source":"subagent","source":{"subagent":{"thread_spawn":{"agent_path":agent_path,"agent_role":None}}}}},{"type":"response_item","payload":{"type":"function_call","name":"search","call_id":"1","arguments":"{}"}},{"type":"response_item","payload":{"type":"function_call_output","call_id":"1","output":"ok"}},{"type":"event_msg","payload":{"type":"task_complete","last_agent_message":final_message}}]; path.write_text("\n".join(json.dumps(x) for x in rows)+"\n")


def test_rollout_gates(tmp_path):
    bad=tmp_path/"bad"; write_rollout(bad,None,None); assert not audit_rollout(bad)["passes_all_gates"]
    good=tmp_path/"good"; write_rollout(good,"topic-researcher.toml","result"); assert audit_rollout(good)["passes_all_gates"]
