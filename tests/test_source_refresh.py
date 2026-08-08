import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.evidence import ingest_worker_result, iter_jsonl
from lib.research_memory import build_reuse_plan
from tests.test_runtime import prepare_topic, worker_result


def test_known_url_refresh_updates_freshness_without_duplicate_evidence(tmp_path):
    cards = tmp_path / "topic/evidence/cards.jsonl"; cards.parent.mkdir(parents=True); cards.write_text(""); prepare_topic(cards)
    first = worker_result(); initial = ingest_worker_result(cards, first, 3); evidence_id = initial["accepted_ids"][0]
    state_path = tmp_path / "topic/state.json"; state = json.loads(state_path.read_text()); state["active_run_id"] = "run-2"; state["active_run_scope"] = {"run_id": "run-2", "assigned_question_ids": ["q-001"]}; state_path.write_text(json.dumps(state))
    refreshed = worker_result(); refreshed.update(worker_result_id="worker-2", run_id="run-2", queries_run=[]); refreshed["source_attempts"][0].update(id="src-2", query_id=None, discovery_method="known_url"); refreshed["evidence_cards"][0]["source_attempt_id"] = "src-2"; refreshed["budget_used"] = {"tool_calls": 1, "search_queries": 0, "source_pages": 1}
    outcome = ingest_worker_result(cards, refreshed, 3)
    assert outcome["accepted"] == 0; assert outcome["verified_ids"] == [evidence_id]; assert outcome["accepted_ids"] == [evidence_id]
    assert sum(1 for _ in iter_jsonl(cards)) == 1; assert sum(1 for _ in iter_jsonl(tmp_path / "topic/evidence/verifications.jsonl")) == 1
    plan = build_reuse_plan(tmp_path / "topic", "q-001")
    assert plan["existing_evidence"][0]["freshness"] == "fresh"; assert plan["known_sources"][0]["latest_source_attempt_id"] == "src-2"
