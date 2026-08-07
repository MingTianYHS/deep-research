# Changelog

All notable changes to this project are documented here.

## Unreleased

### Lean runtime v2

- Replace lite/standard per-Claim coordinator loops with one deterministic, idempotent Claim sync grouped by research question.
- Skip the separate report scaffold turn for lite/standard and synthesize directly into the final report path.
- Reduce the report contract to six body sections and generate quality diagnostics outside model-authored prose.
- Replace the weighted report score with explicit hard gates while retaining citation, independence, risk, and quote-audit safeguards.
- Preserve the strict deep workflow and explicit Claim review.

### Added

- Versioned Researcher, Critic, and Synthesis assignments with explicit instruction-inheritance notices.
- Immutable Design/Worker/Evidence/Claim snapshot hashes for Critic Review v2.
- Stable Critic Finding and Targeted Search contracts with bounded remediation routing.
- Search-free SynthesisResult v1 validation and guarded report persistence through `agentctl.py`.
- Regression coverage for complete researcher payloads, stale Critic approvals, targeted remediation, and synthesis snapshot boundaries.
- State-driven `research.py next` coordinator contracts with explicit phases, next actions, named Agent assignments, blockers, progress, and user-input requirements.
- Explicit `mechanical_lineage` audits for low-token report provenance checks.
- Lean workflow defaults for lite/standard profiles with strict deep-profile preservation.
- Atomic per-run coordinator step budgets and consecutive-action loop detection.
- Optional single-coordinator leases using explicit or host-provided session identity.
- Profile-specific Critic review and targeted-remediation limits.

### Changed

- Release candidate metadata advances to `0.9.0rc3`.
- `topic_researcher` no longer assumes parent Skill inheritance and receives full scope, exclusions, known URLs, dependency results, version anchors, remediation targets, and numeric budgets.
- Known-URL retrieval uses an initial attempt plus one failure-specific fallback instead of an unconditional multi-tool chain.
- `research_critic` approvals are invalidated when reviewed state changes; `changes_required` now routes to Researcher remediation before recheck.
- `research_synthesizer` is strictly search-free and returns a validated JSON envelope instead of unbound Markdown.
- Codex remains the only upper-level orchestrator; Python validates legal workflow actions and contracts.
- Lite and standard profiles replace the second post-synthesis Critic pass with a deterministic lineage audit.
- Lite and standard profiles defer Reflection instead of blocking report delivery or the next run.
- Lite and standard profiles stop automatic full Critic re-review after the configured limit.
- The deep profile retains independent quote verification, expanded Critic limits, and Critic-linked Reflection.

### Fixed

- Stale Critic approval can no longer satisfy completion after Design, Worker, Evidence, or Claim changes.
- Critic targeted searches are limited and must reference blocker/high findings.
- Reports cannot be written by synthesis outside the canonical topic `reports/` directory.
- `qualityctl` audit commands now accept an optional topic slug and work from the current topic workspace.
- Repeated coordinator actions can no longer grow without a persisted hard stop.
- A second identified coordinator cannot drive the same active topic while another lease is valid.

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
