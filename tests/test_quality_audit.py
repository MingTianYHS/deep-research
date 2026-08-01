from datetime import date
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.audit import create_audit, validate_audit
from lib.io_utils import atomic_write_json
from lib.quality import evaluate, freshness_score, load_policy

POLICY = SCRIPT_DIR.parent / "config/source_policy.toml"


def card(evidence_id="ev-1", source_type="official", published_at="2026-07-25"):
    return {"id": evidence_id, "question_id": "q-1", "source": {"url": "https://example.com", "publisher": "Example", "source_type": source_type, "published_at": published_at}, "statement": "Fact", "quote": "Exact quote", "locator": "Section 1", "stance": "support", "independence_group": "example", "prompt_injection_risk": "low"}


def test_freshness_is_source_type_specific():
    policy = load_policy(POLICY)
    assert freshness_score("paper", "2026-07-25", policy, date(2026, 8, 1)) > freshness_score("news", "2026-07-25", policy, date(2026, 8, 1))


def test_quality_report_is_transparent_and_bounded():
    result = evaluate([card()], load_policy(POLICY), date(2026, 8, 1))
    assert result["primary_source_ratio"] == 1.0
    assert set(result["details"][0]["dimensions"]) == {"authority", "directness", "independence", "specificity", "freshness"}
    invalid = card("ev-2"); invalid["quality"] = {"authority": 2.0}
    try:
        evaluate([invalid], load_policy(POLICY), date(2026, 8, 1))
        assert False, "expected bounded quality dimension"
    except ValueError:
        pass


def test_audit_requires_metadata_and_unchanged_report(tmp_path):
    report = tmp_path / "report.md"; report.write_text("Fact [[ev-1]]", encoding="utf-8")
    output = tmp_path / "audit.json"; create_audit(report, {"ev-1": card()}, output)
    audit = __import__("json").loads(output.read_text()); audit["items"][0]["status"] = "verified"
    atomic_write_json(output, audit)
    assert not validate_audit(output, require_all_verified=True)["valid"]
    audit["items"][0]["checked_at"] = "2026-08-01T00:00:00Z"; audit["items"][0]["checked_by"] = "codex/reviewer"
    atomic_write_json(output, audit)
    assert validate_audit(output, require_all_verified=True)["valid"]
    report.write_text("Changed [[ev-1]]", encoding="utf-8")
    result = validate_audit(output, require_all_verified=True)
    assert not result["valid"]
    assert "report changed" in result["errors"][0]
