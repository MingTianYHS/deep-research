import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.agent_contracts import (
    build_researcher_assignment,
    build_synthesis_assignment,
    validate_synthesis_result,
)
from lib.agent_snapshots import build_review_snapshot
from lib.claims import create, link
from lib.critic_reviews import approved_reviews_for_run, save_review


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def prepare_topic(tmp_path: Path) -> tuple[Path, dict, str]:
    root = tmp_path / "测试主题"
    for relative in (
        "plans",
        "logs/workers",
        "logs/critic_reviews",
        "reports",
        "evidence",
        "memory",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "topic.toml").write_text(
        'title = "测试主题"\nlanguage = "zh-CN"\n', encoding="utf-8"
    )
    write_json(
        root / "state.json",
        {
            "topic": "测试主题",
            "active_run_id": "run-1",
            "budget_profile": "standard",
            "baseline_completed": False,
            "open_questions": ["q-001"],
        },
    )
    question = {
        "id": "q-001",
        "status": "open",
        "question": "机制是否有效？",
        "type": "fact",
        "decision_relevance": "决定是否采用",
        "dependencies": [],
        "overlap_key": "mechanism",
        "preferred_source_types": ["official"],
        "acceptance_criteria": ["一条一手来源"],
        "disconfirming_query": "机制无效证据",
        "alternative_explanations": [],
        "exclusions": ["非中国市场"],
        "version_sensitive": False,
        "target_version": "",
        "target_commit": "",
        "allow_main_branch_fallback": False,
        "worker_budget_profile": "standard",
    }
    write_json(
        root / "plans/current-design.json",
        {
            "title": "测试主题",
            "decision_context": "测试",
            "scope": {
                "include": ["中国市场"],
                "exclude": ["海外市场"],
                "time_window": "2026",
                "geographies": ["中国"],
            },
            "questions": [question],
        },
    )
    card = {
        "id": "ev-1",
        "question_id": "q-001",
        "source": {
            "url": "https://example.com/report",
            "canonical_url": "https://example.com/report",
        },
        "statement": "机制有效。",
    }
    (root / "evidence/cards.jsonl").write_text(
        json.dumps(card, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    worker = {
        "worker_result_id": "worker-1",
        "run_id": "run-1",
        "question_id": "q-001",
        "status": "complete",
        "coverage_status": "sufficient",
        "ingest_summary": {"accepted_evidence_ids": ["ev-1"]},
    }
    write_json(root / "logs/workers/worker-1.json", worker)
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    (root / "memory/lessons.jsonl").write_text("", encoding="utf-8")
    claim = create(root / "claims.jsonl", "机制有效。", 0.8, True)
    link(root / "claims.jsonl", claim["id"], "ev-1", "support", 0.9)
    return root, question, claim["id"]


def approved_review(root: Path) -> dict:
    snapshot = build_review_snapshot(root, "run-1")
    return {
        "critic_review_version": 2,
        "id": "critic-1",
        "run_id": "run-1",
        "reviewed_by": "research_critic",
        "reviewed_snapshot": snapshot,
        "status": "approved",
        "findings": [],
        "targeted_searches": [],
        "unresolved": [],
        "stop_reason": "review_complete",
    }


def test_researcher_assignment_contains_explicit_search_context(tmp_path):
    root, question, _ = prepare_topic(tmp_path)
    assignment = build_researcher_assignment(
        root,
        "run-1",
        question,
        SCRIPT_DIR.parent / "config/budgets.toml",
    )
    assert assignment["assignment_version"] == 1
    assert assignment["scope"]["geographies"] == ["中国"]
    assert assignment["question_exclusions"] == ["非中国市场"]
    assert assignment["known_urls"] == ["https://example.com/report"]
    assert assignment["budget"]["max_same_url_attempts"] == 2
    assert "not assume" in assignment["inheritance_notice"]


def test_critic_approval_becomes_stale_after_design_change(tmp_path):
    root, _, _ = prepare_topic(tmp_path)
    save_review(root, approved_review(root), "run-1")
    assert len(approved_reviews_for_run(root, "run-1")) == 1
    design = json.loads(
        (root / "plans/current-design.json").read_text(encoding="utf-8")
    )
    design["decision_context"] = "changed after review"
    write_json(root / "plans/current-design.json", design)
    assert approved_reviews_for_run(root, "run-1") == []


def test_synthesis_result_is_bound_to_reviewed_snapshot(tmp_path):
    root, _, claim_id = prepare_topic(tmp_path)
    review = approved_review(root)
    save_review(root, review, "run-1")
    report = root / "reports/最终报告.md"
    report.write_text("待补充", encoding="utf-8")
    assignment = build_synthesis_assignment(root, "run-1", report)
    result = {
        "synthesis_result_version": 1,
        "id": "synthesis-1",
        "run_id": "run-1",
        "critic_review_id": "critic-1",
        "input_snapshot": assignment["input_snapshot"],
        "status": "complete",
        "report_path": str(report),
        "output_language": "zh-CN",
        "claim_ids_used": [claim_id],
        "evidence_ids_used": ["ev-1"],
        "unresolved": [],
        "report_markdown": "## 核心结论\n\n机制有效。[[ev-1]]",
    }
    checked = validate_synthesis_result(root, result, "run-1")
    assert checked["valid"], checked["errors"]
    result["evidence_ids_used"] = ["ev-invented"]
    checked = validate_synthesis_result(root, result, "run-1")
    assert not checked["valid"]
    assert any("outside" in error for error in checked["errors"])
