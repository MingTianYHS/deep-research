# deep-research

A lightweight, citation-first deep-research Skill for OpenAI Codex.

**Release candidate:** `0.7.0rc1` · Python 3.11+

## What it optimizes

- decision-relevant question decomposition
- bounded, non-overlapping Codex subagents
- expected-answer and disconfirming searches
- primary-source preference and common-origin clustering
- atomic Evidence Cards and reviewed Claim–Evidence relations
- one adversarial critic pass and one targeted gap wave
- calibrated synthesis with conflict and uncertainty
- structural citations, quote audits, and mechanical report-quality gates
- Lite / Standard / Deep token budgets

It intentionally has no scheduler, daemon, queue, vector database, or heavyweight agent framework.

## Workspace location

By default, topic workspaces are stored at `workspace/topics` inside the repository. Set `DEEP_RESEARCH_WORKSPACE_ROOT` to keep private research data elsewhere.

Windows PowerShell, current session:

```powershell
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
```

Persist for the current Windows user, then reopen Codex or the terminal:

```powershell
[Environment]::SetEnvironmentVariable(
  'DEEP_RESEARCH_WORKSPACE_ROOT',
  'D:\知识宇宙海\调研工作区',
  'User'
)
```

Codex must be allowed to read and write that directory. Topic folders may use Chinese. Windows-invalid filename characters are replaced with `-`, and reserved names such as `CON` are made safe.

For a topic named `AI短剧市场研究`, the default report names are:

```text
20260801-AI短剧市场研究.md
20260801-AI短剧市场研究-更新.md
20260801-AI短剧市场研究-最终.md
```

The date uses the host's local date. Internal IDs such as `q-001`, `ev-001`, and `claim-001` remain stable ASCII identifiers.

## Quality-first flow

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py
DCTL=.agents/skills/deep-research/scripts/designctl.py
QCTL=.agents/skills/deep-research/scripts/qualityctl.py
ECTL=.agents/skills/deep-research/scripts/evalctl.py

python "$CTL" init-topic "AI短剧市场研究" --budget standard --install-agent
python "$DCTL" init --title "AI短剧市场研究" --output design.json
python "$DCTL" validate --file design.json --strict
# Codex runs bounded topic_researcher workers, one critic, then synthesis.
python "$CTL" report-init ai短剧市场研究 --type initial
python "$CTL" verify-citations ai短剧市场研究 --report report.md
python "$QCTL" quality-report ai短剧市场研究 --require-gates
python "$QCTL" audit-init ai短剧市场研究 --report report.md
python "$QCTL" audit-validate --audit report.md.audit.json --final
python "$ECTL" report-check ai短剧市场研究 --report report.md --require-gates
```

## Quality model

The Skill checks source authority, directness, independence, specificity, freshness, question coverage, primary-source ratio, citation validity, material-paragraph citation coverage, quantitative citation coverage, conflict treatment, and uncertainty treatment. These are transparent review aids, not automatic truth scores.

The standard-library control plane owns deterministic validation and persistence. Codex owns planning, tool use, evidence interpretation, critique, and synthesis.
