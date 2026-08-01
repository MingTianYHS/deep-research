# End-to-end persisted topic fixture

This is a synthetic fixture for testing the control-plane flow. The `example.com` URLs intentionally are not real research evidence and must never be presented as factual research.

Copy it into a disposable workspace:

```bash
cp -R examples/end-to-end workspace/topics/example-ai-research
CTL=.agents/skills/deep-research/scripts/researchctl.py
QCTL=.agents/skills/deep-research/scripts/qualityctl.py

python "$CTL" status example-ai-research
python "$CTL" validate example-ai-research
python "$CTL" claims example-ai-research
python "$QCTL" quality-report example-ai-research --as-of 2026-08-01
python "$CTL" verify-citations example-ai-research --report workspace/topics/example-ai-research/reports/initial.md
python "$QCTL" audit-init example-ai-research --report workspace/topics/example-ai-research/reports/initial.md
```

The structural citation check succeeds. A final quote-fidelity audit should remain unresolved because synthetic sources are not valid evidence. This demonstrates that structural validity does not equal factual verification.
