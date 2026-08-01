# deep-research

A lightweight, persistent deep-research skill for OpenAI Codex.

## Capabilities

- repository-scoped Codex skill and native parallel subagents
- pluggable host/MCP search and fetch routing
- persistent topic workspaces and optional topic-level agents
- hard Lite / Standard / Deep budgets and resumable runs
- evidence ingestion, Claim–Evidence event graph, and reviewed core transitions
- incremental plans, citation-aware reports, quality gates, and quote audits
- provider manifests and normalized actual/estimated cost events
- deterministic topic export packages and release readiness checks
- prompt-injection isolation and coordinator-only writes

## Quick start

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py
QCTL=.agents/skills/deep-research/scripts/qualityctl.py
RCTL=.agents/skills/deep-research/scripts/releasectl.py

python "$CTL" init-topic "AI short drama market" --install-agent
python "$CTL" plan ai-short-drama-market --questions 5
python "$CTL" run-start ai-short-drama-market --mode initial
python "$CTL" ingest-worker ai-short-drama-market --file examples/worker-result.json
```

Record provider cost without hard-coding prices:

```bash
python "$RCTL" providers --name exa
python "$RCTL" cost-record ai-short-drama-market \
  --provider exa --operation search --quantity 2 --unit request \
  --cost-usd 0.014 --run-id run-ID --estimated
python "$RCTL" cost-summary ai-short-drama-market --run-id run-ID
```

Build and validate a report:

```bash
python "$CTL" claim-create ai-short-drama-market --text "Example claim" --core
python "$CTL" claim-link ai-short-drama-market --claim cl-ID --evidence ev-ID --stance support --strength 0.8
python "$CTL" report-init ai-short-drama-market --type initial
REPORT=workspace/topics/ai-short-drama-market/reports/YYYYMMDD-initial.md
python "$CTL" verify-citations ai-short-drama-market --report "$REPORT"
python "$QCTL" quality-report ai-short-drama-market --require-gates
python "$QCTL" audit-init ai-short-drama-market --report "$REPORT"
python "$QCTL" audit-validate --audit "$REPORT.audit.json" --final
```

Export and verify a topic handoff:

```bash
python "$RCTL" export-topic ai-short-drama-market
python "$RCTL" verify-package --package dist/ai-short-drama-market.deep-research.zip
python "$RCTL" release-check
```

See `examples/end-to-end/` for the persisted data flow. The standard-library control plane owns deterministic state, budgets, validation, accounting, packaging, and recovery. Codex owns planning, native subagents, host/MCP tools, semantic extraction, critique, and synthesis.
