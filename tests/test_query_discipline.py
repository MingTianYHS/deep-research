from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.source_attempts import build_attempt
from lib.worker_contract import profile_limits, validate_worker_result


def query(query_id, text, intent, outcome="candidate_found", provider="native_web", fallback_of=None, time_anchor=None):
    return {"id": query_id, "query": text, "intent": intent, "provider": provider, "language": "en", "time_anchor": time_anchor, "fallback_of": fallback_of, "outcome": outcome}


def accepted_attempt(attempt_id="src-1", query_id="query-1"):
    return {"id": attempt_id, "url": "https://example.com/report", "normalized_url": "https://example.com/report", "status": "accepted", "eligible_for_evidence": True, "tool": "direct_fetch", "access_mode": "public_static", "content_sha256": "a" * 64, "http_status": 200, "source_version": "2026", "query_id": query_id, "discovery_method": "search", "discovered_via_source_attempt_id": None}


def evidence_card(source_attempt_id="src-1"):
    return {"id": "ev-1", "statement": "A bounded fact.", "stance": "support", "confidence": 0.8, "independence_group": "origin-a", "source_attempt_id": source_attempt_id, "prompt_injection_risk": "low", "version_compatibility": "exact", "quote": "A bounded fact.", "source": {"url": "https://example.com/report", "title": "Official report", "publisher": "Example", "source_type": "official"}}


def worker_result(profile="standard"):
    return {"worker_result_version": 2, "status": "complete", "question_id": "q-001", "overlap_key": "policy", "budget_profile": profile, "coverage_status": "sufficient", "queries_run": [query("query-1", "site:example.com official report 2026", "primary_source", "primary_candidate_found", time_anchor="2026")], "source_attempts": [accepted_attempt()], "evidence_cards": [evidence_card()], "gaps": [], "budget_used": {"tool_calls": 2, "search_queries": 1, "source_pages": 1}, "stop_reason": "acceptance_criteria_met"}


def validate(result): return validate_worker_result(result, profile_limits(result["budget_profile"]))


def test_compact_standard_worker_does_not_require_per_question_disconfirmation():
    checked = validate(worker_result())
    assert checked["valid"], checked["errors"]


def test_deep_worker_requires_disconfirming_query():
    result = worker_result("deep"); checked = validate(result)
    assert not checked["valid"] and any("disconfirming" in error for error in checked["errors"])
    result["queries_run"].append(query("query-2", "official report limitations", "disconfirming", "contradiction_found")); result["budget_used"]["search_queries"] = 2
    assert validate(result)["valid"]


def test_worker_v1_is_rejected():
    result = worker_result(); result.pop("worker_result_version")
    checked = validate(result)
    assert not checked["valid"] and any("must be 2" in error for error in checked["errors"])


def test_same_query_is_not_broadcast_to_multiple_providers():
    result = worker_result(); result["queries_run"].append(query("query-3", "site:example.com official report 2026", "primary_source", provider="tavily", time_anchor="2026"))
    assert any("broadcast" in error for error in validate(result)["errors"])


def test_fallback_depth_and_strategy_change_are_bounded():
    result = worker_result(); result["queries_run"].extend([query("query-3", "official report", "discovery", "low_yield"), query("query-4", "site:example.com official report", "primary_source", "low_yield", fallback_of="query-3"), query("query-5", "\"Official report\"", "exact_verification", "candidate_found", fallback_of="query-4")]); result.update(status="partial", coverage_status="partial", stop_reason="low_yield_after_fallback", gaps=[{"reason": "No independent primary source"}])
    assert any("fallback depth" in error for error in validate(result)["errors"])


def test_second_low_yield_requires_partial_status_stop_reason_and_gap():
    result = worker_result(); result["queries_run"].extend([query("query-3", "general source", "discovery", "low_yield"), query("query-4", "site:example.org primary source", "primary_source", "low_yield", fallback_of="query-3")])
    assert any("second low-yield" in error for error in validate(result)["errors"])


def test_search_attempt_requires_valid_query_id():
    result = worker_result(); result["source_attempts"][0]["query_id"] = "query-missing"
    assert any("valid query_id" in error for error in validate(result)["errors"])


def test_citation_backtrack_requires_query_and_accepted_parent():
    result = worker_result(); result["queries_run"].append(query("query-3", "Referenced study DOI", "citation_backtrack", "candidate_found")); child = accepted_attempt("src-2", "query-3"); child.update(url="https://example.org/study", normalized_url="https://example.org/study", discovery_method="citation_backtrack", discovered_via_source_attempt_id="src-missing"); result["source_attempts"].append(child)
    assert any("discovered_via_source_attempt_id" in error for error in validate(result)["errors"])


def test_version_check_requires_reproducible_anchor():
    result = worker_result(); result["queries_run"].append(query("query-3", "software release", "version_check"))
    assert any("time_anchor" in error for error in validate(result)["errors"])


def test_build_attempt_records_discovery_lineage():
    attempt = build_attempt("https://example.com/doc", "direct_fetch", 200, "content", query_id="query-1", discovery_method="search")
    assert attempt["query_id"] == "query-1" and attempt["discovery_method"] == "search" and attempt["discovered_via_source_attempt_id"] is None
