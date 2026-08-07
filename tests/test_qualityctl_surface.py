import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts/qualityctl.py"
SPEC = importlib.util.spec_from_file_location("qualityctl", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


def test_quality_control_owns_all_quality_and_report_checks():
    root = module.parser()
    subparsers = next(action for action in root._actions if action.dest == "command")
    assert set(subparsers.choices) == {"quality-report", "report-check", "audit-init", "audit-mechanical", "audit-validate"}
