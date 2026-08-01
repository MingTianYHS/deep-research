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

## Quality-first flow

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py
DCTL=.agents/skills/deep-research/scripts/designctl.py
QCTL=.agents/skills/deep-research/scripts/qualityctl.py
ECTL=.agents/skills/deep-research/scripts/evalctl.py

python "$CTL" init-topic "Research topic" --budget standard --install-agent
python "$DCTL" init --title "Research topic" --output design.json
python "$DCTL" validate --file design.json --strict
# Codex runs bounded topic_researcher workers, one critic, then synthesis.
python "$CTL" verify-citations topic-slug --report report.md
python "$QCTL" quality-report topic-slug --require-gates
python "$QCTL" audit-init topic-slug --report report.md
python "$QCTL" audit-validate --audit report.md.audit.json --final
python "$ECTL" report-check topic-slug --report report.md --require-gates
```

## Quality model

The Skill checks source authority, directness, independence, specificity, freshness, question coverage, primary-source ratio, citation validity, material-paragraph citation coverage, quantitative citation coverage, conflict treatment, and uncertainty treatment. These are transparent review aids, not automatic truth scores.

The standard-library control plane owns deterministic validation and persistence. Codex owns planning, tool use, evidence interpretation, critique, and synthesis.
