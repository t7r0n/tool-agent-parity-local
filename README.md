# Tool Agent Parity Local

Local migration and parity harness for turning structured tool bundles into agent metadata.

The project reads deterministic synthetic tool-bundle definitions, lifts parameter schemas into compact agent metadata, synthesizes tool descriptions from existing comments, and runs record/replay parity evals to prove agent invocations match direct tool calls.

## Features

- Synthetic corpus of 24 tool bundles across content, calendar, CRM, finance, and internal-ops shapes.
- Deterministic schema lift from typed tool parameters to JSON-schema-like agent metadata.
- Deterministic description synthesis from comments, with no model calls.
- Record/replay parity eval with 30 scenarios per category.
- Migration metrics: added lines, build-to-demo estimate, parity pass rate, tool-selection accuracy.
- JSONL tool loop, loopback HTTP API, verifier, benchmark, dashboard, and demo-pack export.

## Quickstart

```bash
uv sync --extra dev
uv run tool-agent-parity init-demo --force
uv run tool-agent-parity lift bundle-0001
uv run tool-agent-parity eval-bundle bundle-0001
uv run tool-agent-parity run-suite
uv run tool-agent-parity verify
```

Generated runtime data is excluded from git.
