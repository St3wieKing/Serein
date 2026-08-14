# Research Decision Log — 07 · Data Questions (20)

**Q1.** What data does the system need at minimum?
**A:** OHLCV + volume, timestamped UTC, symbol-consistent, adjusted for
corporate actions. Tick/quote data is a roadmap upgrade.
**Conf:** H. **Δ:** —.

**Q2.** Is synthetic data acceptable for research?
**A:** For engineering validation only — never for edge claims. All
synthetic results are labeled as such everywhere.
**Conf:** H. **Δ:** —.

**Q3.** How is raw data kept immutable?
**A:** Ingestion writes raw files that are never modified; derived frames
are rebuilt from raw (registry + data version tags).
**Conf:** M. **Δ:** —.

**Q4.** How are missing observations handled?
**A:** Detected by validation, never silently filled; engines handle gaps
explicitly (gap-through-stop); ML drops NaN rows after audit.
**Conf:** H. **Δ:** —.

**Q5.** How are duplicates handled?
**A:** Rejected by validation (duplicate timestamps flagged); ingestion
must dedupe by (symbol, timestamp) before storage.
**Conf:** H. **Δ:** —.

**Q6.** How are outliers handled?
**A:** Anomaly flags (impossible prices, insane ranges, return spikes)
and drop-with-tolerance; more than 2% anomalous → refuse dataset.
**Conf:** H. **Δ:** —.

**Q7.** What is a stale observation?
**A:** Flat closes beyond threshold or feed lag beyond max_staleness;
flagged by validation, kills trading via data kill switch.
**Conf:** M. **Δ:** —.

**Q8.** How is timezone handled?
**A:** UTC storage everywhere; session features derived with an explicit
ET session map; DST handled by pandas tz machinery (documented).
**Conf:** M. **Δ:** —.

**Q9.** Do we need delisted securities for real data?
**A:** Yes — survivorship bias is a real-data must; the synthetic
universe can't have it, so it's a hard requirement for the real-data
adapter.
**Conf:** H. **Δ:** —.

**Q10.** Are adjusted prices required?
**A:** Yes — splits/dividends corrupt returns; adjust or tag unadjusted
and refuse to train on mixed series.
**Conf:** H. **Δ:** —.

**Q11.** How is data versioned?
**A:** Data version tags (e.g., "synth-v1") flow into model records and
experiments; content hashes stored in registries.
**Conf:** M. **Δ:** —.

**Q12.** What does the leakage auditor check?
**A:** Alignment, monotonicity, target-in-features, perfect correlations,
horizon overlap warnings (implemented + tested).
**Conf:** H. **Δ:** —.

**Q13.** Can normalization leak future info?
**A:** Yes if fit on the full sample; all rolling features are causal by
construction (tested); global scalers are a roadmap item with
fit-on-train-only.
**Conf:** H. **Δ:** —.

**Q14.** How is bar alignment across symbols done?
**A:** Union index with per-symbol lookups; missing bars are gaps, not
zeros (engine handles explicitly).
**Conf:** H. **Δ:** —.

**Q15.** What data quality gates block trading?
**A:** Data kill switch: non-finite prices, stale feed, anomaly floods,
validation errors — any → no new trades.
**Conf:** H. **Δ:** —.

**Q16.** How much history is needed for hourly features?
**A:** ~500+ bars for percentile features; the pipeline drops warm-up
rows rather than padding with garbage.
**Conf:** M. **Δ:** —.

**Q17.** Are bid/ask data required for cost realism?
**A:** Preferred; spread model is the current approximation. Roadmap:
trade-and-quote ingestion.
**Conf:** M. **Δ:** —.

**Q18.** How is volume data validated?
**A:** Non-negative, finite, no absurd spikes (anomaly flags); bar ADV
drives impact and liquidity caps.
**Conf:** H. **Δ:** —.

**Q19.** Should the system use revised (vintage) macro data?
**A:** Only if events are modeled; revisions are leakage vectors — the
audit flags revised-data risk in the source register.
**Conf:** M. **Δ:** —.

**Q20.** What is the data layer's cardinal rule?
**A:** Never train or trade on data that failed validation; never silently
fill; never let a corrupted feed look healthy.
**Conf:** H. **Δ:** —.
