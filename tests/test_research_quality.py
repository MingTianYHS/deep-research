from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.report_rubric import evaluate_report, load_rubric
from lib.reports import scaffold


def evidence(card_id, group):
    return {"id": card_id, "source": {"publisher": group}, "independence_group": group, "prompt_injection_risk": "low"}


def test_compact_scaffold_has_six_sections(tmp_path):
    report = tmp_path / "report.md"
    claims = {"claim-1": {"relations": [{"evidence_id": "ev-1", "stance": "support"}]}}
    scaffold(report, "产品上线决策调研报告", "final", claims, "2026-08-01")
    text = report.read_text(encoding="utf-8")
    assert "## 核心结论" in text
    assert "## 冲突、限制与未解决问题" in text
    assert "## 核心主张与证据" not in text
    assert "## 调研质量说明" not in text
    assert "[[ev-1]]" in text


def test_hard_gate_rubric_accepts_compact_report(tmp_path):
    rubric = load_rubric(SCRIPT_DIR.parent / "config/report_rubric.toml")
    cards = {"ev-1": evidence("ev-1", "origin-a"), "ev-2": evidence("ev-2", "origin-b")}
    report = tmp_path / "good.md"
    report.write_text("""---
title: 产品上线决策调研报告
topic: 产品上线决策
report_type: final
status: complete
created: 2026-08-01
confidence: medium-high
---

# 产品上线决策调研报告

## 核心结论

当前证据支持有限上线，而非全面推广；这一判断受样本范围和测量口径限制。[[ev-1]][[ev-2]]

## 调研范围与方法

研究覆盖 2026 年公开的一手指标与独立分析，排除匿名推测，并记录证据截止日期和不可访问来源。

## 核心发现

一手来源在明确分母和目标人群后报告了 20% 的结果，但该数值只适用于原研究范围。[[ev-1]]

## 冲突、限制与未解决问题

独立分析指出测量方法与样本选择削弱外推效度；只有决策依赖跨人群推广时才需要继续取得底层记录。[[ev-2]]

## 决策启示与建议

更合理的行动是设置有限试点与退出门槛，而不是直接全面上线。[[ev-1]][[ev-2]]

## 来源

- [[ev-1]] 官方指标报告。
- [[ev-2]] 独立方法分析。
""", encoding="utf-8")
    result = evaluate_report(report, cards, rubric)
    assert result["passes_all_gates"], result
    assert result["score"] is None
    assert result["scoring_mode"] == "hard_gates_only"
