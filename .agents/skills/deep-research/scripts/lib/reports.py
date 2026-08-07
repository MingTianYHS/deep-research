from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import utc_now


def scaffold(path: Path, title: str, report_type: str, claims: dict[str, dict[str, Any]], since: str | None) -> None:
    """Create the compact six-section report contract.

    Lite/standard normally skip this step and synthesize directly. The scaffold
    remains for explicit use and the deep profile.
    """
    generated = utc_now(); topic = title.removesuffix("调研报告") or title
    evidence_ids = sorted({item.get("evidence_id") for claim in claims.values() for item in claim.get("relations", []) if item.get("evidence_id")})
    lines = [
        "---", f"title: {json.dumps(title, ensure_ascii=False)}", f"topic: {json.dumps(topic, ensure_ascii=False)}", f"report_type: {report_type}", "status: draft", f"created: {generated[:10]}", f"updated: {generated[:10]}", f"evidence_cutoff: {json.dumps(since or 'initial baseline', ensure_ascii=False)}", "confidence: pending", "tags: [deep-research]", "---", "",
        f"# {title}", "", "## 核心结论", "", "待补充：直接回答研究问题，给出置信度、关键依据和最重要限制。", "",
        "## 调研范围与方法", "", "待补充：定义、时间、地域、证据截止日期和不可访问来源。", "",
        "## 核心发现", "", "待补充：按问题呈现事实与解释，每个事实段落使用 [[ev-ID]]。", "",
        "## 冲突、限制与未解决问题", "", "待补充：只保留会改变结论的冲突、限制和缺口。", "",
        "## 决策启示与建议", "", "待补充：区分观察、推断和建议，并给出适用条件与退出门槛。", "",
        "## 来源", "",
    ]
    lines.extend(f"- [[{evidence_id}]]" for evidence_id in evidence_ids)
    if not evidence_ids: lines.append("- 待补充：仅列出实际引用且已接受的 Evidence Card。")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(lines), encoding="utf-8")
