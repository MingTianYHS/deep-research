# Architecture

## Agent hierarchy

```text
User-directed main Codex session
├── topic_researcher
├── research_critic
└── research_synthesizer
```

There is no background scheduler or autonomous next-Run loop. `AGENTS.md` is a short boot protocol. The three custom agents are fixed read-only roles.

## Authority and memory layers

```text
Source Attempt → Evidence Card → Claim–Evidence
                                  ↓
                    bounded memory/report views
                                  ↓
                     next-research backlog
```

- `plans/current-design.json` is the active scoped question design.
- `plans/research-backlog.json` stores at most five optional future questions.
- `claims.jsonl`, `evidence/cards.jsonl`, and accepted Source Attempts are canonical research memory.
- Worker logs preserve prior Query intent and outcome for duplicate suppression.
- `memory/current.md` is bounded and rebuildable, never a fact store.
- `memory/knowledge-deltas.jsonl` preserves cross-Run cognitive change.
- `memory/lessons.jsonl` stores Critic-validated reusable research strategies.

## Runtime

The Skill uses Codex as the coordinator, fixed custom subagents, host/MCP search tools, standard-library control scripts, and append-only JSONL. It intentionally avoids LangGraph, queues, daemons, vector databases, raw-page caches, memory middleware, and duplicate Wikis.

## Workspace format 2

```text
<topic>/
├── AGENTS.md
├── topic.toml
├── state.json
├── context.md
├── questions.md
├── claims.jsonl
├── plans/
│   ├── current-design.json
│   └── research-backlog.json
├── evidence/cards.jsonl
├── memory/
│   ├── current.md
│   ├── knowledge-deltas.jsonl
│   └── lessons.jsonl
├── reports/
└── logs/
    ├── runs.jsonl
    ├── source_attempts.jsonl
    ├── workers/
    ├── critic_reviews/
    └── syntheses/
```

`state.usage` is reset for each Run; `state.lifetime_usage` is diagnostic history. The main session is the only writer. External content remains untrusted.
