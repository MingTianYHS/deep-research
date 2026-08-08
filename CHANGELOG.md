# Changelog

All notable changes to this project are documented here.

## 1.0.0rc1 - 2026-08-08

### Product transition

- Change the product goal from an autonomous research system to a user-directed persistent research assistant.
- Preserve the previous `0.9.0rc3` behavior at commit `5ac0ab62d0e45d86e7aea471bf7566cbc30e46b4` and branch `archive/v0.9.0rc3-autonomous-research`.
- Stop after report delivery and follow-up planning; another Run requires an explicit user request.

### Added

- Bounded reuse plans containing existing Evidence, relevant Claims, known URLs, freshness, prior Queries, time anchor, and follow-up backlog.
- Explicit `reused_evidence_ids` for zero-search lite/standard Worker completion when prior Evidence is sufficient.
- Cross-Run historical Query duplicate validation with explicit refresh/scope/version/remediation/low-yield reasons.
- `memory/current.md`, `memory/knowledge-deltas.jsonl`, and bounded `plans/research-backlog.json`.
- SynthesisResult v2 with a six-part knowledge delta and at most five actionable follow-up questions.
- Separate active-Run and lifetime work-unit accounting.

### Changed

- Successful Run completion sets the baseline independently of Reflection.
- `state.usage` resets at every Run start; `state.lifetime_usage` remains diagnostic.
- Researcher assignments now instruct reuse, direct known-URL refresh, and gap-only discovery.
- Topic `AGENTS.md` is a compact memory boot protocol rather than an autonomous orchestration loop.
- Deep retains strict fresh verification; lite/standard retain one Critic and mechanical lineage audit.

### Fixed

- Lite/standard topics can enter a real incremental second Run even when Reflection was deferred.
- Long-lived topics no longer exhaust all future Run budgets through cumulative usage.
- Incremental mode, last-Run time, priority Claims, prior Queries, and known sources now reach the Researcher.

## 0.9.0rc3 - 2026-08-07

- Streamlined lite/standard runtime, compact Worker Result v2, run-level disconfirmation, six-section reports, hard-gate scoring, pseudo-Token budget removal, and CI/maintenance-surface reduction.

## 0.9.0rc1 - 2026-08-02

- Added persistent topic experts, format-2 workspaces, Research Design, bounded Briefs, Reflection, and reusable validated Lessons.

## 0.8.0rc1 - 2026-08-02

- Added strict Worker/Source Attempt/Evidence linkage, authorized web-access fallback, budgets, locks, Doctor, Quote Audit, and cross-platform CI.

## 0.7.0rc1 - 2026-08-01

- Added typed research design, origin clustering, adversarial critique, calibrated synthesis, and report rubric.

## 0.6.0rc1 - 2026-08-01

- Added Codex-native Skill, persistent workspaces, Claim/Evidence, quality audits, migrations, exports, and CI.
