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
PUBLIC = ROOT / ".agents/skills/deep-research/scripts/research.py"
CONTROL = ROOT / ".agents/skills/deep-research/scripts/researchctl.py"
QUALITY = ROOT / ".agents/skills/deep-research/scripts/qualityctl.py"
RELEASE = ROOT / ".agents/skills/deep-research/scripts/releasectl.py"
sys.path.insert(0, str(ROOT / ".agents/skills/deep-research/scripts"))
from lib.agent_snapshots import build_review_snapshot


def run(env: dict[str, str], *args: object) -> dict:
    completed = subprocess.run([PYTHON, *map(str, args)], cwd=ROOT, env=env, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(completed.stdout)


def worker(worker_id: str, run_id: str, source_id: str, evidence_id: str, url: str, fact: str, group: str, digest: str) -> dict:
    prefix = worker_id.replace("worker-", "")
    return {
        "worker_result_version": 2, "worker_result_id": worker_id, "run_id": run_id,
        "status": "complete", "question_id": "q-001", "overlap_key": "smoke-boundary",
        "budget_profile": "lite", "coverage_status": "sufficient",
        "queries_run": [
            {"id": f"query-{prefix}-primary", "query": fact, "intent": "primary_source", "provider": "native_web", "language": "en", "time_anchor": "2026-08-03", "fallback_of": None, "outcome": "primary_candidate_found"},
            {"id": f"query-{prefix}-against", "query": fact + " limitations", "intent": "disconfirming", "provider": "native_web", "language": "en", "time_anchor": "2026-08-03", "fallback_of": None, "outcome": "candidate_found"},
        ],
        "source_attempts": [{"id": source_id, "url": url, "normalized_url": url, "status": "accepted", "eligible_for_evidence": True, "tool": "direct_fetch", "access_mode": "public_static", "query_id": f"query-{prefix}-primary", "discovery_method": "search", "discovered_via_source_attempt_id": None, "content_sha256": digest, "http_status": 200, "source_version": "2026-08-03", "reason": None}],
        "evidence_cards": [{"id": evidence_id, "source_attempt_id": source_id, "source": {"url": url, "title": fact, "publisher": group, "published_at": "2026-08-03", "source_type": "official"}, "statement": fact, "quote": fact, "locator": "Section 1", "stance": "support", "confidence": 0.9, "independence_group": group, "prompt_injection_risk": "low", "version_compatibility": "not_applicable"}],
        "gaps": [], "budget_used": {"tool_calls": 2, "search_queries": 2, "source_pages": 1},
        "stop_reason": "acceptance_criteria_met",
    }


def report_text() -> str:
    return """---
title: Lifecycle smoke report
report_type: final
---

## Executive conclusion

The deterministic lifecycle produces auditable evidence and preserves the active run boundary from ingestion through completion. [[ev-1]]

## Scope and method

This offline smoke test exercises the coordinator lifecycle without external network access or mutable third-party dependencies.

## Supported findings

The first independent official fixture confirms that Worker ingestion preserves query and source lineage for completion review. [[ev-1]]

The second independent official fixture confirms that duplicate-free Evidence can satisfy the configured independence boundary. [[ev-2]]

## Conflict and weakening evidence

The test explicitly records a bounded disconfirming route while noting that deterministic fixtures cannot establish real-world factual truth. [[ev-1]]

## Implications and recommendations

A complete status is appropriate only after Worker, Critic, quality, report, citation, and profile audit gates pass together. [[ev-2]]

## Uncertainty and limitations

This smoke test proves lifecycle mechanics and deterministic validation, but it does not prove network availability or semantic correctness of external research. [[ev-1]]

## Unresolved questions

No lifecycle blocker remains inside this deterministic fixture; external retrieval behavior remains outside the fixture boundary.

## Claim evidence

The completion decision is supported by two independent fixture origins and their frozen Source Attempt hashes. [[ev-1]] [[ev-2]]

## Sources

The sources are deterministic official-style fixtures created only for offline lifecycle validation and removed after the test.

## Quality and audit

All citations are structurally valid, both Source Attempt identities are frozen, and hard quality and report gates are evaluated before completion.
"""


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="deep-research-lifecycle-") as temporary:
        workspace = Path(temporary) / "topics"; workspace.mkdir(parents=True)
        env = dict(os.environ); env["DEEP_RESEARCH_WORKSPACE_ROOT"] = str(workspace)
        run(env, PUBLIC, "new", "Lifecycle Smoke", "--directory-name", "lifecycle-smoke", "--budget", "lite")
        run(env, PUBLIC, "plan", "lifecycle-smoke", "--questions", "1")
        topic = workspace / "lifecycle-smoke"; design_path = topic / "plans/current-design.json"; design = json.loads(design_path.read_text(encoding="utf-8")); design["questions"][0]["overlap_key"] = "smoke-boundary"; design_path.write_text(json.dumps(design, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(env, PUBLIC, "plan", "lifecycle-smoke")
        run_id = run(env, PUBLIC, "start", "lifecycle-smoke", "--mode", "baseline")["run_id"]
        for value in [
            worker("worker-one", run_id, "src-1", "ev-1", "https://example.com/one", "Lifecycle fact one", "origin-one", "a" * 64),
            worker("worker-two", run_id, "src-2", "ev-2", "https://example.org/two", "Lifecycle fact two", "origin-two", "b" * 64),
        ]:
            path = topic / f"{value['worker_result_id']}.json"; path.write_text(json.dumps(value), encoding="utf-8"); run(env, CONTROL, "ingest-worker", "lifecycle-smoke", "--file", path)
        state = json.loads((topic / "state.json").read_text(encoding="utf-8"))
        assert state["usage"] == {"queries": 4, "pages": 2, "evidence_cards": 2}
        critic = {"critic_review_version": 2, "id": "critic-lifecycle", "run_id": run_id, "reviewed_by": "research_critic", "reviewed_snapshot": build_review_snapshot(topic, run_id), "status": "approved", "findings": [], "targeted_searches": [], "unresolved": [], "stop_reason": "review_complete"}
        critic_path = topic / "critic.json"; critic_path.write_text(json.dumps(critic), encoding="utf-8"); run(env, CONTROL, "critic-save", "lifecycle-smoke", "--file", critic_path)
        report = topic / "reports/final.md"; report.write_text(report_text(), encoding="utf-8")
        run(env, CONTROL, "verify-citations", "lifecycle-smoke", "--report", report)
        run(env, QUALITY, "report-check", "lifecycle-smoke", "--report", report, "--require-gates")
        run(env, QUALITY, "audit-init", "lifecycle-smoke", "--report", report)
        audit_path = report.with_suffix(".md.audit.json"); audit = json.loads(audit_path.read_text(encoding="utf-8"))
        for item in audit["items"]:
            item.update(status="verified", checked_at="2026-08-03T00:00:00Z", checked_by="research_critic", observed_text=item["expected_quote"], content_sha256=item["expected_content_sha256"], match_type="exact")
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(env, QUALITY, "audit-validate", "--audit", audit_path, "--final")
        finish = run(env, PUBLIC, "finish", "lifecycle-smoke", "--status", "complete"); assert finish["completion_gates"]["valid"]
        reflection = {"run_id": run_id, "critic_review_id": "critic-lifecycle", "summary": "Lifecycle completed", "open_questions": [], "next_actions": [], "lesson_candidates": []}
        reflection_path = topic / "reflection.json"; reflection_path.write_text(json.dumps(reflection), encoding="utf-8"); run(env, CONTROL, "reflect", "lifecycle-smoke", "--file", reflection_path)
        run(env, PUBLIC, "validate", "lifecycle-smoke")
        package = Path(temporary) / "lifecycle.deep-research.zip"; run(env, RELEASE, "export-topic", "lifecycle-smoke", "--output", package); run(env, RELEASE, "verify-package", "--package", package)


if __name__ == "__main__": main()
