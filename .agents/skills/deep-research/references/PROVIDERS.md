# Provider manifests and cost accounting

`config/providers.toml` declares capabilities, authentication contracts, accounting modes, and supported usage units. It contains no API keys and does not guarantee a provider is connected.

```bash
python scripts/releasectl.py providers
python scripts/releasectl.py providers --name exa
```

A provider adapter is usable only when both conditions hold:

1. the manifest declares the capability and usage unit;
2. Codex confirms the host tool, MCP connection, or environment credential is actually available.

## Normalized cost events

```bash
python scripts/releasectl.py cost-record topic \
  --provider exa --operation search --quantity 2 --unit request \
  --cost-usd 0.014 --run-id run-ID --estimated

python scripts/releasectl.py cost-summary topic --run-id run-ID
```

Every event records provider, operation, quantity, unit, USD cost, estimated/actual flag, run ID, timestamp, and optional metadata. Costs are supplied by the runtime/provider invoice when available. Do not silently convert an estimate into an actual value.

Pricing URLs are references only. Prices must not be copied into durable logic because providers change them.
