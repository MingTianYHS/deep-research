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
    (root / "evidence").mkdir(parents=True)
    (root / "evidence/cards.jsonl").write_text("", encoding="utf-8")
    (root / "memory").mkdir(parents=True)
    (root / "memory/lessons.jsonl").write_text("", encoding="utf-8")
    (root / "topic.toml").write_text(
        'title = "测试主题"\nlanguage = "zh-CN"\n', encoding="utf-8"
    )
    write_json(
        root / "state.json",
        {
            "topic": "测试主题",
            "budget_profile": "standard",
            "active_run_id": active_run_id,
            "baseline_completed": False,
            "open_questions": ["q-001"],
        },
    )
    return root


def test_next_requests_canonical_design_when_missing(tmp_path):
    root = topic(tmp_path)
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "research_design"
    assert result["next_action"] == "create_research_design"
    assert result["requires_user_input"] is False


def test_next_starts_run_after_valid_design(tmp_path):
    root = topic(tmp_path)
    write_json(root / "plans/current-design.json", design())
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "ready_to_start"
    assert result["next_action"] == "start_run"


def test_next_delegates_complete_assignment_to_named_researcher(tmp_path):
    root = topic(tmp_path, active_run_id="run-current")
    write_json(root / "plans/current-design.json", design())
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "worker_research"
    assert result["agent"] == "topic_researcher"
    assignment = result["assignments"][0]
    assert assignment["question_id"] == "q-001"
    assert assignment["assignment_version"] == 1
    assert assignment["budget"]["max_search_queries"] == 6
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
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "reflection_blocked"
    assert result["progress"]["run_id"] == "run-finished"


def prepare_completed_worker(root: Path):
    write_json(
        root / "logs/workers/worker-current.json",
        {
            "worker_result_id": "worker-current",
            "run_id": "run-current",
            "question_id": "q-001",
            "status": "complete",
            "coverage_status": "sufficient",
            "ingest_summary": {"accepted_evidence_ids": ["ev-current"]},
        },
    )


def patch_claim_and_approval(monkeypatch):
    monkeypatch.setattr(
        workflow,
        "materialize",
        lambda _path: {
            "claim-current": {
                "id": "claim-current",
                "relations": [
                    {"evidence_id": "ev-current", "stance": "support"}
                ],
            }
        },
    )
    monkeypatch.setattr(
        workflow,
        "approved_reviews_for_run",
        lambda _root, _run, current_only=True: [
            {
                "id": "critic-1",
                "status": "approved",
                "reviewed_snapshot": {},
            }
        ],
    )


def test_next_initializes_audit_only_for_report_citing_current_run(
    monkeypatch, tmp_path
):
    root = topic(tmp_path, active_run_id="run-current")
    write_json(root / "plans/current-design.json", design())
    prepare_completed_worker(root)
    patch_claim_and_approval(monkeypatch)
    report = root / "reports/最终报告.md"
    report.write_text(
        "---\ntitle: 最终报告\nstatus: complete\n---\n\n"
        "## 核心结论\n\n本轮证据支持该结论。[[ev-current]]",
        encoding="utf-8",
    )
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "report_audit"
    assert result["next_action"] == "initialize_quote_audit"
    assert str(report) in result["command"]
    assert result["progress"]["current_run_citations"] == ["ev-current"]


def test_next_routes_historical_report_to_new_scaffold(monkeypatch, tmp_path):
    root = topic(tmp_path, active_run_id="run-current")
    write_json(root / "plans/current-design.json", design())
    prepare_completed_worker(root)
    patch_claim_and_approval(monkeypatch)
    (root / "logs/runs.jsonl").write_text(
        json.dumps(
            {
                "id": "run-current",
                "status": "running",
                "started_at": "2999-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "reports/历史报告.md").write_text(
        "---\ntitle: 历史报告\nstatus: complete\n---\n\n"
        "## 核心结论\n\n历史结论。[[ev-historical]]",
        encoding="utf-8",
    )
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "synthesis"
    assert result["next_action"] == "create_report_scaffold"


def test_next_routes_current_changes_required_to_targeted_research(
    monkeypatch, tmp_path
):
    root = topic(tmp_path, active_run_id="run-current")
    write_json(root / "plans/current-design.json", design())
    prepare_completed_worker(root)
    monkeypatch.setattr(
        workflow,
        "materialize",
        lambda _path: {
            "claim-current": {
                "id": "claim-current",
                "relations": [{"evidence_id": "ev-current"}],
            }
        },
    )
    monkeypatch.setattr(
        workflow, "approved_reviews_for_run", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        workflow,
        "latest_review_for_run",
        lambda *_args: {
            "id": "critic-1",
            "status": "changes_required",
            "findings": [],
            "targeted_searches": [
                {
                    "id": "targeted-1",
                    "finding_id": "finding-1",
                    "question_id": "q-001",
                    "query": "site:example.gov primary filing",
                    "intent": "primary_source",
                    "required_evidence": "Primary filing",
                    "stop_condition": "Found or official archive exhausted",
                }
            ],
        },
    )
    monkeypatch.setattr(workflow, "review_is_current", lambda *_args: True)
    result = derive_workflow(root, SCRIPT_DIR.parent)
    assert result["phase"] == "critic_remediation"
    assert result["agent"] == "topic_researcher"
    assert result["assignments"][0]["remediation"]["finding_id"] == "finding-1"
