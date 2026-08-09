# Architecture

## Agent hierarchy

```text
User-directed main Codex session
├── topic_researcher
├── research_critic
└── research_synthesizer
```

There is no background scheduler or autonomous next-Run loop. `AGENTS.md` is a short boot protocol. The three custom agents are fixed read-only roles, and the main session is the only workspace writer.

## Authority and memory layers

```text
Source Attempt → Evidence Card → Claim–Evidence
       ↓              ↓
Verification event ───┘
                      ↓
          bounded memory/report views
                      ↓
           next-research backlog
```

- `plans/current-design.json` is the active scoped question design.
- `plans/research-backlog.json` stores at most five optional future questions.
- `claims.jsonl`, `evidence/cards.jsonl`, accepted Source Attempts, and valid Verification events are canonical research memory.
- Worker logs preserve prior Query intent and outcome for duplicate suppression.
- `memory/current.md` is bounded and rebuildable, never a fact store.
- `memory/knowledge-deltas.jsonl` preserves cross-Run cognitive change.
- `memory/lessons.jsonl` stores Critic-validated reusable research strategies.

## Versioned boundary

ResearcherAssignment v2 sends only the current question, observable budgets, and a bounded `research_context`. Worker Result v2 is validated before atomic ingestion. CriticAssignment v2 binds one full review and, for Lite/Standard only when required, one targeted recheck to the current Snapshot v2. The snapshot includes effective Verification IDs and hashes, so refreshed Evidence invalidates stale reviews. SynthesisResult v2 is search-free and writes a bounded knowledge delta and backlog.

## Runtime

The Skill uses Codex as the coordinator, fixed custom subagents, host/MCP search tools, standard-library control scripts, and append-only JSONL. It intentionally avoids LangGraph, queues, daemons, vector databases, raw-page caches, memory middleware, and duplicate Wikis.

## Workspace Format 3

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
│   ├── research-backlog.json
│   └── history/
├── evidence/
│   ├── cards.jsonl
│   └── verifications.jsonl
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

`state.usage` resets for each Run; `state.lifetime_usage` is diagnostic history. `active_run_scope` freezes the Design hash and every assigned question. Format 1, Format 2, and unversioned workspaces are rejected; they are not migrated automatically. External content remains untrusted.
