# Tool routing

Use the highest-authority available route and do not assume a declared provider is connected.

| Need | Preferred | Fallback |
|---|---|---|
| OpenAI/Codex behavior | official docs → version-pinned GitHub | Context7 → web |
| GitHub code/activity | GitHub MCP at requested tag/commit | public web |
| broad discovery | web/semantic search | news search |
| static official page | direct fetch | Jina/reader |
| authorized login/anti-bot/dynamic page | installed web-access Skill | host browser, otherwise unavailable |

Per Worker: 2-4 queries by default, one accepted URL fetch, one transient retry, one fallback, at most two attempts for one normalized URL, and at least 20% final-output reserve.

A static 401/403/404/error page is unavailable. When web-access is installed, use it once in read-only research mode with the user's authorized session. Do not extract credentials or perform account-changing actions. Record failed static and accepted browser attempts separately; only the accepted attempt may back Evidence.

For software/API/configuration behavior, record the target version and prefer its release tag/commit. Main-branch evidence is `mismatch` unless tied to the target version.
