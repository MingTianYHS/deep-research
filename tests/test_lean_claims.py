import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.claims import materialize
from lib.lean_claims import sync_run_claims


def test_sync_materializes_one_claim_per_question_and_is_idempotent(tmp_path):
    root = tmp_path / "topic"
    (root / "logs/workers").mkdir(parents=True)
    (root / "evidence").mkdir()
    (root / "claims.jsonl").write_text("", encoding="utf-8")
    worker = {"run_id": "run-1", "ingest_summary": {"accepted_evidence_ids": ["ev-1", "ev-2"]}}
    (root / "logs/workers/w.json").write_text(json.dumps(worker), encoding="utf-8")
    cards = [
        {"id": "ev-1", "question_id": "q-1", "statement": "机制有效。", "stance": "support", "confidence": 0.8},
        {"id": "ev-2", "question_id": "q-1", "statement": "效果受样本限制。", "stance": "contradict", "confidence": 0.7},
    ]
    (root / "evidence/cards.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in cards) + "\n", encoding="utf-8")
    first = sync_run_claims(root, "run-1")
    second = sync_run_claims(root, "run-1")
    claims = materialize(root / "claims.jsonl")
    assert first["claims_created"] == 1
    assert first["relations_added"] == 2
    assert second["claims_created"] == 0
    assert second["relations_added"] == 0
    assert len(claims) == 1
    claim = next(iter(claims.values()))
    assert claim["status"] == "contested"
    assert {x["evidence_id"] for x in claim["relations"]} == {"ev-1", "ev-2"}
