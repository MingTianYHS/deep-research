# Token budget and bounded workers

Codex owns provider usage. Budgets combine one canonical `config/budgets.toml` profile with work-unit limits. Worker values are self-reported unless a Rollout is supplied for observed custom-Agent/final-message/tool-call verification.

Profiles define total workers/questions/queries/pages/cards/tokens and per-worker tool calls, queries, pages, same-URL attempts, duration, and 20% output reserve. Parallelism reduces latency, not consumption.

Rules: Worker brief below about 1,500 tokens; result below about 2,500; quote target 50-250 words; synthesizer reads accepted cards/claims, not raw pages; every Worker returns a final object; one recovery request for a missing final; one retry plus one fallback; one accepted normalized URL fetch per run.

Stop on acceptance criteria, any work-unit/duration limit, output reserve, two low-yield searches, two failed attempts for one URL, or low marginal evidence yield. Rollout counters are diagnostic and host billing remains authoritative.
