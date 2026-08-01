import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts/researchctl.py"
spec = importlib.util.spec_from_file_location("researchctl", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_slugify_ascii():
    assert module.slugify("AI Market Research") == "ai-market-research"


def test_slugify_chinese():
    assert module.slugify("AI 短剧 行业") == "ai-短剧-行业"


def test_budget_profiles_exist():
    budgets = module.load_budgets()
    assert {"lite", "standard", "deep"}.issubset(budgets)
    assert budgets["standard"]["max_workers"] <= 5
