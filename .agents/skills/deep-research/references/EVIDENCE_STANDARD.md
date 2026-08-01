# Evidence and claim standard

Each evidence card is one atomic proposition, not a page summary.

```json
{
  "id": "ev-uuid",
  "question_id": "q-001",
  "source": {
    "url": "https://example.com",
    "canonical_url": "https://example.com",
    "title": "Title",
    "publisher": "Publisher",
    "published_at": "2026-01-01",
    "accessed_at": "2026-08-01T00:00:00Z",
    "source_type": "official"
  },
  "statement": "One testable factual proposition with scope preserved.",
  "quote": "Exact source text.",
  "locator": "section, line range, page, table, or timestamp",
  "stance": "support",
  "relevance": "core",
  "confidence": 0.8,
  "independence_group": "origin-owner",
  "prompt_injection_risk": "low",
  "tags": []
}
```

## Atomicity and entailment

A card should be usable or rejectable as one unit. Preserve:

- observation/event date separately from publication/access date;
- units, currency, denominator, population, geography, and sample size;
- whether the source reports an observation, author interpretation, forecast, or recommendation;
- uncertainty intervals and caveats that materially change meaning.

A quote that supports only half of a sentence cannot support the whole statement. Split the statement or add evidence.

## Independence

Multiple pages are not independent when they derive from one press release, filing, dataset, interview, paper, or syndicated article. Use that common origin as `independence_group`. Independent interpretation of the same dataset may add analytical diversity but not a second underlying observation.

## Contradiction search

For every core question, search at least one plausible disconfirming formulation. Preserve negative, null, and weakening evidence. Do not force conflicts into a false consensus; explain differences in population, date, method, or definition.

Assess authority, directness, topic-relative freshness, specificity, and independence separately. Claims are versioned interpretations linked through support, contradict, and context relations. Core-claim status changes require review.

Deduplicate by canonical URL, original-source cluster, normalized content hash, then title/publisher/date. Embeddings remain optional and unnecessary for this lightweight Skill.
