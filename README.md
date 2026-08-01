# deep-research

A lightweight, persistent deep-research skill for OpenAI Codex.

## Capabilities

- repository-scoped Codex skill and native parallel subagents
- pluggable host/MCP search and fetch routing
- persistent topic workspaces and optional topic-level agents
- hard Lite / Standard / Deep budgets and resumable runs
- evidence ingestion, URL canonicalization, and deduplication
- append-only Claim–Evidence graph with reviewed core-claim transitions
- incremental research plans and citation-verified report scaffolds
- prompt-injection isolation and coordinator-only writes

## Quick start

```bash
CTL=.agents/skills/deep-research/scripts/researchctl.py
python "$CTL" init-topic "AI short drama market" --install-agent
python "$CTL" plan ai-short-drama-market --questions 5
python "$CTL" run-start ai-short-drama-market --mode initial
```

After subagents return structured results:

```bash
python "$CTL" ingest-worker ai-short-drama-market --file examples/worker-result.json
python "$CTL" claim-create ai-short-drama-market --text "Example claim" --core
python "$CTL" claim-link ai-short-drama-market --claim cl-ID --evidence ev-ID --stance support --strength 0.8
python "$CTL" claim-status ai-short-drama-market --claim cl-ID --status supported --reason "reviewed evidence"
python "$CTL" claim-status ai-short-drama-market --claim cl-ID --status supported --reason "approved" --approve-core
python "$CTL" report-init ai-short-drama-market --type initial
python "$CTL" verify-citations ai-short-drama-market --report workspace/topics/ai-short-drama-market/reports/YYYYMMDD-initial.md
python "$CTL" run-finish ai-short-drama-market --status complete
```

For later runs:

```bash
python "$CTL" incremental-plan ai-short-drama-market
python "$CTL" run-start ai-short-drama-market --mode incremental
```

The standard-library control plane owns deterministic state, budgets, evidence/claim validation, deduplication, citation structure, and recovery boundaries. Codex owns planning, native subagents, host/MCP tools, semantic extraction, critique, and synthesis.
