from pathlib import Path
import json
import sys
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
import lib.completion as completion


def test_completion_quality_is_scoped_to_active_run_snapshot(monkeypatch,tmp_path):
    root=tmp_path/"topic";(root/"reports").mkdir(parents=True)
    (root/"state.json").write_text(json.dumps({"active_run_id":"run-current","active_run_scope":{"run_id":"run-current","assigned_question_ids":["q-new"]}}))
    current={"id":"ev-current","question_id":"q-old"};historical={"id":"ev-historical","question_id":"q-old"};captured={}
    monkeypatch.setattr(completion,"_workers",lambda _root,_run:[{"status":"complete","question_id":"q-new","ingest_summary":{"accepted_evidence_ids":["ev-current"]}}])
    monkeypatch.setattr(completion,"_evidence",lambda _root:{"ev-current":current,"ev-historical":historical})
    monkeypatch.setattr(completion,"approved_reviews_for_run",lambda _root,_run:[{"id":"critic-1"}])
    def fake_quality(_root,cards,_policy,covered_question_ids,run_id=None): captured["ids"]=[item["id"] for item in cards];captured["covered"]=covered_question_ids;captured["run_id"]=run_id;return {"passes_all_gates":True}
    monkeypatch.setattr(completion,"_quality",fake_quality);monkeypatch.setattr(completion,"load_rubric",lambda _path:{})
    result=completion.completion_gate(root,"run-current",tmp_path/"skill")
    assert captured["ids"]==["ev-current"];assert captured["covered"]=={"q-new"};assert captured["run_id"]=="run-current"
    assert result["assigned_question_ids"]==["q-new"];assert result["quality_scope"]=="active_run_question_snapshot"
