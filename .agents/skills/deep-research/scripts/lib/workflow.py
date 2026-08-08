from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent_contracts import (
    build_critic_assignment,
    build_researcher_assignment,
    build_synthesis_assignment,
)
from .audit import validate_audit
from .citations import CITATION_RE
from .claims import materialize
from .completion import completion_gate
from .critic_reviews import (
    approved_reviews_for_run,
    latest_review_for_run,
    review_is_current,
)
from .io_utils import iter_jsonl, read_json
from .research_design import validate_design

WORKFLOW_SCHEMA_VERSION = 2
REPORT_TODO_RE = re.compile(r"TODO|待补充|待填写|待判定|pending", re.IGNORECASE)


def _workers(root: Path, run_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    directory = root / "logs/workers"
    if not directory.is_dir():
        return values
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("run_id") == run_id:
            values.append(value)
    return values


def _unfinished_reflection(root: Path) -> str | None:
    finished: list[str] = []
    reflected: set[str] = set()
    path = root / "logs/runs.jsonl"
    if not path.exists():
        return None
    for _, event in iter_jsonl(path):
        run_id = event.get("id")
        if not isinstance(run_id, str) or not run_id:
            continue
        if event.get("type") == "run.reflected":
            reflected.add(run_id)
        if event.get("finished_at") and event.get("status") in {
            "complete",
            "partial",
            "failed",
        }:
            finished.append(run_id)
    for run_id in reversed(finished):
        if run_id not in reflected:
            return run_id
    return None


def _run_started_timestamp(root: Path, run_id: str) -> float | None:
    for _, event in iter_jsonl(root / "logs/runs.jsonl"):
        if event.get("id") != run_id or not event.get("started_at"):
            continue
        try:
            return datetime.fromisoformat(
                str(event["started_at"]).replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            return None
    return None


def _result(
    root: Path,
    state: dict[str, Any],
    phase: str,
    next_action: str,
    *,
    command: str | None = None,
    agent: str | None = None,
    requires_user_input: bool = False,
    blockers: list[str] | None = None,
    assignments: list[dict[str, Any]] | None = None,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "topic": state.get("topic", root.name),
        "workspace": str(root),
        "active_run_id": state.get("active_run_id"),
        "phase": phase,
        "next_action": next_action,
        "command": command,
        "agent": agent,
        "requires_user_input": requires_user_input,
        "blockers": blockers or [],
        "assignments": assignments or [],
        "progress": progress or {},
        "coordinator_instruction": (
            "Execute next_action in the Codex coordinator. Do not ask the user to run "
            "internal controllers. Do not assume subagents inherit the parent Skill; "
            "send the returned versioned assignment unchanged. Ask the user only when "
            "requires_user_input is true, scope is materially ambiguous, or an external "
            "side effect needs approval."
        ),
    }


def derive_workflow(root: Path, skill_dir: Path) -> dict[str, Any]:
    state = read_json(root / "state.json", {})
    design_path = root / "plans/current-design.json"
    if not design_path.exists():
        return _result(
            root,
            state,
            "research_design",
            "create_research_design",
            command="research.py plan --questions <1-8>",
            blockers=["No canonical Research Design exists."],
        )

    design = read_json(design_path, {})
    design_check = validate_design(design, state.get("budget_profile", "standard"))
    if not design_check["valid"]:
        return _result(
            root,
            state,
            "research_design",
            "repair_research_design",
            command="designctl.py validate --file plans/current-design.json --strict",
            blockers=design_check["errors"],
        )

    active_run_id = state.get("active_run_id")
    if not active_run_id:
        unreflected = _unfinished_reflection(root)
        if unreflected:
            approved = approved_reviews_for_run(root, unreflected, current_only=False)
            if not approved:
                return _result(
                    root,
                    state,
                    "reflection_blocked",
                    "report_missing_run_critic_review",
                    blockers=[
                        "The finished Run has no approved persisted Critic Review; "
                        "Reflection cannot be applied safely."
                    ],
                    progress={"run_id": unreflected},
                )
            return _result(
                root,
                state,
                "reflection",
                "apply_critic_linked_reflection",
                command="researchctl.py reflect --file reflection.json",
                progress={"run_id": unreflected},
            )
        return _result(
            root,
            state,
            "ready_to_start",
            "start_run",
            command="research.py start --mode initial",
            progress={"open_questions": len(state.get("open_questions", []))},
        )

    questions = [
        item
        for item in design.get("questions", [])
        if isinstance(item, dict) and item.get("status", "open") == "open"
    ]
    questions_by_id = {str(item.get("id")): item for item in questions}
    workers = _workers(root, active_run_id)
    completed_questions = {
        str(worker.get("question_id"))
        for worker in workers
        if worker.get("status") == "complete" and worker.get("question_id")
    }
    attempted_questions = {
        str(worker.get("question_id"))
        for worker in workers
        if worker.get("question_id")
    }
    closed_questions = {
        str(item.get("id"))
        for item in design.get("questions", [])
        if isinstance(item, dict) and item.get("status") == "closed"
    }
    available_dependencies = closed_questions | completed_questions
    remaining = [
        item for item in questions if str(item.get("id")) not in completed_questions
    ]
    ready = [
        item
        for item in remaining
        if set(map(str, item.get("dependencies", []))) <= available_dependencies
    ]
    progress = {
        "questions_total": len(questions),
        "questions_completed": len(completed_questions),
        "workers_persisted": len(workers),
    }
    if remaining:
        if not ready:
            return _result(
                root,
                state,
                "worker_research",
                "resolve_question_dependencies",
                blockers=[
                    "Open questions remain, but their dependencies are not complete."
                ],
                progress=progress,
            )
        retry = any(str(item.get("id")) in attempted_questions for item in ready)
        assignments = [
            build_researcher_assignment(
                root,
                active_run_id,
                item,
                skill_dir / "config/budgets.toml",
            )
            for item in ready
        ]
        return _result(
            root,
            state,
            "worker_research",
            "redelegate_incomplete_questions" if retry else "delegate_open_questions",
            agent="topic_researcher",
            assignments=assignments,
            progress=progress,
        )

    accepted_evidence_ids = {
        evidence_id
        for worker in workers
        for evidence_id in (worker.get("ingest_summary") or {}).get(
            "accepted_evidence_ids", []
        )
        if isinstance(evidence_id, str)
    }
    claims = materialize(root / "claims.jsonl")
    run_claims = [
        claim
        for claim in claims.values()
        if any(
            relation.get("evidence_id") in accepted_evidence_ids
            for relation in claim.get("relations", [])
            if isinstance(relation, dict)
        )
    ]
    progress.update(
        {
            "accepted_evidence": len(accepted_evidence_ids),
            "run_claims": len(run_claims),
        }
    )
    if accepted_evidence_ids and not run_claims:
        return _result(
            root,
            state,
            "claim_review",
            "materialize_claim_evidence",
            command="researchctl.py claim-create / claim-link / claim-status",
            blockers=[
                "Current-run Evidence has not been connected to any materialized Claim."
            ],
            progress=progress,
        )

    approved_reviews = approved_reviews_for_run(root, active_run_id)
    latest_review = latest_review_for_run(root, active_run_id)
    if not approved_reviews:
        previous_id = latest_review.get("id") if latest_review else None
        if latest_review and latest_review.get("status") == "changes_required":
            if review_is_current(root, latest_review, active_run_id):
                remediation_assignments: list[dict[str, Any]] = []
                missing_questions: list[str] = []
                for targeted in latest_review.get("targeted_searches", []):
                    question_id = str(targeted.get("question_id", ""))
                    question = questions_by_id.get(question_id)
                    if not question:
                        missing_questions.append(question_id)
                        continue
                    remediation_assignments.append(
                        build_researcher_assignment(
                            root,
                            active_run_id,
                            question,
                            skill_dir / "config/budgets.toml",
                            remediation={
                                "critic_review_id": latest_review.get("id"),
                                **targeted,
                            },
                        )
                    )
                if remediation_assignments:
                    return _result(
                        root,
                        state,
                        "critic_remediation",
                        "delegate_targeted_searches",
                        agent="topic_researcher",
                        assignments=remediation_assignments,
                        blockers=[
                            f"Unknown targeted-search question IDs: {missing_questions}"
                        ]
                        if missing_questions
                        else [],
                        progress={
                            **progress,
                            "critic_review_id": previous_id,
                            "targeted_searches": len(remediation_assignments),
                        },
                    )
                return _result(
                    root,
                    state,
                    "critic_remediation",
                    "resolve_critic_findings_without_search",
                    blockers=[
                        item.get("required_action", "Resolve Critic finding")
                        for item in latest_review.get("findings", [])
                        if isinstance(item, dict)
                    ],
                    progress={**progress, "critic_review_id": previous_id},
                )
            return _result(
                root,
                state,
                "critic_recheck",
                "invoke_research_critic",
                agent="research_critic",
                assignments=[
                    build_critic_assignment(root, active_run_id, previous_id)
                ],
                progress={**progress, "previous_critic_review_id": previous_id},
            )
        return _result(
            root,
            state,
            "critic_recheck" if latest_review else "critic_review",
            "invoke_research_critic",
            agent="research_critic",
            assignments=[build_critic_assignment(root, active_run_id, previous_id)],
            blockers=["The previous approved Critic Review is stale."]
            if latest_review
            and latest_review.get("status") in {"approved", "approved_with_findings"}
            else [],
            progress={**progress, "previous_critic_review_id": previous_id},
        )

    audits: list[tuple[Path, dict[str, Any]]] = []
    for audit_path in sorted((root / "reports").glob("*.md.audit.json")):
        audit = read_json(audit_path, {})
        if audit.get("run_id") == active_run_id:
            audits.append((audit_path, audit))
    if not audits:
        started = _run_started_timestamp(root, active_run_id)
        reports = sorted(
            [
                path
                for path in (root / "reports").glob("*.md")
                if started is None or path.stat().st_mtime >= started - 2
            ],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        completed_reports: list[Path] = []
        for path in reports:
            text = path.read_text(encoding="utf-8")
            cited = set(CITATION_RE.findall(text))
            if not REPORT_TODO_RE.search(text) and bool(
                cited & accepted_evidence_ids
            ):
                completed_reports.append(path)
        if completed_reports:
            report = completed_reports[0]
            return _result(
                root,
                state,
                "report_audit",
                "initialize_quote_audit",
                command=f'qualityctl.py audit-init --report "{report}"',
                progress={
                    **progress,
                    "report": str(report),
                    "current_run_citations": sorted(
                        set(CITATION_RE.findall(report.read_text(encoding="utf-8")))
                        & accepted_evidence_ids
                    ),
                },
            )
        if not reports:
            return _result(
                root,
                state,
                "synthesis",
                "create_report_scaffold",
                command="research.py report --type final",
                progress=progress,
            )
        report = reports[0]
        return _result(
            root,
            state,
            "synthesis",
            "invoke_research_synthesizer",
            agent="research_synthesizer",
            command="agentctl.py synthesis-save --file synthesis-result.json",
            assignments=[
                build_synthesis_assignment(
                    root, active_run_id, report, approved_reviews[-1]
                )
            ],
            blockers=[
                "Synthesizer must return SynthesisResult v2 and may not search."
            ],
            progress={**progress, "report": str(report)},
        )

    valid_final_audits = [
        str(path)
        for path, _ in audits
        if validate_audit(path, require_all_verified=True)["valid"]
    ]
    if not valid_final_audits:
        return _result(
            root,
            state,
            "report_audit",
            "verify_quote_audit",
            agent="research_critic",
            command="qualityctl.py audit-validate --audit <path> --final",
            blockers=["No current-run Quote Audit is fully verified."],
            progress={**progress, "audit_count": len(audits)},
        )

    completion = completion_gate(root, active_run_id, skill_dir)
    if not completion["valid"]:
        return _result(
            root,
            state,
            "quality_remediation",
            "resolve_completion_gate_failures",
            blockers=completion["errors"],
            progress={
                **progress,
                "valid_final_audits": len(valid_final_audits),
            },
        )
    return _result(
        root,
        state,
        "ready_to_finish",
        "finish_complete_run",
        command="research.py finish --status complete",
        progress={
            **progress,
            "valid_final_audits": len(valid_final_audits),
            "passing_reports": completion.get("passing_reports", []),
        },
    )
