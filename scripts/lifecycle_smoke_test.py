#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SCRIPTS = ROOT / ".agents/skills/deep-research/scripts"
PUBLIC, CONTROL, AGENT = SCRIPTS / "research.py", SCRIPTS / "researchctl.py", SCRIPTS / "agentctl.py"
QUALITY, RELEASE = SCRIPTS / "qualityctl.py", SCRIPTS / "releasectl.py"
sys.path.insert(0, str(SCRIPTS))
from lib.agent_contracts import build_synthesis_assignment
from lib.agent_snapshots import build_review_snapshot


def run(env: dict[str, str], *args: object) -> dict:
    command = [PYTHON, *map(str, args)]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"command failed: {command}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
    return json.loads(completed.stdout)


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def new_worker(worker_id: str, run_id: str, source_id: str, evidence_id: str, url: str, fact: str, origin: str, digest: str) -> dict:
    suffix = worker_id.removeprefix("worker-")
    return {
        "worker_result_version": 2, "worker_result_id": worker_id, "run_id": run_id, "status": "complete",
        "question_id": "q-001", "overlap_key": "smoke-boundary", "budget_profile": "lite", "coverage_status": "sufficient",
        "queries_run": [
            {"id": f"query-{suffix}-primary", "query": fact, "intent": "primary_source", "provider": "native_web", "language": "en", "time_anchor": "2026-08-03", "fallback_of": None, "outcome": "primary_candidate_found"},
            {"id": f"query-{suffix}-against", "query": fact + " limitations", "intent": "disconfirming", "provider": "native_web", "language": "en", "time_anchor": "2026-08-03", "fallback_of": None, "outcome": "candidate_found"},
        ],
        "source_attempts": [{"id": source_id, "url": url, "normalized_url": url, "status": "accepted", "eligible_for_evidence": True, "tool": "direct_fetch", "access_mode": "public_static", "query_id": f"query-{suffix}-primary", "discovery_method": "search", "discovered_via_source_attempt_id": None, "attempted_at": "2026-08-03T00:00:00Z", "content_sha256": digest, "http_status": 200, "source_version": "2026-08-03", "reason": None}],
        "evidence_cards": [{"id": evidence_id, "source_attempt_id": source_id, "source": {"url": url, "title": fact, "publisher": origin, "published_at": "2026-08-03", "source_type": "official"}, "statement": fact, "quote": fact, "locator": "Section 1", "stance": "support", "confidence": 0.9, "independence_group": origin, "prompt_injection_risk": "low", "version_compatibility": "not_applicable"}],
        "reused_evidence_ids": [], "gaps": [], "budget_used": {"tool_calls": 2, "search_queries": 2, "source_pages": 1}, "stop_reason": "acceptance_criteria_met",
    }


def reuse_worker(run_id: str, question_id: str) -> dict:
    rationale = "The user-selected continuation explicitly names this fresh Evidence and the lifecycle assertion is unchanged."
    return {"worker_result_version": 2, "worker_result_id": "worker-incremental-reuse", "run_id": run_id, "status": "complete", "question_id": question_id, "overlap_key": f"incremental-{question_id}", "budget_profile": "lite", "coverage_status": "sufficient", "queries_run": [], "source_attempts": [], "evidence_cards": [], "reused_evidence_ids": ["ev-1", "ev-2"], "reuse_rationale": {"ev-1": rationale, "ev-2": rationale}, "gaps": [], "budget_used": {"tool_calls": 0, "search_queries": 0, "source_pages": 0}, "stop_reason": "existing_evidence_sufficient"}


def report_text(label: str) -> str:
    return f"""---
title: {label}
report_type: final
---

## Executive conclusion

The deterministic lifecycle preserves run boundaries from ingestion through completion. [[ev-1]]

## Scope and method

This offline smoke test exercises persistence without external network access.

## Supported findings

Independent fixtures preserve Query, Source Attempt, Evidence, and Claim lineage. [[ev-1]] [[ev-2]]

## Conflict and weakening evidence

The fixture records a bounded disconfirming route but does not establish external factual truth. [[ev-1]]

## Implications and recommendations

A complete status is appropriate only when deterministic quality gates pass together. [[ev-2]]

## Uncertainty and limitations

Network availability and external semantic correctness remain outside this fixture. [[ev-1]]

## Unresolved questions

The next bounded Run should test reuse without rediscovery.

## Claim evidence

Two independent fixture origins support the lifecycle assertion. [[ev-1]] [[ev-2]]

## Sources

The sources are deterministic offline fixtures.

## Quality and audit

Citations, Source Attempt identities, and frozen hashes are checked before completion.
"""


def save_critic(env: dict[str, str], topic: Path, run_id: str, critic_id: str) -> dict:
    value = {"critic_review_version": 2, "id": critic_id, "run_id": run_id, "reviewed_by": "research_critic", "reviewed_snapshot": build_review_snapshot(topic, run_id), "status": "approved", "findings": [], "targeted_searches": [], "unresolved": [], "stop_reason": "review_complete"}
    path = topic / f"{critic_id}.json"; save(path, value)
    return run(env, CONTROL, "critic-save", "lifecycle-smoke", "--file", path)["critic_review"]


def synthesis(topic: Path, run_id: str, critic: dict, report: Path, synthesis_id: str, label: str, backlog: list[dict]) -> dict:
    assignment = build_synthesis_assignment(topic, run_id, report, critic)
    return {"synthesis_result_version": 2, "id": synthesis_id, "run_id": run_id, "critic_review_id": critic["id"], "input_snapshot": assignment["input_snapshot"], "status": "complete", "report_path": str(report), "output_language": "zh-CN", "claim_ids_used": assignment["claim_ids"], "evidence_ids_used": ["ev-1", "ev-2"], "unresolved": [], "knowledge_delta": {"new_claims": [f"{label}: lifecycle lineage remains intact"], "strengthened_claims": [], "weakened_claims": [], "new_connections": ["Persistent Evidence can support a later bounded Run"], "new_hypotheses": [], "remaining_gaps": [item["question"] for item in backlog]}, "next_research": backlog, "report_markdown": report_text(label)}


def save_synthesis(env: dict[str, str], topic: Path, value: dict) -> dict:
    path = topic / f"{value['id']}.json"; save(path, value)
    return run(env, AGENT, "synthesis-save", "lifecycle-smoke", "--file", path)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="deep-research-lifecycle-") as temporary:
        workspace = Path(temporary) / "topics"; workspace.mkdir(parents=True)
        env = dict(os.environ); env["DEEP_RESEARCH_WORKSPACE_ROOT"] = str(workspace)
        run(env, PUBLIC, "new", "Lifecycle Smoke", "--directory-name", "lifecycle-smoke", "--budget", "lite")
        run(env, PUBLIC, "plan", "lifecycle-smoke", "--questions", "1")
        topic = workspace / "lifecycle-smoke"; design_path = topic / "plans/current-design.json"
        design = json.loads(design_path.read_text(encoding="utf-8")); design["questions"][0]["overlap_key"] = "smoke-boundary"; save(design_path, design); run(env, PUBLIC, "plan", "lifecycle-smoke")
        run_id = run(env, PUBLIC, "start", "lifecycle-smoke", "--mode", "baseline")["run_id"]
        values = [new_worker("worker-one", run_id, "src-1", "ev-1", "https://example.com/one", "Lifecycle fact one", "origin-one", "a" * 64), new_worker("worker-two", run_id, "src-2", "ev-2", "https://example.org/two", "Lifecycle fact two", "origin-two", "b" * 64)]
        for value in values:
            path = topic / f"{value['worker_result_id']}.json"; save(path, value); run(env, CONTROL, "ingest-worker", "lifecycle-smoke", "--file", path)
        assert json.loads((topic / "state.json").read_text())["usage"] == {"queries": 4, "pages": 2, "evidence_cards": 2}
        run(env, PUBLIC, "claim-sync", "lifecycle-smoke"); critic = save_critic(env, topic, run_id, "critic-baseline")
        report = topic / "reports/final.md"; backlog = [{"id": "rq-overseas", "question": "Can existing Evidence answer the next bounded question?", "reason": "Exercise explicit continuation and reuse", "priority": "medium", "gap_type": "continuation", "known_evidence_ids": ["ev-1", "ev-2"], "acceptance_criteria": ["Reuse fresh Evidence without a discovery Query"]}]
        first = synthesis(topic, run_id, critic, report, "syn-baseline", "Baseline synthesis", backlog)
        assert save_synthesis(env, topic, first)["memory_applied"] is True; assert save_synthesis(env, topic, first)["idempotent"] is True
        assert len((topic / "memory/knowledge-deltas.jsonl").read_text().splitlines()) == 1
        run(env, CONTROL, "verify-citations", "lifecycle-smoke", "--report", report); run(env, QUALITY, "report-check", "lifecycle-smoke", "--report", report, "--require-gates"); run(env, QUALITY, "audit-init", "lifecycle-smoke", "--report", report)
        audit_path = report.with_suffix(".md.audit.json"); audit = json.loads(audit_path.read_text())
        for item in audit["items"]: item.update(status="verified", checked_at="2026-08-03T00:00:00Z", checked_by="research_critic", observed_text=item["expected_quote"], content_sha256=item["expected_content_sha256"], match_type="exact")
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); run(env, QUALITY, "audit-validate", "--audit", audit_path, "--final")
        assert run(env, PUBLIC, "finish", "lifecycle-smoke", "--status", "complete")["completion_gates"]["valid"]
        assert run(env, PUBLIC, "next", "lifecycle-smoke")["phase"] == "awaiting_user_research_request"

        continued = run(env, PUBLIC, "continue", "lifecycle-smoke", "--backlog-id", "rq-overseas"); run_id_2 = continued["run_id"]
        assert continued["mode"] == "incremental" and run_id_2 != run_id
        question_id = json.loads(design_path.read_text())["questions"][0]["id"]; reuse = reuse_worker(run_id_2, question_id); reuse_path = topic / "worker-incremental-reuse.json"; save(reuse_path, reuse)
        reused = run(env, CONTROL, "ingest-worker", "lifecycle-smoke", "--file", reuse_path); assert reused["accepted"] == 0 and reused["reused"] == 2
        run(env, PUBLIC, "claim-sync", "lifecycle-smoke"); critic_2 = save_critic(env, topic, run_id_2, "critic-incremental")
        second = synthesis(topic, run_id_2, critic_2, topic / "reports/incremental.md", "syn-incremental", "Incremental reuse synthesis", []); save_synthesis(env, topic, second)
        assert len((topic / "memory/knowledge-deltas.jsonl").read_text().splitlines()) == 2
        run(env, PUBLIC, "finish", "lifecycle-smoke", "--status", "partial"); assert run(env, PUBLIC, "next", "lifecycle-smoke")["phase"] == "awaiting_user_research_request"
        assert "run.reflected" not in (topic / "logs/runs.jsonl").read_text(); run(env, PUBLIC, "validate", "lifecycle-smoke")
        package = Path(temporary) / "lifecycle.deep-research.zip"; run(env, RELEASE, "export-topic", "lifecycle-smoke", "--output", package); run(env, RELEASE, "verify-package", "--package", package)


if __name__ == "__main__":
    main()
