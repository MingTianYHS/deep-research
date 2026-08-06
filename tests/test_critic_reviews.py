import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.critic_reviews import validate_review


def base_review():
    return {
        "critic_review_version": 2,
        "id": "critic-1",
        "run_id": "run-1",
        "reviewed_by": "research_critic",
        "reviewed_snapshot": {},
        "status": "changes_required",
        "findings": [
            {
                "id": "finding-1",
                "severity": "high",
                "issue_type": "missing_primary_source",
                "question_id": "q-1",
                "evidence_ids": [],
                "explanation": "Only a secondary source is available.",
                "required_action": "Find the primary filing.",
            }
        ],
        "targeted_searches": [
            {
                "id": "targeted-1",
                "finding_id": "finding-1",
                "question_id": "q-1",
                "query": "site:example.gov filing",
                "intent": "primary_source",
                "required_evidence": "Primary filing",
                "stop_condition": "Filing found or official archive exhausted",
            }
        ],
        "unresolved": ["finding-1"],
        "stop_reason": "serious_findings_require_remediation",
    }


def test_version_two_targeted_search_contract_is_valid():
    checked = validate_review(base_review())
    assert checked["valid"], checked["errors"]


def test_targeted_search_must_reference_serious_finding():
    value = base_review()
    value["targeted_searches"][0]["finding_id"] = "missing"
    checked = validate_review(value)
    assert not checked["valid"]
    assert any("blocker/high" in error for error in checked["errors"])


def test_targeted_search_count_is_bounded():
    value = base_review()
    value["targeted_searches"] = [
        {**value["targeted_searches"][0], "id": f"targeted-{index}"}
        for index in range(4)
    ]
    checked = validate_review(value)
    assert not checked["valid"]
    assert any("at most 3" in error for error in checked["errors"])
