from pathlib import Path
import sys
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
import lib.completion as completion


def test_completion_quality_is_scoped_to_active_run(monkeypatch,tmp_path):
    root=tmp_path/"topic";(root/"reports").mkdir(parents=True)
    current={"id":"ev-current","question_id":"q-1"};historical={"id":"ev-historical","question_id":"q-1"};captured={}
    monkeypatch.setattr(completion,"_workers",lambda _root,_run:[{"ingest_summary":{"accepted_evidence_ids":["ev-current"]}}])
    monkeypatch.setattr(completion,"_evidence",lambda _root:{"ev-current":current,"ev-historical":historical})
    monkeypatch.setattr(completion,"approved_reviews_for_run",lambda _root,_run:[{"id":"critic-1"}])
    def fake_quality(_root,cards,_policy):captured["ids"]=[item["id"] for item in cards];return {"passes_all_gates":True}
    monkeypatch.setattr(completion,"_quality",fake_quality)
    monkeypatch.setattr(completion,"load_rubric",lambda _path:{})
    result=completion.completion_gate(root,"run-current",tmp_path/"skill")
    assert captured["ids"]==["ev-current"]
    assert result["quality_scope"]=="active_run"
