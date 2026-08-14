"""Serein — full research pipeline (Phase 1-14 of the build order).

Runs the complete validation stack on SYNTHETIC regime-switching data:
  data -> validation -> features -> regime -> strategies -> meta ->
  backtest -> walk-forward -> ML (with leakage audit) -> stress -> PBO ->
  ablation -> drift -> paper broker -> registries -> dashboard -> report

All results are labeled SYNTHETIC. They validate engineering and statistical
machinery, NOT any real-market edge.

Usage:
    .venv/bin/python scripts/run_research.py            # full run
    .venv/bin/python scripts/run_research.py --quick    # small run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serein.config import load_config  # noqa: E402
from serein import constants as C  # noqa: E402
from serein.data.synthetic import generate_universe  # noqa: E402
from serein.data.validation import validate_bars, anomaly_flags  # noqa: E402
from serein.features import build_features, make_labels  # noqa: E402
from serein.regimes import RegimeEngine  # noqa: E402
from serein.strategies.classic import (  # noqa: E402
    TrendStrategy, MomentumStrategy, MeanReversionStrategy, BreakoutStrategy,
)
from serein.meta import MetaEngine  # noqa: E402
from serein.backtest.engine import Backtester  # noqa: E402
from serein.backtest import stress  # noqa: E402
from serein.backtest.robustness import (  # noqa: E402
    run_parameter_sweep, cscv_pbo, stability_summary, ablation,
)
from serein.ml.models import ModelFactory, walk_forward_ml, build_ml_dataset  # noqa: E402
from serein.ml.calibration import reliability_report, expected_calibration_error, brier_score  # noqa: E402
from serein.registry import ExperimentRegistry, ModelRegistry  # noqa: E402
from serein.drift import feature_drift_report, performance_drift_report  # noqa: E402
from serein.execution.broker import PaperBroker, Order  # noqa: E402
from serein.execution.validation import OrderValidator  # noqa: E402
from serein.reporting import backtest_report, stress_section, config_section  # noqa: E402
from serein.dashboard import generate_dashboard  # noqa: E402

ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

DISCLAIMER = (
    "> **Data provenance: SYNTHETIC.** All results below come from a "
    "regime-switching simulator with planted effects, NOT real market data. "
    "They validate the engineering and statistical machinery of the framework. "
    "They are NOT evidence of any tradable edge."
)


def banner(msg: str) -> None:
    print(f"\n{'=' * 78}\n{msg}\n{'=' * 78}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small fast run")
    ap.add_argument("--config", default=str(ROOT / "config" / "research_config.json"))
    args = ap.parse_args()

    t0 = time.time()
    cfg = load_config(args.config)
    if args.quick:
        cfg.start, cfg.end = "2019-01-01", "2022-01-01"

    # ------------------------------------------------------------------ data
    banner("PHASE 1 — synthetic data generation + quality validation")
    symbols = ["SYNTH-A", "SYNTH-B", "SYNTH-C"]
    start_dt = pd.Timestamp(cfg.start)
    end_dt = pd.Timestamp(cfg.end)
    periods = int((end_dt - start_dt) / pd.Timedelta("1h")) + 1
    if args.quick:
        periods = min(periods, 4000)
    bars = generate_universe(symbols, periods=periods, freq=cfg.freq, seed=cfg.seed)
    for s, b in bars.items():
        problems = validate_bars(b, s)
        n_anom = int(anomaly_flags(b)["any_anomaly"].sum())
        print(f"[data] {s}: {len(b)} bars, {len(problems)} problems, "
              f"{n_anom} anomaly-flagged bars")
        for p in problems[:5]:
            print(f"  PROBLEM: {p}")

    # ------------------------------------------------------------ regime
    banner("PHASE 2 — regime classification")
    re = RegimeEngine()
    regimes = {s: re.classify_series(b) for s, b in bars.items()}
    for s in symbols:
        counts = regimes[s]["regime"].value_counts()
        print(f"[regime] {s}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))

    # --------------------------------------------------------- strategies
    banner("PHASE 3 — strategy engines + meta decision")
    sp = cfg.strategy
    strategies = {
        "trend": TrendStrategy({"trend_fast": sp.trend_fast, "trend_slow": sp.trend_slow,
                                "trend_vol_filter_n": sp.trend_vol_filter_n,
                                "trend_vol_filter_pct": sp.trend_vol_filter_pct}),
        "momentum": MomentumStrategy({"momentum_lookback": sp.momentum_lookback}),
        "mean_reversion": MeanReversionStrategy({
            "reversion_z_n": sp.reversion_z_n, "reversion_z_entry": sp.reversion_z_entry,
            "reversion_atr_filter_pct": sp.reversion_atr_filter_pct}),
        "breakout": BreakoutStrategy({"breakout_lookback": sp.breakout_lookback,
                                      "breakout_compression_pct": sp.breakout_compression_pct}),
    }
    meta = MetaEngine(weights={"trend": 1.0, "momentum": 0.8, "mean_reversion": 0.6,
                               "breakout": 0.8})
    meta_signals: dict[str, pd.DataFrame] = {}
    for s in symbols:
        raw = {name: strat.generate(bars[s], regimes[s]) for name, strat in strategies.items()}
        meta_signals[s] = meta.combine(raw, regimes[s])
        n = int((meta_signals[s]["direction"] != 0).sum())
        print(f"[meta] {s}: {n} active-signal bars / {len(meta_signals[s])} "
              f"(mean confidence of active: "
              f"{meta_signals[s].loc[meta_signals[s]['direction'] != 0, 'confidence'].mean():.2f})")

    # ---------------------------------------------------------- backtests
    banner("PHASE 4 — full-period backtest (with Risk Engine in the loop)")
    res = Backtester(cfg).run(bars, meta_signals)
    print(res.summary())
    print(f"[risk] {json.dumps(res.risk_summary, default=str)}")

    # IS / OOS split (temporal, locked)
    split = pd.Timestamp("2022-01-01")
    if args.quick:
        split = bars[symbols[0]].index[int(0.6 * periods)]
    is_bars = {s: b.loc[b.index < split] for s, b in bars.items()}
    oos_bars = {s: b.loc[b.index >= split] for s, b in bars.items()}
    res_is = Backtester(cfg).run(is_bars, meta_signals)
    if any(len(b) > 0 for b in oos_bars.values()):
        res_oos = Backtester(cfg).run(oos_bars, meta_signals)
        print(f"[IS ] {res_is.summary().splitlines()[0:3]}")
        print(f"[OOS] {res_oos.summary().splitlines()[0:3]}")
        print(f"[OOS] max drawdown: {res_oos.metrics['max_drawdown']:.2%}")
        has_oos = True
    else:
        res_oos = None
        has_oos = False
        print("[OOS] no out-of-sample data in this window; skipped")

    # ---------------------------------------------------------------- ML
    banner("PHASE 6 — machine learning with leakage audit + purged CV")
    sym0 = symbols[0]
    feats = build_features(bars[sym0], horizons=(1, 6, 24), regime_series=regimes[sym0]["regime"])
    labels = make_labels(bars[sym0], horizon=cfg.horizon_bars, mode="binary")["label"]
    X, y, audit = build_ml_dataset(feats, labels)
    print(f"[ml] features={X.shape[1]}, samples={len(X)}, audit={'PASS' if audit['pass'] else 'FAIL'}")
    for w in audit["warnings"]:
        print(f"  audit WARN: {w}")

    factory = ModelFactory(data_version="synth-v1")
    ml_results = {}
    for family in ("logistic", "random_forest", "gradient_boosting"):
        rec = factory.build(family, list(X.columns), str(X.index[0]), str(X.index[-1]))
        r = walk_forward_ml(X, y, rec, n_splits=4, embargo_bars=24,
                            min_train=max(1500, len(X) // 10))
        ml_results[family] = r
        print(f"[ml] {family}: OOS AUC={r['oos_auc']:.4f} acc={r['oos_accuracy']:.3f} "
              f"ECE={r['ece']:.3f} Brier={r['brier']:.4f} (base rate {r['base_rate']:.3f}, "
              f"n={r['n_oos']})")

    # ----------------------------------------------------------- stress
    banner("PHASE 7 — stress testing")
    stress_out = {}
    stress_out["costs"] = stress.stress_costs(bars, meta_signals, cfg)
    stress_out["slippage"] = stress.stress_slippage(bars, meta_signals, cfg)
    stress_out["volatility"] = stress.stress_volatility(bars, meta_signals, cfg)
    stress_out["liquidity"] = stress.stress_liquidity(bars, meta_signals, cfg)
    stress_out["latency"] = stress.stress_latency(bars, meta_signals, cfg, delays=(0, 1, 3, 6))
    stress_out["missing"] = stress.stress_missing_data(bars, meta_signals, cfg)
    for name, df in stress_out.items():
        print(f"[stress] {name}:")
        for _, r in df.iterrows():
            print(f"   {r['shock']:<22} ret={r['total_return']:>9.2%}  "
                  f"sharpe={r['sharpe']:>6.2f}  maxdd={r['max_drawdown']:>8.2%}  "
                  f"trades={int(r['n_trades'])}")

    # -------------------------------------------- parameter sweep + PBO
    banner("PHASE 8 — parameter sweep + probability of backtest overfitting (CSCV)")
    sweep_space = {
        "trend_fast": [10, 20, 40],
        "trend_slow": [40, 60, 120],
    }

    def sweep_backtest(sig_dict):
        return Backtester(cfg).run(bars, sig_dict)

    sweep_rows = []
    from serein.backtest.robustness import parameter_grid
    for params in parameter_grid(sweep_space):
        strat = TrendStrategy(params)
        sigs = {s: strat.generate(bars[s], regimes[s]) for s in symbols}
        # per-subperiod performance matrix for CSCV
        sub_metrics = []
        sub_edges = np.array_split(np.arange(periods), 6)
        for seg in sub_edges:
            seg_bars = {s: b.iloc[seg] for s, b in bars.items()}
            r = Backtester(cfg).run(seg_bars, sigs)
            sub_metrics.append(r.metrics.get("sharpe", np.nan))
        full = sweep_backtest(sigs)
        sweep_rows.append({"params": params, "sharpe_full": full.metrics["sharpe"],
                           "subperiods": sub_metrics})
    sweep_df = pd.DataFrame(sweep_rows)
    pbo_matrix = pd.DataFrame(sweep_df["subperiods"].tolist())
    pbo_matrix.columns = [f"p{i}" for i in range(pbo_matrix.shape[1])]
    pbo_matrix = pbo_matrix.fillna(0.0)  # no-trade subperiod = flat, not evidence
    pbo = cscv_pbo(pbo_matrix, n_partitions=6, max_trials=2000, seed=cfg.seed)
    print(f"[pbo] {pbo.summary()}")
    for _, r in sweep_df.iterrows():
        print(f"   {r['params']}: full sharpe={r['sharpe_full']:.2f} "
              f"subperiods={[round(x, 2) if np.isfinite(x) else None for x in r['subperiods']]}")

    stab = stability_summary(pd.DataFrame(
        [{"metrics": {"sharpe": r["sharpe_full"]}} for _, r in sweep_df.iterrows()]))
    print(f"[stability] median sharpe {stab['median']:.2f}, p25 {stab['p25']:.2f}, "
          f"p75 {stab['p75']:.2f}, frac positive {stab['frac_positive']:.0%}")

    # ------------------------------------------------------- perturbation
    banner("PHASE 9 — parameter perturbation stress")
    pert = stress.stress_parameter_perturbation(
        lambda p: TrendStrategy(p),
        {"trend_fast": sp.trend_fast, "trend_slow": sp.trend_slow},
        bars, regimes[list(bars)[0]], cfg, frac=0.15, n=10, seed=cfg.seed)
    print(f"[perturbation] sharpe: median={pert['sharpe'].median():.2f} "
          f"min={pert['sharpe'].min():.2f} frac>0={(pert['sharpe'] > 0).mean():.0%}")

    # ----------------------------------------------------------- ablation
    banner("PHASE 10 — feature ablation (ML)")
    groups = [
        ("volume", [c for c in X.columns if c.startswith(("rel_vol", "vol_accel"))]),
        ("time", [c for c in X.columns if c in ("hour", "dow", "month", "session")]),
        ("regime", [c for c in X.columns if c.startswith("regime_")]),
        ("momentum", [c for c in X.columns if c.startswith("mom_")]),
        ("volatility", [c for c in X.columns if c.startswith(("vol_", "atr"))]),
    ]

    def fit_eval(feature_list: list[str]):
        rec = factory.build("logistic", feature_list, "x", "y")
        r = walk_forward_ml(X[feature_list], y, rec, n_splits=3, embargo_bars=24,
                            min_train=max(1000, len(X) // 12))
        return {"oos_auc": r["oos_auc"]}

    abl = ablation(groups, fit_eval, list(X.columns), metric="oos_auc")
    print(abl.to_string(index=False))

    # ------------------------------------------------------------- drift
    banner("PHASE 11 — drift detection")
    tr_idx = X.index[: len(X) // 2]
    lv_idx = X.index[len(X) // 2:]
    # PSI on stationary features only: price LEVELS (ma_, vwap_) are
    # non-stationary by construction, so their PSI is not a drift signal.
    stationary = [c for c in X.columns
                  if not c.startswith(("ma_", "vwap_", "hour", "dow", "month", "session"))]
    drift_df = feature_drift_report(X.loc[tr_idx, stationary], X.loc[lv_idx, stationary])
    print(f"[drift] features with PSI alert (stationary set): "
          f"{int(drift_df['alert'].sum())} of {len(drift_df)}  "
          f"(top: {drift_df.head(3)[['feature', 'psi']].to_dict('records')})")
    perf_drift = performance_drift_report(res.trades, window=30)
    print(f"[drift] performance: {perf_drift}")

    # ----------------------------------------------- paper broker + gates
    banner("PHASE 12 — paper broker, order validation, failure injection")
    pb = PaperBroker(bars, cfg, seed=5)
    validator = OrderValidator(cfg.risk, cfg.sizing)
    pb.set_clock(bars[sym0].index[100])
    quotes = pb.get_quotes([sym0])
    vr = validator.validate(
        symbol=sym0, direction=1, qty=100, price=quotes[sym0]["ask"],
        quote=quotes[sym0], positions={}, open_orders=[],
        equity=cfg.initial_equity, data_fresh=True, market_open=True,
        broker_healthy=True, model_approved=True, daily_loss_halted=False,
        risk_new_trades_allowed=True,
        bar_volume=float(bars[sym0].iloc[100]["volume"]),
        now=bars[sym0].index[100],
    )
    print(f"[order-validation] {vr.summary()}")
    if vr.ok:
        o = Order(order_id="", symbol=sym0, side="buy", qty=100)
        filled = pb.submit_order(o)
        print(f"[paper] order {filled.status} @ {filled.fill_price:.2f} "
              f"(slippage {filled.realized_slippage_bps:.1f} bps)")
    pb.inject_failure(healthy=False)
    o2 = Order(order_id="", symbol=sym0, side="sell", qty=100)
    rejected = pb.submit_order(o2)
    print(f"[paper] after broker-failure injection: {rejected.status} "
          f"({rejected.reject_reason})")
    pb.inject_failure(healthy=True)
    print(f"[paper] account: {pb.get_account().as_dict()}")

    # ---------------------------------------------------------- registries
    banner("PHASE 13 — registries")
    exp_reg = ExperimentRegistry(ARTIFACTS / "experiments.jsonl")
    exp_reg.append_experiment({
        "hypothesis": "Vol-adjusted MA trend + TSMOM + z-reversion + compression "
                      "breakout ensemble, meta-gated, beats random baseline after costs "
                      "on synthetic regime data",
        "dataset": "synthetic regime-switching OHLCV, 3 symbols, hourly "
                   f"{cfg.start}..{cfg.end}",
        "features": "returns, vol family, momentum family, z-scores, "
                    "rel-volume, time, regime (see features.py)",
        "model": "rule ensemble + meta decision (no ML in the loop)",
        "parameters": json.dumps(config_section(cfg)),
        "training_period": "none (rules; parameters locked from config)",
        "validation_period": str(split.date()),
        "oos_period": f"{split.date()}..{cfg.end}",
        "costs": "commission + half-spread + slippage + impact (config)",
        "results": {"full_sharpe": res.metrics["sharpe"],
                    "oos_sharpe": res_oos.metrics["sharpe"] if res_oos else None,
                    "oos_maxdd": res_oos.metrics["max_drawdown"] if res_oos else None},
        "drawdown": res.metrics["max_drawdown"],
        "robustness": {"pbo": pbo.pbo, "stab": stab, "perturbation_median": pert["sharpe"].median()},
        "failure_cases": "high-vol regimes; latency > 3 bars; cost x10",
        "decision": C.DECISION_RESEARCH_MORE,
    })
    print(f"[registry] experiments recorded: {exp_reg.count()}")

    model_reg = ModelRegistry(ARTIFACTS / "models.jsonl")
    for family, r in ml_results.items():
        rec = factory.build(family, list(X.columns), str(X.index[0]), str(X.index[-1]))
        rec.oos_metrics = {k: v for k, v in r.items()
                           if k not in ("oos_true", "oos_pred", "reliability")}
        model_reg.register(rec.to_dict())
    print(f"[registry] models recorded: {model_reg.count()}")

    # --------------------------------------------- report + dashboard
    banner("PHASE 14 — report + dashboard")
    report_path = ARTIFACTS / "research_report.md"
    stress_md = [DISCLAIMER, ""]
    stress_md.append("## Full-period backtest")
    stress_md.append(backtest_report(res, "Full-period ensemble (synthetic)"))
    stress_md.append("\n## In-sample vs out-of-sample\n")
    stress_md.append("**IS** (before split): "
                     f"sharpe {res_is.metrics['sharpe']:.2f}, "
                     f"return {res_is.metrics['total_return']:.2%}, "
                     f"maxDD {res_is.metrics['max_drawdown']:.2%}\n")
    if res_oos is not None:
        stress_md.append("**OOS** (after split): "
                         f"sharpe {res_oos.metrics['sharpe']:.2f}, "
                         f"return {res_oos.metrics['total_return']:.2%}, "
                         f"maxDD {res_oos.metrics['max_drawdown']:.2%}\n")
    else:
        stress_md.append("**OOS**: no data in window (skipped)\n")
    for name, df in stress_out.items():
        stress_md.append(stress_section(f"Stress: {name}", df))
    stress_md.append("\n## PBO (CSCV)\n")
    stress_md.append(f"**{pbo.summary()}**\n")
    stress_md.append("\n## ML walk-forward (pooled OOS)\n")
    stress_md.append("| family | AUC | accuracy | ECE | Brier | n |")
    stress_md.append("|---|---|---|---|---|---|")
    for family, r in ml_results.items():
        stress_md.append(f"| {family} | {r['oos_auc']:.4f} | {r['oos_accuracy']:.3f} "
                         f"| {r['ece']:.3f} | {r['brier']:.4f} | {r['n_oos']} |")
    stress_md.append("\n## Ablation (logistic, Δ OOS AUC vs all features)\n")
    stress_md.append(abl.to_markdown(index=False))
    stress_md.append("\n## Risk engine summary\n")
    stress_md.append(f"```json\n{json.dumps(res.risk_summary, default=str, indent=2)}\n```")
    stress_md.append("\n## Config\n")
    stress_md.append(config_section(cfg))
    report_path.write_text("\n".join(stress_md))
    print(f"[report] written to {report_path}")

    dash = generate_dashboard(
        res, ARTIFACTS / "dashboard.html",
        title="Serein — synthetic research dashboard",
        extra_sections=[
            ("Stress summary", _stress_table(stress_out)),
            ("PBO", f"<pre>{pbo.summary()}</pre>"),
        ],
    )
    print(f"[dashboard] written to {dash}")

    print(f"\nTotal pipeline time: {time.time() - t0:.1f}s")
    print("\nNOTE: all numbers above are from SYNTHETIC data. No performance "
          "claim about real markets is made or implied.")
    return 0


def _stress_table(stress_out: dict) -> str:
    rows = []
    for name, df in stress_out.items():
        for _, r in df.iterrows():
            rows.append(f"<tr><td>{name}</td><td>{r['shock']}</td>"
                        f"<td>{r['total_return']:.2%}</td><td>{r['sharpe']:.2f}</td>"
                        f"<td>{r['max_drawdown']:.2%}</td></tr>")
    return ("<table class='tbl'><tr><th>family</th><th>shock</th><th>return</th>"
            f"<th>sharpe</th><th>maxdd</th></tr>{''.join(rows)}</table>")


if __name__ == "__main__":
    sys.exit(main())
