import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("qualityctl", SCRIPT_DIR / "qualityctl.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


def test_quality_control_owns_all_quality_and_report_checks():
    root = module.parser()
    subparsers = next(action for action in root._actions if action.dest == "command")
    assert set(subparsers.choices) == {"quality-report", "report-check", "audit-init", "audit-mechanical", "audit-validate"}
