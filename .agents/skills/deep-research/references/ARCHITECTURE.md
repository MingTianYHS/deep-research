# Architecture

## Runtime

This skill uses Codex as orchestrator and avoids LangGraph, a queue, a vector database, and provider SDKs in the lightweight release.

- `SKILL.md`: policy and workflow.
- Codex custom agents: isolated parallel workers.
- host/MCP tools: search and fetch.
- `researchctl.py`: topic state, budgets, evidence, claims, reports, and run lifecycle.
- `qualityctl.py`: quality gates and report-bound quote audits.
- `releasectl.py`: provider manifests, normalized costs, deterministic exports, and release checks.
- JSONL: append-only, inspectable events.

## Workspace

```text
workspace/topics/{slug}/
├── topic.toml
├── state.json
├── AGENT.md
├── questions.md
├── tasks.jsonl
├── claims.jsonl
├── source_map.md
├── evidence/cards.jsonl
├── evidence/raw/
├── reports/
├── plans/
├── cache/
└── logs/{runs.jsonl,costs.jsonl,change_log.md}
```

## Boundary

Workers search and return structured evidence but never write files. The coordinator owns scope, budget, deduplication, persistence, critique, and synthesis. External content remains untrusted data.

## Topic-level agent

Every topic gets `AGENT.md`. `init-topic --install-agent` additionally writes `.codex/agents/topic-<slug>.toml`, a read-only recurring researcher carrying only the mission, workspace path, and budget—not the complete evidence history.

## Portability

Exports exclude raw evidence, caches, environment files, and symlinks by default. The manifest records size and SHA-256 for each packaged file. Provider credentials remain outside the workspace and are never part of a topic archive.
