# Tool routing

Tool routing answers **which available route should execute an already constructed query**. Query construction and stopping rules live in `QUERY_CRAFT.md`.

Use the highest-authority available route, select one provider per query, and do not assume that a declared provider is connected or has remaining quota.

| Need | Preferred | One bounded fallback |
|---|---|---|
| General discovery, official pages, exact entities | native web | Tavily |
| Current web/news or structured web extraction | Tavily | native web |
| Semantic discovery or uncertain terminology | Exa | native web |
| GitHub repository, issue, PR, release, tag, commit | GitHub MCP at requested tag/commit | public web |
| Known static URL | direct fetch | Jina |
| Dynamic or complex extraction | Firecrawl | web-access |
| Authorized login/anti-bot page | installed web-access Skill | host browser, otherwise unavailable |
| OpenAI/Codex behavior | official docs → version-pinned GitHub | Context7 → web |

Default registry order remains:

```text
search: native_web → tavily → exa
fetch: direct_fetch → jina → firecrawl → web_access → browser
```

This order is a policy preference, not a command to call every provider. A low-yield query may receive one strategy pivot; do not resend the same query unchanged across the chain.

Per Worker: 2-4 query intents by default, one accepted URL fetch, one transient retry, one strategy pivot, at most two attempts for one normalized URL, and at least 20% final-output reserve.

A static 401/403/404/error page is unavailable. When web-access is installed, use it once in read-only research mode with the user's authorized session. Do not extract credentials or perform account-changing actions. Record failed static and accepted browser attempts separately; only the accepted attempt may back Evidence.

For software/API/configuration behavior, record the target version and prefer its release tag or commit. Main-branch evidence is `mismatch` unless tied to the requested version.

Quota exhaustion or HTTP 429 may trigger one free-route strategy pivot. Never enable paid overage, auto-recharge, or automatic multi-account/API-key rotation.