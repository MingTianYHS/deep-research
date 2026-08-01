# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- `DEEP_RESEARCH_WORKSPACE_ROOT` support for external topic workspaces, including Windows paths such as `D:\知识宇宙海\调研工作区`.
- UTF-8 Chinese topic directory names with cross-platform filename sanitization.
- Host-local `YYYYMMDD-主题.md` report naming, plus localized update and final suffixes.
- Regression tests for external roots, Chinese names, Windows reserved names, and report filenames.

## 0.7.0rc1 - 2026-08-01

### Added

- Typed, dependency-aware research design with non-overlapping worker boundaries.
- Required disconfirming queries, acceptance criteria, source preferences, and alternative explanations.
- Source-origin clustering and structured rejected-source/contradiction output.
- Adversarial critic contract for entailment, scope, epistemic type, independence, and overreach.
- Calibrated synthesizer contract separating fact, inference, causal interpretation, forecast, and recommendation.
- Mechanical report rubric for sections, material citation coverage, numeric citation coverage, source independence, conflict, uncertainty, and citation validity.
- Good/bad report regression tests and research-design fixtures.

## 0.6.0rc1 - 2026-08-01

### Added

- Codex-native deep-research Skill and bounded parallel subagents.
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
