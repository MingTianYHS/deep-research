import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import lib.workflow as workflow
from lib.workflow import derive_workflow


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def design() -> dict:
    return {
        "title": "测试主题",
        "decision_context": "支持测试决策",
        "scope": {
            "include": [],
            "exclude": [],
            "time_window": "",
            "geographies": [],
        },
        "questions": [
            {
                "id": "q-001",
                "status": "open",
                "question": "当前机制是否有效？",
                "type": "fact",
                "decision_relevance": "决定是否继续采用",
                "dependencies": [],
                "overlap_key": "mechanism",
                "preferred_source_types": ["official"],
                "acceptance_criteria": ["至少一个一手来源"],
                "disconfirming_query": "机制无效的证据",
                "alternative_explanations": [],
                "exclusions": [],
                "version_sensitive": False,
                "target_version": "",
                "target_commit": "",
                "allow_main_branch_fallback": False,
                "worker_budget_profile": "standard",
            }
        ],
    }


def topic(tmp_path: Path, *, active_run_id=None) -> Path:
    root = tmp_path / "测试主题"
    (root / "logs/workers").mkdir(parents=True)
    (root / "logs/critic_reviews").mkdir(parents=True)
    (root / "reports").mkdir(parents=True)
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    (root / "logs/runs.jsonl").write_text("", encoding="utf-8")
    write_json(
        root / "state.json",
        {
            "topic": "测试主题",
            "budget_profile": "standard",
            "active_run_id": active_run_id,
            "open_questions": ["q-001"],
        },
    )
    return root


def test_next_requests_canonical_design_when_missing(tmp_path):
    root = topic(tmp_path)
    result = derive_workflow(root, tmp_path / "skill")
    assert result["phase"] == "research_design"
    assert result["next_action"] == "create_research_design"
    assert result["requires_user_input"] is False


def test_next_starts_run_after_valid_design(tmp_path):
    root = topic(tmp_path)
    write_json(root / "plans/current-design.json", design())
    result = derive_workflow(root, tmp_path / "skill")
    assert result["phase"] == "ready_to_start"
    assert result["next_action"] == "start_run"


def test_next_delegates_ready_questions_to_named_researcher(tmp_path):
    root = topic(tmp_path, active_run_id="run-current")
    write_json(root / "plans/current-design.json", design())
    result = derive_workflow(root, tmp_path / "skill")
    assert result["phase"] == "worker_research"
    assert result["agent"] == "topic_researcher"
    assert result["assignments"][0]["question_id"] == "q-001"
    assert result["requires_user_input"] is False


def test_next_blocks_unsafe_reflection_without_critic(tmp_path):
    root = topic(tmp_path)
    write_json(root / "plans/current-design.json", design())
    (root / "logs/runs.jsonl").write_text(
        json.dumps(
            {
                "id": "run-finished",
                "status": "partial",
                "finished_at": "2026-08-06T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = derive_workflow(root, tmp_path / "skill")
    assert result["phase"] == "reflection_blocked"
    assert result["progress"]["run_id"] == "run-finished"


def test_next_initializes_audit_after_substantive_report(monkeypatch, tmp_path):
    root = topic(tmp_path, active_run_id="run-current")
    value = design()
    value["questions"][0]["status"] = "closed"
    write_json(root / "plans/current-design.json", value)
    monkeypatch.setattr(
        workflow,
        "approved_reviews_for_run",
        lambda _root, _run: [{"id": "critic-1", "status": "approved"}],
    )
    report = root / "reports/最终报告.md"
    report.write_text(
        "---\ntitle: 最终报告\nstatus: complete\n---\n\n## 核心结论\n\n已完成报告。",
        encoding="utf-8",
    )
    result = derive_workflow(root, tmp_path / "skill")
    assert result["phase"] == "report_audit"
    assert result["next_action"] == "initialize_quote_audit"
    assert str(report) in result["command"]
