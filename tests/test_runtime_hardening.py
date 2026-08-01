import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.research_design import template, validate_design
from lib.rollout_audit import audit_rollout
from lib.runtime_preflight import diagnose
from lib.source_attempts import assess_response, build_attempt, may_attempt
from lib.worker_contract import profile_limits, validate_worker_result


def make_user_install(tmp_path: Path):
    skill = tmp_path / ".agents/skills/deep-research"
    for relative in ("SKILL.md", "config/budgets.toml", "scripts/researchctl.py", "scripts/runtimectl.py"):
        path = skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    agents = tmp_path / ".codex/agents"
    agents.mkdir(parents=True)
    for name in ("topic-researcher.toml", "research-critic.toml", "research-synthesizer.toml"):
        (agents / name).write_text("x", encoding="utf-8")
    workspace = tmp_path / "研究工作区"
    workspace.mkdir()
    return skill, workspace


def test_user_level_preflight_passes(tmp_path):
    skill, workspace = make_user_install(tmp_path)
    result = diagnose(skill, workspace, home=tmp_path, python_version=(3, 11))
    assert result["valid"]
    assert result["installation_mode"] == "user-level"


def test_project_layout_is_rejected(tmp_path):
    _, workspace = make_user_install(tmp_path)
    project_skill = tmp_path / "project/.agents/skills/deep-research"
    project_skill.mkdir(parents=True)
    result = diagnose(project_skill, workspace, home=tmp_path, python_version=(3, 11))
    assert not result["valid"]
    assert any(item["code"] == "skill_not_user_level" for item in result["checks"])


def test_version_sensitive_design_requires_version_or_commit():
    design = template("Codex config behavior")
    design["questions"][0]["version_sensitive"] = True
    result = validate_design(design)
    assert not result["valid"]
    design["questions"][0]["target_version"] = "0.146.0"
    assert validate_design(design)["valid"]


def valid_worker():
    return {"status": "complete", "question_id": "q-001", "overlap_key": "runtime-config", "coverage_status": "sufficient", "queries_run": [], "source_clusters": [], "evidence_cards": [], "rejected_sources": [], "contradictions": [], "gaps": [], "suggested_followups": [], "budget_used": {"tool_calls": 4, "search_queries": 2, "source_pages": 3, "duration_minutes": 2, "same_url_attempts_max": 1}, "stop_reason": "acceptance_criteria_met"}


def test_worker_contract_enforces_budget_and_final_shape():
    result = valid_worker()
    assert validate_worker_result(result, profile_limits("standard"))["valid"]
    result["budget_used"]["tool_calls"] = 99
    outcome = validate_worker_result(result, profile_limits("standard"))
    assert not outcome["valid"]
    assert any("exceeds" in error for error in outcome["errors"])


def test_http_error_page_is_not_evidence():
    assert not assess_response(200, "<title>404: Not Found</title>")["eligible_for_evidence"]
    assert assess_response(200, "Substantive official documentation")["eligible_for_evidence"]


def test_source_attempt_limit_and_reuse(tmp_path):
    log = tmp_path / "attempts.jsonl"
    attempt = build_attempt("https://example.com/doc?utm_source=x", "docs", 200, "valid content", source_version="v1")
    log.write_text(json.dumps(attempt) + "\n", encoding="utf-8")
    result = may_attempt(log, "https://example.com/doc")
    assert not result["allowed"]
    assert result["reason"] == "already_accepted"


def write_rollout(path: Path, *, agent_path, final_message):
    rows = [
        {"type": "session_meta", "payload": {"thread_source": "subagent", "cwd": "C:/research", "source": {"subagent": {"thread_spawn": {"agent_path": agent_path, "agent_role": None}}}}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "search", "call_id": "1", "arguments": "{\"url\":\"https://example.com\"}"}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "1", "output": "ok"}},
        {"type": "event_msg", "payload": {"type": "task_complete", "last_agent_message": final_message}},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_rollout_audit_detects_generic_empty_worker(tmp_path):
    path = tmp_path / "bad.jsonl"; write_rollout(path, agent_path=None, final_message=None)
    result = audit_rollout(path)
    assert not result["passes_all_gates"]
    assert not result["gates"]["custom_agent"]
    assert not result["gates"]["final_message"]


def test_rollout_audit_accepts_custom_worker_with_final(tmp_path):
    path = tmp_path / "good.jsonl"; write_rollout(path, agent_path="topic-researcher.toml", final_message="structured result")
    assert audit_rollout(path)["passes_all_gates"]
