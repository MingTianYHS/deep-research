# Architecture

## Runtime

This skill uses Codex as orchestrator and avoids LangGraph, a queue, a vector database, and provider SDKs in v0.1.

- `SKILL.md`: policy and workflow.
- Codex custom agents: isolated parallel workers.
- host/MCP tools: search and fetch.
- `researchctl.py`: deterministic workspace, state, validation, and budget inspection.
- JSONL: append-only, inspectable records.

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
├── cache/
└── logs/{runs.jsonl,change_log.md}
```

## Boundary

Workers search and return structured evidence but never write files. The coordinator owns scope, budget, deduplication, persistence, critique, and synthesis. This prevents concurrent-write conflicts, all-to-all agent chatter, and propagation of source instructions.

## Topic-level agent

Every topic gets `AGENT.md`. `init-topic --install-agent` additionally writes `.codex/agents/topic-<slug>.toml`, a read-only recurring researcher carrying only the mission, workspace path, and budget—not the complete evidence history.
