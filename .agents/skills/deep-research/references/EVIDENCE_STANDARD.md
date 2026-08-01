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
  "statement": "One testable factual proposition.",
  "quote": "Exact source text.",
  "locator": "section, line range, page, or timestamp",
  "stance": "support",
  "relevance": "core",
  "confidence": 0.8,
  "independence_group": "origin-owner",
  "prompt_injection_risk": "low",
  "tags": []
}
```

Stance: `support`, `contradict`, `context`. Relevance: `core`, `supporting`, `background`.

Assess authority, directness, topic-relative freshness, specificity, and independence separately. Multiple articles repeating one press release are one independence group.

Claims are versioned interpretations linked to evidence relations. Do not auto-change a core claim from supported to rejected; create a proposed transition for review.

Deduplicate by canonical URL, normalized full-content hash, title/publisher/date, then near-duplicate text. Embeddings are optional and unnecessary for v0.1.
