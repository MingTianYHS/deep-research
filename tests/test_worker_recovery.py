import json
import sys
from pathlib import Path
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
import lib.evidence as evidence
from tests.test_runtime import prepare_topic,worker_result


def test_worker_ingest_recovers_pending_transaction(monkeypatch,tmp_path):
    cards=tmp_path/"topic/evidence/cards.jsonl";cards.parent.mkdir(parents=True);cards.write_text("");prepare_topic(cards)
    original=evidence._append_missing;calls={"count":0}
    def fail_once(path,records,key="id"):
        calls["count"]+=1
        if calls["count"]==2: raise OSError("simulated crash")
        return original(path,records,key)
    monkeypatch.setattr(evidence,"_append_missing",fail_once)
    try:evidence.ingest_worker_result(cards,worker_result(),3);assert False
    except OSError:pass
    pending=tmp_path/"topic/logs/workers/.worker-1.pending.json";assert pending.exists()
    monkeypatch.setattr(evidence,"_append_missing",original)
    outcome=evidence.ingest_worker_result(cards,worker_result(),3)
    assert outcome["recovered_transaction"] and outcome["accepted"]==1
    assert not pending.exists()
    assert sum(1 for _ in evidence.iter_jsonl(cards))==1
    assert sum(1 for _ in evidence.iter_jsonl(tmp_path/"topic/logs/source_attempts.jsonl"))==1
    logged=json.loads((tmp_path/"topic/logs/workers/worker-1.json").read_text());assert logged["ingest_summary"]["accepted_evidence_ids"]
