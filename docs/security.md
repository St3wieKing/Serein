# Serein — Security

## Principles

1. **No secrets in code.** API keys, tokens, passwords live in the
   environment / secret manager. `.env` is gitignored; `.env.example`
   documents variable names only.
2. **Least privilege.** Research credentials are read-only. Paper
   credentials can only reach the paper broker. Execution/admin
   credentials are separate and out of scope for the research state.
3. **No bypass paths.** Architecture review + tests confirm there is no
   code path from a model to an order except through the validator and
   risk engine.
4. **Fail closed.** Any uncertainty about identity, state, or data
   stops order flow.

## Current repository state

| Asset | Status |
|---|---|
| API keys in repo | none (verified by `git grep` discipline) |
| Real broker adapter | none — PaperBroker only |
| Network egress for orders | none — no order-transmission code exists |
| Personal information | never logged; logs local |
| Dependency surface | numpy, pandas, scikit-learn, matplotlib, pytest, tabulate |
| Dynamic code execution | none — strategies are static classes |

## Rules for contributors

- Never commit `.env`, keys, or credentials.
- Never log raw credentials, tokens, or full account numbers.
- Config changes to risk limits require code review (they are code).
- Registry records are append-only; corrections are new records.

## Future live-trading requirements (documented now, not implemented)

1. Separate execution credentials with per-credential order limits
   (mirrors the SEC market-access framework: pre-set financial limits,
   erroneous-order controls).
2. Signed, timestamped, idempotent order requests; replay protection.
3. IP allowlists + short-lived tokens; key rotation policy.
4. Tamper-evident audit chain (hash-chained registry) — current
   append-only JSONL is the baseline.
5. Dependency pinning + supply-chain review as a deployment gate.
6. Container with read-only root FS; secrets via volume/env, never in
   image layers.
7. Incident response runbook: credential rotation, kill switch,
   registry replay, post-mortem template.

## Paper-safety guarantee

Because no live adapter exists and `PAPER_TRADING_ONLY=True` is a
hard constant, even a fully compromised environment cannot place real
orders. This is the security property that makes unattended research
runs acceptable.
