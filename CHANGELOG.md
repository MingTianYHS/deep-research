# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Versioned Researcher, Critic, and Synthesis assignments with explicit instruction-inheritance notices.
- Immutable Design/Worker/Evidence/Claim snapshot hashes for Critic Review v2.
- Stable Critic Finding and Targeted Search contracts with bounded remediation routing.
- Search-free SynthesisResult v1 validation and guarded report persistence through `agentctl.py`.
- Regression coverage for complete researcher payloads, stale Critic approvals, targeted remediation, and synthesis snapshot boundaries.
- State-driven `research.py next` coordinator contracts with explicit phases, next actions, named Agent assignments, blockers, progress, and user-input requirements.

### Changed

- Release candidate metadata advances to `0.9.0rc3`.
- `topic_researcher` no longer assumes parent Skill inheritance and receives full scope, exclusions, known URLs, dependency results, version anchors, remediation targets, and numeric budgets.
- Known-URL retrieval uses an initial attempt plus one failure-specific fallback instead of an unconditional multi-tool chain.
- `research_critic` approvals are invalidated when reviewed state changes; `changes_required` now routes to Researcher remediation before recheck.
- `research_synthesizer` is strictly search-free and returns a validated JSON envelope instead of unbound Markdown.
- Codex remains the only upper-level orchestrator; Python validates legal workflow actions and contracts.

### Fixed

- Stale Critic approval can no longer satisfy completion after Design, Worker, Evidence, or Claim changes.
- Critic targeted searches are limited to three and must reference blocker/high findings.
- Reports cannot be written by synthesis outside the canonical topic `reports/` directory.

## 0.9.0rc1 - 2026-08-02

### Added

- Codex-native persistent topic experts, format-2 workspaces, Research Design, bounded Briefs, Reflection, and reusable validated Lessons.

## 0.8.0rc1 - 2026-08-02

### Added

- Strict Worker/Source Attempt/Evidence linkage, authorized web-access fallback, budgets, locks, Doctor, Quote Audit, and cross-platform CI.

## 0.7.0rc1 - 2026-08-01

### Added

- Typed research design, origin clustering, adversarial critique, calibrated synthesis, and report rubric.

## 0.6.0rc1 - 2026-08-01

### Added

- Codex-native Skill, persistent workspaces, Claim/Evidence, quality audits, migrations, exports, and CI.
