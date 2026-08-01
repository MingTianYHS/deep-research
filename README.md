# deep-research

A lightweight, persistent deep-research skill for OpenAI Codex.

## Capabilities

- repository-scoped Codex skill and native parallel subagents
- pluggable host/MCP search and fetch routing
- persistent topic workspaces and optional topic-level agents
- hard Lite / Standard / Deep budgets and resumable runs
- evidence ingestion, Claim–Evidence event graph, and reviewed core transitions
- incremental plans and citation-aware report scaffolds
- source-type freshness, transparent quality scoring, and quote-fidelity audits
- prompt-injection isolation and coordinator-only writes

## Quick start

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py
QCTL=.agents/skills/deep-research/scripts/qualityctl.py

python "$CTL" init-topic "AI short drama market" --install-agent
python "$CTL" plan ai-short-drama-market --questions 5
python "$CTL" run-start ai-short-drama-market --mode initial
python "$CTL" ingest-worker ai-short-drama-market --file examples/worker-result.json
```

Build claims and a report:

```bash
python "$CTL" claim-create ai-short-drama-market --text "Example claim" --core
python "$CTL" claim-link ai-short-drama-market --claim cl-ID --evidence ev-ID --stance support --strength 0.8
python "$CTL" claim-status ai-short-drama-market --claim cl-ID --status supported --reason "evidence"
python "$CTL" claim-status ai-short-drama-market --claim cl-ID --status supported --reason "approved" --approve-core
python "$CTL" report-init ai-short-drama-market --type initial
```

Validate quality before final delivery:

```bash
REPORT=workspace/topics/ai-short-drama-market/reports/YYYYMMDD-initial.md
python "$CTL" verify-citations ai-short-drama-market --report "$REPORT"
python "$QCTL" quality-report ai-short-drama-market --require-gates
python "$QCTL" audit-init ai-short-drama-market --report "$REPORT"
python "$QCTL" audit-validate --audit "$REPORT.audit.json" --final
```

See `examples/end-to-end/` for the complete persisted data flow. The standard-library control plane owns deterministic state, budgets, validation, scoring, and recovery. Codex owns planning, native subagents, host/MCP tools, semantic extraction, critique, and synthesis.
