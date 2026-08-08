# Work-unit budget and bounded context

Codex owns provider Token accounting. This Skill does not estimate or enforce fictional Token totals. It enforces observable work units: search Queries, fetched source pages, newly accepted Evidence Cards, per-worker tool calls, and coordinator steps.

`state.usage` belongs to the active Run and resets at Run start. `state.lifetime_usage` accumulates diagnostics but never prevents another Run. Explicitly reused Evidence consumes no Query, page, or new-card budget.

Keep inputs bounded:

- `memory/current.md`: at most 8,000 characters;
- reuse plan: at most 8 Evidence, 8 sources, 8 prior Queries, 8 relevant Claims, and 5 backlog items;
- report follow-up backlog: at most 5 items;
- Worker output: compact lineage and at most two material gaps;
- Synthesizer: reviewed Claims/Evidence, never raw pages.

Search rules:

1. reuse sufficient fresh Evidence before tools;
2. refresh a known stale URL before broad discovery;
3. do not repeat a historical Query without an explicit reason;
4. use one strategy-changing fallback after low yield;
5. stop at acceptance criteria or a hard work-unit budget.

Parallelism reduces latency, not consumption. Host billing remains authoritative.
