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
    values = []; directory = root / "logs/workers"
    if not directory.is_dir(): return values
    for path in sorted(directory.glob("*.json")):
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        if value.get("run_id") == run_id: values.append(value)
    return values


def _quality(root: Path, cards: list[dict[str, Any]], policy_file: Path, covered_question_ids: set[str]) -> dict[str, Any]:
    policy = load_policy(policy_file); result = evaluate(cards, policy, date.today()); design = read_json(root / "plans/current-design.json", {}); questions = [item for item in design.get("questions", []) if isinstance(item, dict) and item.get("id")]; question_ids = {str(item["id"]) for item in questions}; covered = question_ids.intersection(covered_question_ids); coverage = len(covered) / len(question_ids) if question_ids else 0.0; gates = policy["quality_gates"]
    result["question_count"] = len(question_ids); result["question_coverage"] = round(coverage, 4); result["gates"] = {"minimum_primary_source_ratio": result["primary_source_ratio"] >= float(gates["minimum_primary_source_ratio"]), "minimum_question_coverage": coverage >= float(gates["minimum_question_coverage"]), "maximum_high_risk_cards": len(result["high_risk_cards"]) <= int(gates["maximum_high_risk_cards"])}; result["passes_all_gates"] = all(result["gates"].values()); result["scoring_mode"] = "hard_gates_only"; return result


def completion_gate(root: Path, run_id: str, skill_dir: Path) -> dict[str, Any]:
    errors: list[str] = []; workers = _workers(root, run_id)
    if not workers: errors.append("complete run requires at least one persisted Worker Result for the active run")
    accepted_evidence_ids = {evidence_id for worker in workers for evidence_id in (worker.get("ingest_summary") or {}).get("accepted_evidence_ids", []) if isinstance(evidence_id, str)}; covered_question_ids = {str(worker.get("question_id")) for worker in workers if worker.get("status") == "complete" and (worker.get("ingest_summary") or {}).get("accepted_evidence_ids")}
    evidence = _evidence(root); run_cards = [card for evidence_id, card in evidence.items() if evidence_id in accepted_evidence_ids]
    if not run_cards: errors.append("complete run requires Evidence accepted or explicitly reused during the active run")
    critics = approved_reviews_for_run(root, run_id)
    if not critics: errors.append("complete run requires an approved persisted Critic Review for the active run")
    quality = _quality(root, run_cards, skill_dir / "config/source_policy.toml", covered_question_ids)
    if not quality["passes_all_gates"]: errors.append("complete run requires all active-run Evidence hard gates")
    report_candidates = []; rubric = load_rubric(skill_dir / "config/report_rubric.toml")
    for audit_path in sorted((root / "reports").glob("*.md.audit.json")):
        audit = read_json(audit_path, {})
        if audit.get("run_id") != run_id or not audit.get("report"): continue
        report_path = Path(audit["report"])
        if not report_path.exists(): continue
        report_candidates.append({"report": str(report_path), "audit": validate_audit(audit_path, require_all_verified=True), "citations": verify_report(report_path, evidence), "rubric": evaluate_report(report_path, evidence, rubric)})
    passing = [item for item in report_candidates if item["audit"]["valid"] and item["citations"]["valid"] and item["rubric"]["passes_all_gates"]]
    if not passing: errors.append("complete run requires a current-run citation-valid report that passes hard report gates and the profile audit")
    return {"valid": not errors, "errors": errors, "run_id": run_id, "worker_count": len(workers), "run_evidence_count": len(run_cards), "accepted_evidence_ids": sorted(accepted_evidence_ids), "covered_question_ids": sorted(covered_question_ids), "critic_review_ids": [item["id"] for item in critics], "quality_scope": "active_run", "quality": quality, "report_candidates": report_candidates, "passing_reports": [item["report"] for item in passing]}
