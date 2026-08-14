# Research Decision Log — 10 · Security Questions (15)

**Q1.** Where do API keys live?
**A:** Nowhere in this repo — env vars/secret manager only; `.env` is
gitignored; `.env.example` documents names.
**Conf:** H. **Δ:** —.

**Q2.** Are secrets ever printed to logs?
**A:** No — logging policy redacts credentials; code review enforces.
**Conf:** H. **Δ:** —.

**Q3.** What permissions does research have?
**A:** Read-only data access; no order capability. Paper trading uses
paper-only credentials. Admin/execution credentials are separate and
out of scope for the research state.
**Conf:** H. **Δ:** —.

**Q4.** How is the config protected?
**A:** Config is code-reviewed like code; risk limits cannot be changed
at runtime by any component.
**Conf:** H. **Δ:** —.

**Q5.** Can a model change its own limits?
**A:** No — limits live in the risk engine; no API exists for models to
modify them (checked by architecture review).
**Conf:** H. **Δ:** —.

**Q6.** How are logs protected?
**A:** Logs may contain PII if personal data is added — policy: never
log personal info; logs are local files with restricted access.
**Conf:** M. **Δ:** —.

**Q7.** How is the environment isolated?
**A:** venv + pinned requirements; containerization documented for
deployment.
**Conf:** M. **Δ:** —.

**Q8.** What happens if the environment is compromised?
**A:** Paper-only means no financial damage path; kill switch + credential
rotation + audit replay are the response procedures.
**Conf:** M. **Δ:** —.

**Q9.** Are dependencies vetted?
**A:** Minimal, mainstream, pinned; supply-chain review is a deployment
gate.
**Conf:** M. **Δ:** —.

**Q10.** How are order endpoints protected (future live)?
**A:** Signed requests, per-credential limits, separate execution
credentials with minimum permissions, IP allowlists (documented in
security.md as requirements).
**Conf:** M. **Δ:** —.

**Q11.** Is the audit trail tamper-evident?
**A:** Append-only JSONL + recorded_at UTC; hash-chaining is a roadmap
hardening.
**Conf:** L-M. **Δ:** —.

**Q12.** How is remote code execution prevented?
**A:** No dynamic code loading; strategies are classes in the repo;
model files are validated data, not code.
**Conf:** H. **Δ:** —.

**Q13.** What if an API returns malformed data?
**A:** Validation layer rejects; no partial state; error logged; data
kill switch.
**Conf:** H. **Δ:** —.

**Q14.** Are credentials separated by environment?
**A:** Yes — research / paper / admin mapped to separate secrets; a
paper credential cannot place real orders because no real-order path
exists.
**Conf:** H. **Δ:** —.

**Q15.** What is the security cardinal rule?
**A:** The system must be safe to run unattended in paper mode: no
secrets in code, no bypass paths, no way to turn paper into live
without an explicit human deployment gate.
**Conf:** H. **Δ:** —.
