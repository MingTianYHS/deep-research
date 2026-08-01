# Token budget and parallelism

Codex owns provider usage, so budgets are conservative estimates plus hard work-unit limits. Never claim exact usage unless the runtime exposes it.

Canonical profiles are in `config/budgets.toml`.

Estimated-token allocation:

- planning and briefs: 8%
- workers and extraction: 52%
- critique/verification: 15%
- synthesis: 20%
- reserve: at least 5%

Rules:

- worker brief below about 1,500 tokens before excerpts;
- worker result below about 2,500 tokens;
- quote target 50-250 words;
- synthesizer reads accepted cards and claim relations, not raw pages;
- default to four concurrent workers and never exceed profile maximum;
- parallelism reduces latency, not token consumption.

Stop on reserve, query/page/card limit, two zero-yield waves, 85% weighted-question coverage, marginal accepted evidence below 0.15 per fetched page, or user cost limit.

Fallback estimate when actual usage is unavailable:

```text
estimated_tokens = ceil(characters / 3.2)
```
