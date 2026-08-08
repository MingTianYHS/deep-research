import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.claims import materialize
from lib.lean_claims import sync_run_claims


def setup(root: Path, cards: list[dict], accepted: list[str], run_id="run-1", question_id="q-1"):
    (root / "logs/workers").mkdir(parents=True, exist_ok=True); (root / "evidence").mkdir(exist_ok=True); (root / "claims.jsonl").write_text("", encoding="utf-8")
    worker = {"run_id": run_id, "question_id": question_id, "ingest_summary": {"accepted_evidence_ids": accepted}}
    (root / f"logs/workers/{run_id}.json").write_text(json.dumps(worker), encoding="utf-8"); (root / "evidence/cards.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in cards) + "\n", encoding="utf-8")


def test_sync_materializes_one_claim_per_question_and_is_idempotent(tmp_path):
    root = tmp_path / "topic"; cards = [{"id": "ev-1", "question_id": "q-1", "statement": "机制有效。", "stance": "support", "confidence": 0.8}, {"id": "ev-2", "question_id": "q-1", "statement": "效果受样本限制。", "stance": "contradict", "confidence": 0.7}]; setup(root, cards, ["ev-1", "ev-2"])
    first = sync_run_claims(root, "run-1"); second = sync_run_claims(root, "run-1"); claims = materialize(root / "claims.jsonl")
    assert first["claims_created"] == 1; assert first["relations_added"] == 2; assert second["claims_created"] == 0; assert second["relations_added"] == 0; assert len(claims) == 1
    claim = next(iter(claims.values())); assert claim["status"] == "contested"; assert {x["evidence_id"] for x in claim["relations"]} == {"ev-1", "ev-2"}


def test_later_support_does_not_erase_historical_contradiction(tmp_path):
    root = tmp_path / "topic"; cards = [{"id": "ev-1", "question_id": "q-1", "statement": "机制有效。", "stance": "support", "confidence": 0.8}, {"id": "ev-2", "question_id": "q-1", "statement": "机制无效。", "stance": "contradict", "confidence": 0.8}]; setup(root, cards, ["ev-1", "ev-2"]); sync_run_claims(root, "run-1")
    (root / "logs/workers/run-2.json").write_text(json.dumps({"run_id": "run-2", "question_id": "q-new", "ingest_summary": {"accepted_evidence_ids": ["ev-1"]}})); sync_run_claims(root, "run-2")
    assert next(iter(materialize(root / "claims.jsonl").values()))["status"] == "contested"


def test_context_only_evidence_does_not_create_supported_claim(tmp_path):
    root = tmp_path / "topic"; setup(root, [{"id": "ev-context", "question_id": "q-1", "statement": "背景信息", "stance": "context", "confidence": 0.8}], ["ev-context"])
    result = sync_run_claims(root, "run-1"); assert result["context_only_groups_skipped"] == 1; assert materialize(root / "claims.jsonl") == {}
