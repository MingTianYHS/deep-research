# deep-research

A lightweight citation-first deep-research Skill for OpenAI Codex.

**Release candidate:** `0.9.0rc1` · Python 3.11+

## Topic expert model

Each topic workspace is a persistent Codex expert context. Start Codex from that directory; its `AGENTS.md` makes the main session the topic-expert coordinator. The coordinator owns planning, approvals, state, and writes and delegates only to three global read-only roles:

- `topic_researcher`
- `research_critic`
- `research_synthesizer`

Per-topic `topic-<slug>.toml` agents are deprecated. Expertise compounds through existing Claim/Evidence, a bounded rebuildable `context.md`, and Critic-validated `memory/lessons.jsonl`—not by changing model weights or duplicating a Wiki/database.

## Install

```text
%USERPROFILE%\.agents\skills\deep-research
%USERPROFILE%\.codex\agents\topic-researcher.toml
%USERPROFILE%\.codex\agents\research-critic.toml
%USERPROFILE%\.codex\agents\research-synthesizer.toml
```

Optional: `%USERPROFILE%\.agents\skills\web-access`.

```powershell
py -3.11 "$HOME\.agents\skills\deep-research\scripts\runtimectl.py" doctor --strict
$env:DEEP_RESEARCH_WORKSPACE_ROOT = 'D:\知识宇宙海\调研工作区'
```

## Human-readable naming

User-visible names follow the language of the topic. Chinese topics use a Chinese directory and Chinese report filename by default; stable Question, Evidence, Claim, Run, schema, and Agent identifiers remain ASCII. English product and project names remain unchanged.

`topicctl.py` is the guarded entry point for topic creation and report initialization. It rejects a silent Chinese-title/English-directory mismatch and prevents reports from escaping the canonical topic workspace. Use `--allow-language-mismatch` only when the user explicitly requests a different-language directory.

## New topic

```powershell
$SKILL = "$HOME\.agents\skills\deep-research"
py -3.11 "$SKILL\scripts\topicctl.py" init-topic 'AI短剧市场研究' --budget standard
cd 'D:\知识宇宙海\调研工作区\AI短剧市场研究'
codex
```

Inside the topic directory:

```powershell
py -3.11 "$SKILL\scripts\researchctl.py" plan --questions 5
py -3.11 "$SKILL\scripts\researchctl.py" brief
py -3.11 "$SKILL\scripts\researchctl.py" run-start --mode baseline
py -3.11 "$SKILL\scripts\topicctl.py" report-init --type initial
```

Do not initialize topic workspaces with `mkdir`, `New-Item`, or hand-written `topic.toml`/`state.json`. Do not create a second directory, junction, symlink, hard link, or top-level report copy to represent the same topic.

After a validated run, finish it and apply a Critic-reviewed Reflection. This increments the research generation and stores only reusable research lessons. Topic facts continue to live exclusively in Claim/Evidence.

Existing workspaces migrate to format 2 with:

```powershell
py -3.11 "$SKILL\scripts\releasectl.py" workspace-migrate <slug> --apply
```

Check legacy naming before continuing it:

```powershell
py -3.11 "$SKILL\scripts\topicctl.py" validate-naming <topic-directory>
```

## Free-quota search

The default registry enables native web, Tavily, Exa, Jina, and Firecrawl without permitting paid overage. Workers select one provider per query: native web for ordinary and official discovery, Tavily for current web/news and structured extraction, Exa for semantic discovery, GitHub tools for repository evidence, and Firecrawl only as a quota-bounded dynamic-page or research-index fallback.

Queries use a bounded ladder: broad discovery, `site:` authority targeting, exact-title or identifier verification, original-document lookup, disconfirming search, and a material cross-language check. Quota exhaustion falls back to another free route. The Skill never rotates multiple accounts or keys to evade provider limits, and credentials must stay outside the repository and topic workspaces.

The project remains standard-library based: no scheduler, daemon, LangGraph, memory service, vector database, or heavyweight provider SDK.
