from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import utc_now


def refs(claim: dict[str, Any], stance: str | None = None) -> str:
    return " ".join(f"[[{item['evidence_id']}]]" for item in claim.get("relations", []) if stance is None or item.get("stance") == stance)


def claim_card(claim: dict[str, Any]) -> list[str]:
    claim_id = claim.get("id", "claim-unknown")
    support = refs(claim, "support") or "待补充"
    contradict = refs(claim, "contradict") or "无已记录的反对证据"
    return [
        f"> [!note]+ {claim_id} · {claim.get('status', 'draft')}",
        f"> **主张：** {claim.get('text', '待补充')}",
        f"> **认识类型：** {claim.get('epistemic_type', '待判定')}",
        f"> **置信度：** {claim.get('confidence', '待判定')}",
        f"> **支持证据：** {support}",
        f"> **反对或削弱证据：** {contradict}",
        "> **关键限制：** 待补充范围、口径、时间、样本或方法限制。",
        "> **什么会改变结论：** 待补充可观察的反证或更新条件。",
        "",
    ]


def scaffold(path: Path, title: str, report_type: str, claims: dict[str, dict[str, Any]], since: str | None) -> None:
    generated = utc_now(); topic = title.removesuffix("调研报告") or title
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims.values(): grouped.setdefault(claim.get("status", "draft"), []).append(claim)
    core = [claim for claim in claims.values() if claim.get("is_core")]
    evidence_ids = sorted({item.get("evidence_id") for claim in claims.values() for item in claim.get("relations", []) if item.get("evidence_id")})
    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"topic: {json.dumps(topic, ensure_ascii=False)}",
        f"report_type: {report_type}",
        "status: draft",
        f"created: {generated[:10]}",
        f"updated: {generated[:10]}",
        f"evidence_cutoff: {json.dumps(since or 'initial baseline', ensure_ascii=False)}",
        "confidence: pending",
        "tags:",
        "  - deep-research",
        f"  - report/{report_type}",
        "---",
        "",
        f"# {title}",
        "",
        f"所属主题：[[{topic}]]  ",
        f"生成时间：{generated}  ",
        f"证据截止：{since or '初始基线'}",
        "",
        "## 核心结论",
        "",
        "> [!abstract] 执行结论",
        "> 待补充：先直接回答研究问题，再给出整体置信度、最重要依据和最可能改变结论的限制。核心事实必须带 `[[ev-ID]]`。",
        "",
        "> [!warning] 最重要的限制",
        "> 待补充：只保留会实质改变决策的限制，不要罗列一般性免责声明。",
        "",
        "## 调研范围与方法",
        "",
        "待补充：研究问题、关键定义、时间窗口、地域、纳入与排除范围、搜索边界、证据截止日期，以及失败工具或不可访问来源。",
        "",
        "## 核心发现",
        "",
        "按研究问题组织内容。每节先写直接证据支持的事实，再明确标注推断、因果解释、预测或建议。保留日期、单位、分母、人口和地域。",
        "",
    ]
    supported = grouped.get("supported", [])
    if supported:
        for claim in supported: lines.extend(claim_card(claim))
    else:
        lines += ["> [!note] 尚无已支持主张", "> 待补充：完成 Claim–Evidence 审查后再写入核心发现。", ""]
    lines += ["## 冲突与削弱性证据", ""]
    contested = [claim for status in ("contested", "rejected", "unresolved") for claim in grouped.get(status, [])]
    if contested:
        for claim in contested: lines.extend(claim_card(claim))
    else:
        lines += ["> [!question] 冲突检查", "> 待补充：说明是否执行了反证搜索；若未发现冲突，也要说明搜索范围，不能直接声称不存在冲突。", ""]
    lines += [
        "## 决策启示与建议",
        "",
        "> [!tip] 启示与建议",
        "> 待补充：把观察事实、推断和建议分开。说明适用条件、权衡、行动门槛和不采取行动的代价，并引用支撑这些判断的证据。",
        "",
        "## 风险、不确定性与局限",
        "",
        "> [!caution] 不确定性",
        "> 待补充：列出单一来源、共同来源、陈旧或不可访问证据，数据口径差异、样本偏差，以及哪些结论对方法选择敏感。",
        "",
        "## 未解决问题与后续行动",
        "",
        "> [!todo] 高价值后续行动",
        "> 待补充：只保留可能改变结论或决策的问题，并写明需要什么证据、停止条件和优先级。",
        "",
        "## 核心主张与证据",
        "",
        "| ID | 核心主张 | 类型 | 状态 | 置信度 |",
        "|---|---|---|---|---:|",
    ]
    if core:
        for claim in core: lines.append(f"| {claim.get('id', '—')} | {claim.get('text', '待补充')} | {claim.get('epistemic_type', '待判定')} | {claim.get('status', 'draft')} | {claim.get('confidence', '待判定')} |")
        lines.append("")
        for claim in core: lines.extend(claim_card(claim))
    else:
        lines += ["| — | 待补充至少一个经过审查的核心主张 | 待判定 | draft | 待判定 |", ""]
    lines += ["## 来源", ""]
    if evidence_ids:
        lines.extend(f"- [[{evidence_id}]] — 待补充发布者、标题、发布日期、来源类型和独立来源组。" for evidence_id in evidence_ids)
    else:
        lines.append("- 待补充：仅列出报告实际引用且已接受的 Evidence Card。")
    lines += [
        "",
        "## 调研质量说明",
        "",
        "> [!info] 质量检查",
        "> 待补充：引用覆盖率、数字引用覆盖率、独立来源组数量、无效引用、高风险引用、冲突处理、Quote Audit 状态和未通过的质量门槛。",
        ">",
        "> 机械评分只能检查结构、引用和来源独立性，不能自动证明事实正确、因果有效或引文忠实。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(lines), encoding="utf-8")
