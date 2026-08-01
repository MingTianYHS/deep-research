from pathlib import Path
import json
import sys

SCRIPT_DIR = Path(__file__).parents[1] / ".agents/skills/deep-research/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.report_rubric import evaluate_report, load_rubric
from lib.reports import scaffold
from lib.research_design import validate_design


def evidence(card_id, group):
    return {"id": card_id, "source": {"publisher": group}, "independence_group": group, "prompt_injection_risk": "low"}


def test_research_design_validates_parallel_boundaries():
    design = json.loads((Path(__file__).parents[1] / "examples/evaluation/research-design.json").read_text())
    result = validate_design(design)
    assert result["valid"]
    assert result["parallel_groups"] == [["q-001"], ["q-002"]]
    design["questions"][1]["overlap_key"] = "primary-outcomes"
    assert not validate_design(design)["valid"]


def test_obsidian_scaffold_is_a_quality_contract(tmp_path):
    report = tmp_path / "report.md"
    claims = {"claim-1": {"id": "claim-1", "text": "有限试点比全面上线更符合当前证据。", "status": "supported", "confidence": 0.8, "is_core": True, "relations": [{"evidence_id": "ev-1", "stance": "support"}]}}
    scaffold(report, "产品上线决策调研报告", "final", claims, "2026-08-01")
    text = report.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "> [!abstract] 执行结论" in text
    assert "## 冲突与削弱性证据" in text
    assert "## 核心主张与证据" in text
    assert "[[ev-1]]" in text
    rubric = load_rubric(SCRIPT_DIR.parent / "config/report_rubric.toml")
    result = evaluate_report(report, {"ev-1": evidence("ev-1", "origin-a")}, rubric)
    assert not result["passes_all_gates"]
    assert result["todo_markers"] > 0


def test_report_rubric_distinguishes_substantive_obsidian_report(tmp_path):
    rubric = load_rubric(SCRIPT_DIR.parent / "config/report_rubric.toml")
    cards = {"ev-1": evidence("ev-1", "origin-a"), "ev-2": evidence("ev-2", "origin-b")}
    good = tmp_path / "good.md"
    good.write_text("""---
title: 产品上线决策调研报告
topic: 产品上线决策
report_type: final
status: complete
created: 2026-08-01
confidence: medium-high
tags: [deep-research, report/final]
---

# 产品上线决策调研报告

## 核心结论

> [!abstract] 执行结论
> 当前证据支持有限上线，而非全面推广；这一判断主要受样本范围和测量口径限制。[[ev-1]][[ev-2]]

## 调研范围与方法

本次研究覆盖 2026 年已公开的一手指标与独立分析，排除匿名推测，并记录搜索边界、不可访问来源和证据截止日期。

## 核心发现

一手来源在明确分母和目标人群后报告了 20% 的结果，但该数值只适用于原研究范围，不能推广到全部用户。[[ev-1]]

## 冲突与削弱性证据

独立分析指出测量方法和样本选择会削弱外推效度，因此不能把原始结果解释为普遍成功或确定性因果关系。[[ev-2]]

## 决策启示与建议

基于现有证据，更合理的行动是设置有限试点与退出门槛，而不是将观察结果直接转化为全面上线建议。[[ev-1]][[ev-2]]

## 风险、不确定性与局限

结果可能无法迁移到其他人群，底层记录仍不可访问，且两个来源使用不同方法；这些限制会实质影响置信度。[[ev-1]][[ev-2]]

## 未解决问题与后续行动

只有当最终决策依赖跨人群推广时，才需要取得底层记录并复核指标口径；否则应在有限试点达到停止条件后结束搜索。

## 核心主张与证据

核心主张是“有限试点优于全面上线”，它属于有条件建议，由一手结果支持，并受到独立方法分析的削弱。[[ev-1]][[ev-2]]

## 来源

- [[ev-1]] — 官方指标报告，2026-07-01，一手来源，独立来源组 origin-a。
- [[ev-2]] — 独立方法分析，2026-07-15，二手分析，独立来源组 origin-b。

## 调研质量说明

> [!info] 质量检查
> 报告披露引用覆盖、数字引用、来源独立性、冲突处理和不确定性；机械评分不证明事实或因果正确。
""", encoding="utf-8")
    result = evaluate_report(good, cards, rubric)
    assert result["passes_all_gates"]
    assert result["yaml_frontmatter"]
    assert result["todo_markers"] == 0
    bad = tmp_path / "bad.md"
    bad.write_text("# 报告\n\n## 核心发现\n一个 99% 的结果证明普遍成功，其他部分待补充。\n", encoding="utf-8")
    bad_result = evaluate_report(bad, cards, rubric)
    assert not bad_result["passes_all_gates"]
    assert not bad_result["gates"]["yaml_frontmatter"]
    assert not bad_result["gates"]["maximum_todo_markers"]
