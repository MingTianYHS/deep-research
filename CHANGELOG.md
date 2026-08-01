# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Codex-native deep-research Agent Skill and bounded parallel subagents.
- Persistent topic workspaces, run lifecycle, hard budgets, and evidence ingestion.
- Append-only Claim–Evidence graph with two-step core-claim approval.
- Structural citation checks, incremental plans, and report scaffolding.
- Source-type freshness, transparent quality scoring, and report-bound quote audits.
- Provider manifests, normalized cost events, deterministic topic packages, and release checks.

### Security

- External content is always untrusted data.
- Research workers are read-only and the coordinator owns writes.
- High-risk prompt-injection evidence is quarantined from aggregate quality scores.
- Topic exports exclude raw evidence, caches, environment files, and symlinks by default.
