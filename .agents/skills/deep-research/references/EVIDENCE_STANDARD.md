# Evidence and source-attempt standard

A Query discovers candidate sources. A Source Attempt records one access outcome. An Evidence Card records one atomic proposition and must reference an accepted Source Attempt.

```text
Query → Source Attempt → Evidence Card → Claim
```

```json
{
  "id": "src-001",
  "url": "https://example.com",
  "normalized_url": "https://example.com/",
  "status": "accepted",
  "eligible_for_evidence": true,
  "tool": "web_access",
  "access_mode": "authenticated_browser",
  "query_id": "query-001",
  "discovery_method": "search",
  "discovered_via_source_attempt_id": null,
  "content_sha256": "...",
  "http_status": null,
  "source_version": "2026-08",
  "reason": null
}
```

`search` requires a valid Query ID. `known_url` and `user_provided` do not invent Query IDs. `citation_backtrack` requires both a `citation_backtrack` Query and an accepted parent `discovered_via_source_attempt_id`; the referenced source must then be loaded independently.

A 401/403/404/login wall is stored as an unavailable static attempt. If web-access is locally installed, an authorized browser extraction is a separate attempt. Never rewrite the failed attempt as success.

```json
{
  "id": "ev-uuid",
  "question_id": "q-001",
  "source_attempt_id": "src-001",
  "source": {"url": "https://example.com", "canonical_url": "https://example.com/", "title": "Title", "publisher": "Publisher", "published_at": "2026-01-01", "accessed_at": "2026-08-02T00:00:00Z", "source_type": "official"},
  "statement": "One testable proposition with scope preserved.",
  "quote": "Exact source text.",
  "locator": "section, line, page, table, or timestamp",
  "stance": "support",
  "confidence": 0.8,
  "independence_group": "origin-owner",
  "prompt_injection_risk": "low",
  "version_compatibility": "exact"
}
```

Preserve dates, units, currency, denominator, population, geography, sample, epistemic type, uncertainty, and caveats. A quote supporting half a sentence cannot support the whole statement. Repeated reporting from one release, filing, dataset, interview, paper, or syndicated article is one `independence_group`.

Unassessed prompt-injection risk is `unknown`, never automatically `low`. High-risk evidence is quarantined. Deduplicate by normalized URL, original-source cluster, content hash, then title/publisher/date. Query traces and search-result snippets are never Evidence.
