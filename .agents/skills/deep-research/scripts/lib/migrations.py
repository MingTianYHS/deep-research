from __future__ import annotations
from pathlib import Path
from typing import Any
from .io_utils import append_jsonl,atomic_write_json,read_json,utc_now
CURRENT_WORKSPACE_FORMAT=2

def inspect(root:Path)->dict[str,Any]:
    state=read_json(root/"state.json",{});explicit="workspace_format_version" in state;version=state.get("workspace_format_version",1);errors=[]
    if not isinstance(version,int) or isinstance(version,bool) or version<0:errors.append("workspace_format_version must be a non-negative integer")
    elif version>CURRENT_WORKSPACE_FORMAT:errors.append(f"workspace format {version} is newer than runtime {CURRENT_WORKSPACE_FORMAT}")
    for rel in ("topic.toml","state.json","evidence/cards.jsonl","claims.jsonl"):
        if not (root/rel).exists():errors.append(f"missing required workspace file: {rel}")
    return {"workspace":str(root),"version":version,"current_version":CURRENT_WORKSPACE_FORMAT,"explicit_version":explicit,"needs_migration":not errors and (version<CURRENT_WORKSPACE_FORMAT or not explicit),"errors":errors,"valid":not errors}
def plan(root:Path)->dict[str,Any]:
    result=inspect(root);actions=[]
    if result["valid"] and (result["version"]<2 or not result["explicit_version"]):
        actions += [{"from":result["version"],"to":2,"action":"adopt topic-expert AGENTS.md and bounded context contract"},{"from":result["version"],"to":2,"action":"add validated reusable lessons memory"}]
    result["actions"]=actions;return result
def _default_agents(root:Path)->str:
    return f"# Topic expert coordinator\n\nThis directory is the persistent research workspace. Load the user-level deep-research Skill. The main Codex session owns planning, approvals, state, and writes. Delegate execution only to topic_researcher, research_critic, and research_synthesizer. Read `{(root/'context.md').as_posix()}` as a bounded cache, never as evidence.\n"
def apply(root:Path)->dict[str,Any]:
    migration=plan(root)
    if not migration["valid"]:raise ValueError("; ".join(migration["errors"]))
    if not migration["actions"]:return {**migration,"applied":False}
    old=root/"AGENT.md";new=root/"AGENTS.md"
    if not new.exists():new.write_text(old.read_text(encoding="utf-8") if old.exists() else _default_agents(root),encoding="utf-8")
    (root/"memory").mkdir(parents=True,exist_ok=True);(root/"memory/lessons.jsonl").touch(exist_ok=True);(root/"context.md").touch(exist_ok=True)
    state=read_json(root/"state.json",{});previous=state.get("workspace_format_version","implicit-1");state["workspace_format_version"]=2;state.setdefault("baseline_completed",bool(state.get("last_run_at")));state.setdefault("research_generation",1 if state.get("last_run_at") else 0);state.setdefault("knowledge_status","evolving" if state.get("last_run_at") else "empty");atomic_write_json(root/"state.json",state)
    event={"type":"workspace.migrated","from":previous,"to":2,"at":utc_now(),"actions":migration["actions"]};append_jsonl(root/"logs/migrations.jsonl",[event]);return {**inspect(root),"actions":migration["actions"],"applied":True,"event":event}
