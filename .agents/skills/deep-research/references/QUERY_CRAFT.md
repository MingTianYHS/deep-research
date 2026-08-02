# Query craft

Query craft is a bounded research behavior inside the Deep Research Skill. It is not a search engine, provider optimizer, evidence store, or replacement for Research Design.

```text
Research Question → Query Intent → Query → Source Attempt → Evidence Card → Claim
```

A query discovers candidate sources. It never proves a claim and never becomes Evidence by itself.

## Derive queries from Research Design

Before searching, inherit the assigned question's:

- core entities and decision relevance;
- inclusion and exclusion scope;
- time window, geography, population, units, and denominator;
- target version, release, commit, or data vintage;
- preferred source types and known URLs;
- acceptance criteria and supplied disconfirming query.

Do not broaden one Worker into a general review. Parallelize independent Research Questions at the coordinator layer; do not simulate breadth by broadcasting one query to several providers.

## Query intents

Every version-2 query event has exactly one intent:

| Intent | Purpose |
|---|---|
| `discovery` | Find stable entities, terminology, and promising source directions. |
| `primary_source` | Target official, original, first-party, or otherwise primary material. |
| `exact_verification` | Verify a stable title, identifier, quotation, error, or attribution. |
| `citation_backtrack` | Locate a referenced work discovered through an accepted source. |
| `disconfirming` | Seek exceptions, failures, contrary findings, or alternative explanations. |
| `cross_language` | Use an original or materially useful second language for coverage. |
| `version_check` | Verify a version, tag, commit, date range, or data vintage. |

A typical Worker uses `discovery`, `primary_source`, and `disconfirming`, then adds at most one intent needed by the question. Do not create two or three paraphrases for the same intent by default.

## Query ladder

1. **Discover:** core entity plus only the time, geography, action, or version needed to preserve scope.
2. **Target authority:** add an official domain, repository, scholarly index, regulator, publisher, or original-document identifier.
3. **Verify exactly:** use a stable title, document number, DOI, release, tag, commit, or short quotation.
4. **Disconfirm:** search for a material exception, failure, correction, retraction, counterexample, or competing explanation.
5. **Cross-check when material:** use the original language or one second language only when it can improve authority or coverage.
6. **Backtrack citations when valuable:** discover a referenced source, load it independently, and create a new Source Attempt before using it as Evidence.

The ladder is not a requirement to execute every step. Stop when acceptance criteria are met or a hard limit applies.

## Operators

- Use `"..."` for stable titles, policy names, identifiers, error strings, short quotations, or attribution checks.
- Use `site:` to target a known authority or source class. A domain restriction is not proof of authority.
- Use `filetype:` only to locate likely original documents or attachments. PDF format is not a quality signal.
- Use `-term` only after observed ambiguity dominates results.
- Use `OR` for at most three stable aliases.
- If an engine ignores or mishandles operators, make one plain-term strategy pivot rather than repeating operator variants.

## Time, version, and language

Use reproducible anchors such as `as_of`, an explicit time window, target version, tag, commit, release, or data vintage. Avoid relying on vague words such as “latest” when an explicit date is available.

Time or version anchoring is expected for markets, policy, news, finance, software, APIs, prices, rankings, and company status. It is not mandatory for stable mathematical facts, basic theory, or an explicitly all-time historical review.

Use the original language when it improves access to official or primary material. For locality-specific questions, search the local language first; for international technical questions, English is usually the discovery language. One material cross-language check is enough unless the Research Design requires more.

## Low yield and one pivot

Low yield is evidence-oriented, not result-count-oriented. A query is low-yield when its selected retrievals produce no new candidate capable of advancing acceptance criteria through primary, independent, contradictory, or version-matched evidence.

Examples include:

- duplicate or common-origin reporting only;
- snippets, abstracts, or metadata without accessible support for the material claim;
- no preferred source type when that type is required;
- inaccessible, high-risk, irrelevant, or version-mismatched material only;
- results that cannot reduce a stated uncertainty or gap.

After one low-yield query, make at most one strategy pivot: general to official, keyword to semantic, current name to historical name, one language to another, metadata to full text, positive to disconfirming, or web to a specialized primary-source route. Do not merely resend the same query to another provider.

If the pivot is also low-yield, stop that route and return `partial` or `failed` with `stop_reason = "low_yield_after_fallback"` and an explicit Gap.

## Citation backtracking

1. Record the accepted parent Source Attempt.
2. Create a `citation_backtrack` query event for the referenced work.
3. Load the referenced work independently.
4. Create a new Source Attempt with `discovered_via_source_attempt_id`.
5. Create Evidence only from the independently observed work.

Do not turn a bibliography entry, another author's summary, or an inaccessible reference into Evidence. Discovery lineage does not establish source independence; use the underlying origin when assigning `independence_group`.

## Query trace

Version-2 Worker Results record compact query events:

```json
{
  "id": "query-001",
  "query": "site:gov.cn 生成式人工智能 管理办法 2026",
  "intent": "primary_source",
  "provider": "native_web",
  "language": "zh-CN",
  "time_anchor": "2025-01-01/2026-08-02",
  "fallback_of": null,
  "outcome": "primary_candidate_found"
}
```

Allowed outcomes are `candidate_found`, `primary_candidate_found`, `independent_candidate_found`, `contradiction_found`, `duplicate_only`, `indirect_only`, `low_yield`, `quota_limited`, and `unavailable`.

Record only the event needed for audit. Do not store hidden reasoning, full result pages, credentials, or a second fact database.

## Source lineage

- `search`: requires a valid `query_id`.
- `known_url`: no query is required.
- `user_provided`: no query is required.
- `citation_backtrack`: requires a `citation_backtrack` query and an accepted `discovered_via_source_attempt_id`.

Search results remain discovery aids. Only accepted Source Attempts can support Evidence Cards.