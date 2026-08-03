# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Skill-level query discipline with explicit query intents, evidence-oriented low-yield pivots, compact query traces, and Query-to-Source Attempt lineage.
- Persisted run-bound Critic Reviews and a deterministic full lifecycle smoke test.
- Guarded `topicctl.py` entry points for language-aligned topic creation, naming validation, and topic-contained report initialization.
- Regression coverage for Chinese topic directories, explicit language mismatch overrides, and report path boundaries.

### Changed

- Free-quota provider routing now distinguishes query construction from tool selection and no longer uses result counts as a low-yield threshold.
- Runtime preflight now requires provider manifests and the Query Craft/Tool Routing references used by installed agents.
- Runtime preflight now requires the guarded topic naming entry point.
- Worker ingestion now accumulates self-reported query/page usage and accepted Evidence exactly once.
- Complete Run status now requires active-run Worker/Evidence, approved Critic Review, live quality gates, report rubric, citation validation, and final Quote Audit.
- Chinese topic titles now default to Chinese human-readable directories and report names; technical IDs remain ASCII.

### Fixed

- Real topic workspaces are ignored by Git while the tracked `.gitkeep` remains available.
- Workspace migration, Evidence lineage, and Quote Audit documentation now match format 2 and current validators.
- Quote Audits freeze Source Attempt identity, content hash, report hash, and active Run identity.
- Report initialization no longer permits an accidental top-level report copy outside the canonical topic workspace when using the guarded entry point.

## 0.9.0rc1 - 2026-08-02

### Added

- Codex-native persistent topic experts activated by workspace `AGENTS.md`.
- Current-directory topic command resolution.
- Canonical `plans/current-design.json` with generated `questions.md` and synchronized open-question state.
- Baseline, incremental, and question-specific bounded Briefs.
- Rebuildable `context.md` and Critic-validated reusable `memory/lessons.jsonl`.
- Structured Reflection lifecycle and research-generation tracking.
- Workspace format 2 migration.

### Changed

- The main Codex session is now explicitly the topic-expert coordinator; the three global custom agents remain fixed read-only execution roles.
- Per-topic Agent TOML generation is deprecated and `--install-agent` no longer creates files.
- Existing incremental-plan logic is reused as the foundation for topic context rather than adding a second planner.
- Claim/Evidence remains the only topic fact authority; no Wiki, vector database, or memory middleware was added.

## 0.8.0rc1 - 2026-08-02

### Added

- Strict Worker/Source Attempt/Evidence linkage, authorized web-access fallback, canonical budgets, locks, stronger Doctor and Quote Audit gates, and cross-platform CI.

## 0.7.0rc1 - 2026-08-01

### Added

- Typed research design, origin clustering, adversarial critique, calibrated synthesis, and report rubric.

## 0.6.0rc1 - 2026-08-01

### Added

- Codex-native Skill, persistent workspaces, Claim/Evidence, quality audits, migrations, exports, and CI.
