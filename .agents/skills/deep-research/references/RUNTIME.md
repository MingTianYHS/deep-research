# Runtime commands

`researchctl.py` is the deterministic control plane. It does not call an LLM or search provider.

## Topic setup

```bash
python scripts/researchctl.py init-topic "Topic" --budget standard --install-agent
python scripts/researchctl.py plan topic --questions 5
```

`--install-agent` creates a project-scoped `.codex/agents/topic-<slug>.toml` read-only recurring researcher.

## Run lifecycle

```bash
python scripts/researchctl.py run-start topic --mode initial
python scripts/researchctl.py status topic
python scripts/researchctl.py run-finish topic --status complete --note "summary"
```

Only one active run is allowed per topic. Finish with `partial` when useful evidence exists but a tool, source, or budget prevented completion. Finish with `failed` only when no useful deliverable was produced.

## Budget ledger

```bash
python scripts/researchctl.py budget topic
python scripts/researchctl.py record-usage topic \
  --queries 2 --pages 5 --input-tokens 8000 --output-tokens 1200
```

Usage deltas are non-negative. A delta that crosses a hard profile limit is rejected before the atomic state update. `--force` is an explicit emergency override and must be noted in the run log.

## Tool resolution

```bash
python scripts/researchctl.py tools web_search --all
python scripts/researchctl.py tools repo_read
```

Resolution returns enabled tools ordered by priority. It does not imply the tool is connected in the current Codex session; the coordinator must verify actual availability before use.

## Worker ingestion

A worker output file follows this envelope:

```json
{
  "question_id": "q-001",
  "queries_run": ["example query"],
  "sources_considered": 5,
  "evidence_cards": [
    {
      "source": {
        "url": "https://example.com/report",
        "title": "Example report",
        "publisher": "Example"
      },
      "statement": "One atomic factual proposition.",
      "quote": "Exact source text.",
      "locator": "Section 2",
      "stance": "support",
      "relevance": "core",
      "confidence": 0.8,
      "independence_group": "example-origin"
    }
  ],
  "gaps": [],
  "suggested_followups": []
}
```

Ingest with:

```bash
python scripts/researchctl.py ingest-worker topic --file worker-result.json
```

The command canonicalizes URLs, removes tracking parameters, generates stable IDs, rejects invalid confidence/stance/URL values, deduplicates by canonical URL plus normalized statement, enforces the remaining evidence-card budget, appends accepted cards, and updates usage.

## Validation

```bash
python scripts/researchctl.py validate topic
```

Validation checks required workspace files, evidence records, duplicate IDs, URL/card fields, and the tool registry.
