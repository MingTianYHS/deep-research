# Topic export format

A topic can be packaged into a deterministic ZIP for backup, transfer, or review:

```bash
python scripts/releasectl.py export-topic topic
python scripts/releasectl.py verify-package --package dist/topic.deep-research.zip
```

The archive contains sorted workspace files plus `manifest.json` with SHA-256 and byte size for every included file. ZIP timestamps and permissions are fixed so identical workspaces produce identical archive hashes.

Excluded by default:

- `cache/`;
- `evidence/raw/`;
- `.env` and platform metadata;
- symlinks and Python caches.

This minimizes secret leakage and package size. The archive is an auditable research handoff, not a substitute for source access permissions. If raw evidence is required, transfer it separately under an explicit security review.
