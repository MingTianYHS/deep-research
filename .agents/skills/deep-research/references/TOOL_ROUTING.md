# Tool routing

Match required capabilities to enabled tools in `config/tools.toml`; do not bind the workflow to a vendor. Read `PROVIDERS.md` when enabling a provider or recording cost.

| Need | Preferred | Fallback |
|---|---|---|
| OpenAI/Codex behavior | official docs MCP → version-pinned GitHub source | Context7 → Exa/web → browser/shell |
| GitHub activity/code | GitHub MCP at requested tag/commit | public web search |
| broad discovery | semantic/web search | news search |
| current events | news search | time-filtered web search |
| static official page | direct fetch | reader |
| documentation site | direct docs/search | scrape/map, then crawl |
| dynamic/login page | browser | mark inaccessible |

Cost-aware fetch order: direct source/MCP → reader → managed scrape/crawl → browser. Shell fetch is a last resort, not another automatic retry layer.

## Per-worker routing contract

- use the named `topic_researcher` for exactly one question;
- run 2-4 search queries by default and never exceed the assigned profile limit;
- inspect 5-10 results per query but fetch only complementary pages;
- normalize a URL before access, reuse an accepted result, and fetch one source file once;
- retry a transient failure once, then use one fallback;
- stop a normalized URL after two failed attempts;
- reject HTTP 4xx/5xx, error-page HTML, empty content, and known crawl timeout responses even when a process exits zero;
- hash accepted content and mark mirrored copies as the same origin;
- reserve at least 20% of the worker budget for its mandatory final JSON.

## Version-aware evidence

For software, API, schema, or configuration behavior, record the installed/requested version and prefer the matching release tag or commit. `main`-branch evidence may supplement but must be labeled `version_mismatch` when it cannot be tied to the target version.

For each paid operation, append a normalized cost event with `releasectl.py cost-record`. Preserve the provider's actual cost when available; otherwise mark the event estimated. Never hard-code a pricing-page value into routing logic.
