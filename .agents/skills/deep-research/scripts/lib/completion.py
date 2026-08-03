from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .audit import validate_audit
from .citations import verify_report
from .critic_reviews import approved_reviews_for_run
from .io_utils import iter_jsonl, read_json
from .quality import evaluate, load_policy
from .report_rubric import evaluate_report, load_rubric


def _evidence(root: Path) -> dict[str, dict[str, Any]]: return {item["id"]: item for _, item in iter_jsonl(root / "evidence/cards.jsonl") if item.get("id")}

def _workers(root: Path, run_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []; directory = root / "logs/workers"
    if not directory.is_dir(): return values
    for path in sorted(directory.glob("*.json")):
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        if value.get("run_id") == run_id: values.append(value)
    return values

def _quality(root: Path, cards: list[dict[str, Any]], policy_file: Path) -> dict[str, Any]:
    policy = load_policy(policy_file); result = evaluate(cards, policy, date.today()); design = read_json(root / "plans/current-design.json", {}); questions = [item for item in design.get("questions", []) if isinstance(item, dict) and item.get("id")]; question_ids = {item["id"] for item in questions}; covered = {item.get("question_id") for item in cards if item.get("question_id") in question_ids and item.get("prompt_injection_risk") != "high"}; coverage = len(covered) / len(question_ids) if question_ids else 0.0; gates = policy["quality_gates"]
    result["question_count"] = len(question_ids); result["question_coverage"] = round(coverage, 4); result["gates"] = {"minimum_card_score": result["average_score"] >= float(gates["minimum_card_score"]), "minimum_primary_source_ratio": result["primary_source_ratio"] >= float(gates["minimum_primary_source_ratio"]), "minimum_question_coverage": coverage >= float(gates["minimum_question_coverage"]), "maximum_high_risk_cards": len(result["high_risk_cards"]) <= int(gates["maximum_high_risk_cards"])}; result["passes_all_gates"] = all(result["gates"].values()); return result


def completion_gate(root: Path, run_id: str, skill_dir: Path) -> dict[str, Any]:
    errors: list[str] = []; workers = _workers(root, run_id)
    if not workers: errors.append("complete run requires at least one persisted Worker Result for the active run")
    accepted_attempts = {attempt.get("id") for worker in workers for attempt in worker.get("source_attempts", []) if isinstance(attempt, dict) and attempt.get("status") == "accepted" and attempt.get("eligible_for_evidence")}; evidence = _evidence(root); run_cards = [card for card in evidence.values() if card.get("source_attempt_id") in accepted_attempts]
    if not run_cards: errors.append("complete run requires accepted Evidence from the active run")
    critics = approved_reviews_for_run(root, run_id)
    if not critics: errors.append("complete run requires an approved persisted Critic Review for the active run")
    quality = _quality(root, list(evidence.values()), skill_dir / "config/source_policy.toml")
    if not quality["passes_all_gates"]: errors.append("complete run requires all live Evidence quality gates")
    report_candidates: list[dict[str, Any]] = []; rubric = load_rubric(skill_dir / "config/report_rubric.toml")
    for audit_path in sorted((root / "reports").glob("*.md.audit.json")):
        audit = read_json(audit_path, {})
        if audit.get("run_id") != run_id: continue
        report_value = audit.get("report")
        if not report_value: continue
        report_path = Path(report_value)
        if not report_path.exists(): continue
        citation = verify_report(report_path, evidence); audit_result = validate_audit(audit_path, require_all_verified=True); rubric_result = evaluate_report(report_path, evidence, rubric); report_candidates.append({"report": str(report_path), "audit": audit_result, "citations": citation, "rubric": rubric_result})
    passing_reports = [item for item in report_candidates if item["audit"]["valid"] and item["citations"]["valid"] and item["rubric"]["passes_all_gates"]]
    if not passing_reports: errors.append("complete run requires a current-run citation-valid report that passes rubric gates and final Quote Audit")
    return {"valid": not errors, "errors": errors, "run_id": run_id, "worker_count": len(workers), "run_evidence_count": len(run_cards), "critic_review_ids": [item["id"] for item in critics], "quality": quality, "report_candidates": report_candidates, "passing_reports": [item["report"] for item in passing_reports]}
