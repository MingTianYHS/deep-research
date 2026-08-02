from __future__ import annotations
from collections import Counter
from typing import Any
QUESTION_TYPES={"fact","comparison","causal","forecast","decision","landscape"};WORKER_PROFILES={"lite","standard","deep"};REQUIRED={"id","question","type","decision_relevance","acceptance_criteria","disconfirming_query","overlap_key"}

def validate_design(design:dict[str,Any])->dict[str,Any]:
    errors=[];warnings=[];questions=design.get("questions")
    if not isinstance(questions,list) or not questions:return {"valid":False,"errors":["questions must be a non-empty list"],"warnings":[],"question_count":0}
    if len(questions)>8:errors.append("at most 8 research questions are allowed")
    ids=[i.get("id") for i in questions];duplicates=[v for v,c in Counter(ids).items() if v and c>1]
    if duplicates:errors.append(f"duplicate question ids: {duplicates}")
    known=set(ids);overlap=Counter(i.get("overlap_key") for i in questions if i.get("overlap_key"))
    for n,item in enumerate(questions,1):
        missing=sorted(k for k in REQUIRED if not item.get(k))
        if missing:errors.append(f"question {n}: missing {missing}")
        if item.get("type") not in QUESTION_TYPES:errors.append(f"question {n}: invalid type {item.get('type')}")
        if not isinstance(item.get("acceptance_criteria"),list) or not item.get("acceptance_criteria"):errors.append(f"question {n}: acceptance_criteria must be a non-empty list")
        deps=item.get("dependencies",[])
        if not isinstance(deps,list):errors.append(f"question {n}: dependencies must be a list")
        else:
            unknown=sorted(set(deps)-known)
            if unknown:errors.append(f"question {n}: unknown dependencies {unknown}")
            if item.get("id") in deps:errors.append(f"question {n}: self dependency")
        if overlap[item.get("overlap_key")]>1:errors.append(f"question {n}: duplicate overlap_key {item.get('overlap_key')}")
        if item.get("type") in {"causal","forecast"} and not item.get("alternative_explanations"):warnings.append(f"question {n}: causal/forecast question should list alternative_explanations")
        if not item.get("preferred_source_types"):warnings.append(f"question {n}: preferred_source_types not specified")
        profile=item.get("worker_budget_profile","standard")
        if profile not in WORKER_PROFILES:errors.append(f"question {n}: invalid worker_budget_profile {profile}")
        if item.get("version_sensitive") and not item.get("target_version") and not item.get("target_commit"):errors.append(f"question {n}: version_sensitive requires target_version or target_commit")
    graph={i.get("id"):i.get("dependencies",[]) for i in questions if i.get("id")};visiting=set();visited=set()
    def visit(node:str):
        if node in visiting:errors.append(f"dependency cycle includes {node}");return
        if node in visited:return
        visiting.add(node)
        for dep in graph.get(node,[]):visit(dep)
        visiting.remove(node);visited.add(node)
    for node in graph:visit(node)
    return {"valid":not errors,"errors":sorted(set(errors)),"warnings":sorted(set(warnings)),"question_count":len(questions),"parallel_groups":parallel_groups(questions)}

def parallel_groups(questions:list[dict[str,Any]])->list[list[str]]:
    remaining={i["id"]:set(i.get("dependencies",[])) for i in questions if i.get("id")};done=set();groups=[]
    while remaining:
        ready=sorted(n for n,d in remaining.items() if d<=done)
        if not ready:break
        groups.append(ready);done.update(ready)
        for n in ready:remaining.pop(n)
    return groups

def template(title:str,question_count:int=1,worker_budget_profile:str="standard")->dict[str,Any]:
    questions=[]
    for n in range(1,question_count+1):questions.append({"id":f"q-{n:03d}","question":f"Replace with answerable research question {n}","type":"fact","decision_relevance":"Why the answer matters","dependencies":[],"overlap_key":f"unique-subtopic-{n}","preferred_source_types":["official","paper"],"acceptance_criteria":["At least one primary source","Independent corroboration for a core claim"],"disconfirming_query":"Search terms intended to disprove the expected answer","alternative_explanations":[],"exclusions":[],"version_sensitive":False,"target_version":"","target_commit":"","allow_main_branch_fallback":False,"worker_budget_profile":worker_budget_profile})
    return {"title":title,"decision_context":"What decision or understanding should this research support?","scope":{"include":[],"exclude":[],"time_window":"","geographies":[]},"questions":questions}

def render_questions(design:dict[str,Any])->str:
    lines=["# Research questions",""]
    for item in design.get("questions",[]):lines += [f"## {item.get('id')}","",f"- Status: open",f"- Type: {item.get('type')}",f"- Question: {item.get('question')}",f"- Decision relevance: {item.get('decision_relevance')}",f"- Overlap key: {item.get('overlap_key')}",""]
    return "\n".join(lines).rstrip()+"\n"
