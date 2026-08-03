import json
import sys
from pathlib import Path
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
import lib.evidence as evidence
from tests.test_runtime import prepare_topic,worker_result


def cards_path(tmp_path):
    path=tmp_path/"topic/evidence/cards.jsonl";path.parent.mkdir(parents=True);path.write_text("");prepare_topic(path);return path


def rejected(path,result,text):
    try:evidence.ingest_worker_result(path,result,3);assert False
    except ValueError as exc:assert text in str(exc)


def test_ingest_binds_attempt_url_hash_and_evidence_url(tmp_path):
    path=cards_path(tmp_path);result=worker_result();result["source_attempts"][0]["content_sha256"]="fake";rejected(path,result,"content_sha256")
    result=worker_result();result["source_attempts"][0]["normalized_url"]="https://example.org/wrong";rejected(path,result,"normalized_url")
    result=worker_result();result["evidence_cards"][0]["source"]["url"]="https://attacker.example/report";rejected(path,result,"does not match its Source Attempt")


def test_ingest_budget_counts_are_structurally_observed(tmp_path):
    path=cards_path(tmp_path);result=worker_result();result["budget_used"]["search_queries"]=0;rejected(path,result,"search_queries")
    result=worker_result();result["budget_used"]["source_pages"]=0;rejected(path,result,"source_pages")


def test_pending_recovery_revalidates_active_run(tmp_path,monkeypatch):
    path=cards_path(tmp_path);result=worker_result();original=evidence._append_missing;calls={"count":0}
    def fail_once(target,records,key="id"):
        calls["count"]+=1
        if calls["count"]==2:raise OSError("simulated crash")
        return original(target,records,key)
    monkeypatch.setattr(evidence,"_append_missing",fail_once)
    try:evidence.ingest_worker_result(path,result,3);assert False
    except OSError:pass
    state=json.loads((tmp_path/"topic/state.json").read_text());state["active_run_id"]="run-other";(tmp_path/"topic/state.json").write_text(json.dumps(state))
    monkeypatch.setattr(evidence,"_append_missing",original);rejected(path,result,"does not match active run")
