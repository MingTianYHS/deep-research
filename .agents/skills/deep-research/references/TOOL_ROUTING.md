# Tool routing

Match required capabilities to enabled tools in `config/tools.toml`; do not bind the workflow to a vendor.

| Need | Preferred | Fallback |
|---|---|---|
| broad discovery | semantic/web search | news search |
| current events | news search | time-filtered web search |
| static official page | direct fetch | Jina reader |
| documentation site | scrape/map | crawl |
| dynamic/login page | browser | mark inaccessible |
| GitHub activity/code | GitHub MCP | public web search |

Cost-aware fetch order: direct fetch → reader → managed scrape/crawl → browser.

One worker owns one question, runs 2-4 queries, inspects 5-10 results per query, and fetches only 3-5 complementary pages. Stop after two low-yield queries. Retry transient failures once and use at most one fallback.
