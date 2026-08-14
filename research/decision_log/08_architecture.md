# Research Decision Log — 08 · Software Architecture Questions (20)

**Q1.** Should the system be modular?
**A:** Yes — data/research/models/strategies/risk/execution/monitoring
split with strict interfaces; the mandate's layout is implemented.
**Conf:** H. **Δ:** —.

**Q2.** Should the risk engine be independent of the alpha engine?
**A:** Yes — structurally: alpha output → meta → risk → execution; risk
is the only gate and cannot be bypassed.
**Conf:** H. **Δ:** —.

**Q3.** Python for everything?
**A:** Python for research/prototyping; latency-critical live loops
would need compiled components — a deployment-phase decision.
**Conf:** M. **Δ:** —.

**Q4.** How is configuration managed?
**A:** One JSON config with dataclass loading and rationale comments; no
magic numbers in code (tested by inspection).
**Conf:** H. **Δ:** —.

**Q5.** How are experiments reproduced?
**A:** Registries store hypothesis, data version, features, params,
periods, results, decision + recorded_at; seeds fixed; code committed.
**Conf:** H. **Δ:** —.

**Q6.** Should the system run in Docker?
**A:** For deployment, yes; research runs in a venv. Documented in
deployment.md.
**Conf:** M. **Δ:** —.

**Q7.** How are secrets managed?
**A:** Never in code; env vars / secret store; separate credentials for
research/paper/admin (security.md). No secrets exist in this repo.
**Conf:** H. **Δ:** —.

**Q8.** Is a database needed?
**A:** JSONL registries suffice for research; a time-series store is a
deployment-phase item.
**Conf:** M. **Δ:** —.

**Q9.** How is time handled?
**A:** UTC everywhere, pandas DatetimeIndex, explicit session mapping;
clock-sync checks documented.
**Conf:** H. **Δ:** —.

**Q10.** How are NaN/Inf handled at module boundaries?
**A:** Validated at entry (prices, signals), flagged by audits, and the
risk engine rejects non-finite orders.
**Conf:** H. **Δ:** —.

**Q11.** Should the LLM have decision authority?
**A:** No — LLMs are research/documentation tools; the decision path is
deterministic code. Architecture makes this literal.
**Conf:** H. **Δ:** —.

**Q12.** How is the automation hierarchy implemented?
**A:** Level gates: RESEARCH → VALIDATION → PAPER → APPROVED; only
APPROVED/PAPER statuses reach execution; registry enforces transitions.
**Conf:** H. **Δ:** —.

**Q13.** How are modules tested?
**A:** pytest suite (61 tests: data, features, engine, risk, meta, WFA,
PBO, calibration, drift, broker, validator) — run in CI-style before any
release.
**Conf:** H. **Δ:** —.

**Q14.** How is failure injected?
**A:** Broker failure, partial fills, missing data, latency, cost shocks,
anomaly floods — all exercised in tests/stress.
**Conf:** H. **Δ:** —.

**Q15.** How does restart recovery work?
**A:** Documented procedure: reconnect → authenticate → fetch state →
reconcile → risk check → resume. No assumption of local state validity.
**Conf:** H. **Δ:** —.

**Q16.** How are dashboards generated?
**A:** Static HTML from run artifacts (dashboard.py) — no live server
needed for research; live monitoring is a deployment item.
**Conf:** M. **Δ:** —.

**Q17.** How is the audit trail kept?
**A:** JSONL append-only registries + per-trade journals + rejection
logs + kill-switch log — every decision reconstructible.
**Conf:** H. **Δ:** —.

**Q18.** Should strategies be plugins?
**A:** Yes — Strategy ABC + strict signal schema; adding a strategy does
not touch the engine (tested: 4 strategies share one engine).
**Conf:** H. **Δ:** —.

**Q19.** How is the codebase kept dependency-light?
**A:** numpy/pandas/sklearn/matplotlib only; heavy frameworks deferred
until they earn their place.
**Conf:** H. **Δ:** —.

**Q20.** What is the most important architectural property?
**A:** The failure of any layer must degrade to "no new trades", never
to "uncontrolled trading". Kill switches + validator + risk engine make
this the default behavior.
**Conf:** H. **Δ:** —.
