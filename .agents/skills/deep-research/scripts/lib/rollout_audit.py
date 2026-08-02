from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
from typing import Any
from .source_attempts import normalize_url
FAILURE=re.compile(r"Exit code:\s*(?:1|2|124)\b|401\s*:\s*Unauthorized|403\s*:\s*Forbidden|404\s*:\s*Not Found|Method not found|timed out|browser is already running|CRAWL_LIVECRAWL_TIMEOUT",re.I)
URL=re.compile(r"https?://[^\s\\\"']+")

def _load(path:Path)->list[dict[str,Any]]:
    rows=[]
    for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip():continue
        try:rows.append(json.loads(line))
        except json.JSONDecodeError as e:raise ValueError(f"invalid JSONL line {n}: {e}") from e
    return rows

def audit_rollout(path:Path,*,max_tool_calls:int=24,max_failed_calls:int=3)->dict[str,Any]:
    rows=_load(path);meta=next((r.get("payload",{}) for r in rows if r.get("type")=="session_meta"),{});source=meta.get("source",{}).get("subagent",{});guardian=source.get("other")=="guardian";spawn=source.get("thread_spawn",{}) if isinstance(source,dict) else {};agent_path=spawn.get("agent_path");agent_role=spawn.get("agent_role");calls=[];outputs={};assistant_final=False;compactions=0;guardian_turns=0;task_complete=None;tokens={}
    for row in rows:
        p=row.get("payload",{})
        if row.get("type")=="response_item" and p.get("type")=="function_call":calls.append(p)
        elif row.get("type")=="response_item" and p.get("type")=="function_call_output":outputs[p.get("call_id","")]=str(p.get("output",""))
        elif row.get("type")=="response_item" and p.get("type")=="message" and p.get("role")=="assistant" and p.get("phase") not in {"commentary","analysis"}:assistant_final=True
        elif row.get("type")=="event_msg":
            t=p.get("type")
            if t=="context_compacted":compactions+=1
            elif t=="task_started" and guardian:guardian_turns+=1
            elif t=="task_complete":task_complete=p.get("last_agent_message")
            elif t=="token_count":tokens=p.get("info",{}).get("total_token_usage",{})
    failed=[c for c in calls if FAILURE.search(outputs.get(c.get("call_id",""),""))];urls=[]
    for c in calls:
        for raw in URL.findall(str(c.get("arguments",""))):
            raw=raw.rstrip(";,.)")
            try:urls.append(normalize_url(raw))
            except ValueError:urls.append(raw)
    duplicates={u:n for u,n in Counter(urls).items() if n>1};final_present=bool(task_complete) or assistant_final;custom_agent=bool(agent_path or agent_role);gates={"custom_agent":guardian or custom_agent,"final_message":guardian or final_present,"maximum_tool_calls":len(calls)<=max_tool_calls,"maximum_failed_calls":len(failed)<=max_failed_calls}
    return {"file":str(path),"session_kind":"guardian" if guardian else meta.get("thread_source","unknown"),"cwd":meta.get("cwd"),"agent_nickname":meta.get("agent_nickname"),"agent_path":agent_path,"agent_role":agent_role,"custom_agent":custom_agent,"tool_calls":len(calls),"tool_names":dict(Counter(c.get("name","unknown") for c in calls)),"failed_or_nonproductive_calls":len(failed),"duplicate_urls":duplicates,"context_compactions":compactions,"guardian_turns":guardian_turns,"final_message_present":final_present,"token_usage":tokens,"gates":gates,"passes_all_gates":all(gates.values()),"limitations":["Rollout fields vary by Codex version; custom-agent identity and failure detection remain heuristic."]}
