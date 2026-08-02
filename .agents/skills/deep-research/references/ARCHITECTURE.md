# Architecture

## Agent hierarchy

```text
Main Codex session in topic workspace (topic-expert coordinator)
├── topic_researcher
├── research_critic
└── research_synthesizer
```

`AGENTS.md` activates the coordinator. The three user-level custom agents are fixed read-only execution roles. Per-topic Agent TOML files are deprecated because they duplicate the coordinator, drift from contracts, and do not provide learning.

## Authority layers

```text
Source Attempt → Evidence Card → Claim–Evidence → context/report views
```

- `plans/current-design.json` is the canonical question design.
- `questions.md` and `state.open_questions` are synchronized views.
- `context.md` is bounded and rebuildable, never a fact store.
- `memory/lessons.jsonl` stores only validated reusable research strategies.
- Run logs remain raw events; Lessons are distilled future-facing experience.

## Runtime

The Skill uses Codex as orchestrator, fixed custom subagents, host/MCP search tools, standard-library control scripts, and append-only JSONL. It intentionally avoids LangGraph, queues, daemons, vector databases, memory middleware, and duplicate Wikis.

## Workspace format 2

```text
<topic>/
├── AGENTS.md
├── topic.toml
├── state.json
├── context.md
├── questions.md
├── source_map.md
├── tasks.jsonl
├── claims.jsonl
├── plans/current-design.json
├── evidence/cards.jsonl
├── memory/lessons.jsonl
├── reports/
└── logs/
```

The main session is the only writer. Subagents return structured results. External content remains untrusted.
