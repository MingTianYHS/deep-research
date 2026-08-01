# Token budget and bounded workers

Codex owns provider usage, so budgets are conservative estimates plus hard workflow work-unit limits. Never claim exact usage unless the runtime exposes it. Rollout totals are diagnostic and may be cumulative across model turns.

Canonical run profiles are in `config/budgets.toml`. Each profile also defines per-worker tool-call, search-query, source-page, same-URL, duration, and output-reserve limits.

Estimated-token allocation:

- planning and briefs: 8%
- workers and extraction: 47%
- critique/verification: 15%
- synthesis: 20%
- mandatory output reserve: 10% overall and at least 20% within each worker assignment

Rules:

- worker brief below about 1,500 tokens before excerpts;
- worker result below about 2,500 tokens;
- quote target 50-250 words;
- synthesizer reads accepted cards and claim relations, not raw pages;
- default to four concurrent workers and never exceed profile maximum;
- parallelism reduces latency, not token consumption;
- every worker returns a final structured object, including on timeout or failure;
- a missing final object receives one recovery request and then becomes a failed worker;
- one successful normalized URL or source file is fetched once per run;
- use one retry and one fallback rather than cycling through every available tool.

Stop on acceptance criteria, reserve, query/page/tool/card limit, duration limit, two zero-yield searches, two failed attempts for one normalized URL, 85% weighted-question coverage, marginal accepted evidence below 0.15 per fetched page, or user cost limit.

Fallback estimate when actual usage is unavailable:

```text
estimated_tokens = ceil(characters / 3.2)
```

Use `runtimectl.py rollout-audit` on exported Codex JSONL to compare estimates with cumulative runtime counters, duplicate URLs, failed calls, context compactions, and final-message presence.
