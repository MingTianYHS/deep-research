# Changelog

All notable changes to this project are documented here.

## Unreleased

## 0.8.0rc1 - 2026-08-02

### Added

- User-level runtime preflight that validates complete Skill files, Agent TOML contracts, read-only sandboxes, a real workspace write probe, and optional web-access installation.
- Non-bypassable Worker ingestion with accepted Source Attempts, content hashes, complete Evidence Cards, preserved Worker payloads, and self-reported/observed budget disclosure.
- Authorized web-access fallback for login, dynamic, and anti-bot pages without credential extraction or account-changing actions.
- Topic mutation and JSONL file locks, explicit workspace format stamps, stricter Quote Audits, and zero-citation rejection.
- Version-aware research, Rollout diagnostics, Chinese external workspaces, Obsidian-native reports, and Windows/Linux CI.

### Changed

- Deep profile question limit is consistently eight.
- Worker limits now read from the canonical `budgets.toml` instead of duplicated constants.
- Evidence may reference only an accepted Source Attempt.
- Worker output reserve is at least 20 percent and is reported explicitly.

## 0.7.0rc1 - 2026-08-01

### Added

- Typed dependency-aware research design, source-origin clustering, adversarial critique, calibrated synthesis, report rubric, external workspaces, and bounded subagents.

## 0.6.0rc1 - 2026-08-01

### Added

- Codex-native Skill, persistent workspaces, Evidence/Claim model, citations, quality audits, provider/cost/export tools, migrations, CI, and smoke tests.
