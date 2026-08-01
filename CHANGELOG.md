# Changelog

All notable changes to this project are documented here.

## 0.6.0rc1 - 2026-08-01

### Added

- Codex-native deep-research Agent Skill and bounded parallel subagents.
- Persistent topic workspaces, run lifecycle, hard budgets, and evidence ingestion.
- Append-only Claim–Evidence graph with two-step core-claim approval.
- Structural citation checks, incremental plans, and report scaffolding.
- Source-type freshness, transparent quality scoring, and report-bound quote audits.
- Provider manifests, normalized cost events, deterministic topic packages, and release checks.
- Python 3.11/3.12 CI, end-to-end smoke testing, and versioned workspace migration contracts.

### Security

- External content is always untrusted data.
- Research workers are read-only and the coordinator owns writes.
- High-risk prompt-injection evidence is quarantined from aggregate quality scores.
- Topic packages reject unsafe paths and duplicate members and exclude raw evidence, caches, environment files, and symlinks by default.
