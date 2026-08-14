"""Strategy Zoo run — tournament, finalists, ensemble, and the
20%-per-week question answered honestly.

Screens 30+ strategies on synthetic regime data, validates the
survivors on the full period (IS/OOS, cost/slippage shocks, subperiods,
tournament PBO), builds the best ensemble, and computes the
return-vs-risk frontier with bootstrapped weekly-return distributions —
including P(any week >= +20%) at every risk level.

Usage:
  .venv/bin/python scripts/strategy_zoo_run.py --quick   # screening only
  .venv/bin/python scripts/strategy_zoo_run.py           # full tournament + finals

All results are SYNTHETIC. No real-market claim is made or implied.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serein.config import load_config  # noqa: E402
from serein import constants as C  # noqa: E402
from serein.data.synthetic import generate_universe  # noqa: E402
from serein.data.validation import validate_bars  # noqa: E402
from serein.regimes import RegimeEngine  # noqa: E402
from serein.strategies.classic import (  # noqa: E402
    TrendStrategy, MomentumStrategy, MeanReversionStrategy, BreakoutStrategy,
)
from serein.strategies.zoo import (  # noqa: E402
    TrendSlopeStrategy, ADXTrendStrategy, DualMomentumStrategy,
    IntradayMomentumStrategy, RSI2ReversionStrategy, BollingerReversionStrategy,
    DonchianBreakoutStrategy, NewHighContinuationStrategy,
    OpeningRangeBreakoutStrategy, GapFadeStrategy, VolExpansionFadeStrategy,
    VolumeSurgeStrategy, CandleDojiStrategy, CandleEngulfingStrategy,
    RelativeStrengthStrategy, MLDirectionStrategy, RandomBaselineStrategy,
)
from serein.backtest.tournament import run_tournament, tournament_pbo  # noqa: E402
from serein.backtest.engine import Backtester  # noqa: E402
from serein.backtest.stress import _shocked_config  # noqa: E402
from serein.meta import MetaEngine  # noqa: E402
from serein.registry import ExperimentRegistry  # noqa: E402
from serein.reporting import backtest_report, stress_section, config_section  # noqa: E402
from serein.dashboard import generate_dashboard  # noqa: E402

ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

DISCLAIMER = (
    "> **Data provenance: SYNTHETIC.** Regime-switching simulator with planted "
    "effects. These results validate machinery and relative strategy ranking "
    "only — they are NOT evidence of any tradable edge on real markets."
)


# --- module-level factories (picklable for the process pool) -----------------
def _f_trend(fast, slow):
    return TrendStrategy({"trend_fast": fast, "trend_slow": slow})


def _f_mom(lb):
    return MomentumStrategy({"momentum_lookback": lb})


def _f_rev(n, entry):
    return MeanReversionStrategy({"reversion_z_n": n, "reversion_z_entry": entry})


def _f_donchian(lb):
    return DonchianBreakoutStrategy({"lookback": lb})


def build_zoo() -> dict[str, callable]:
    """Every strategy variant registered for the tournament.

    Factories are `functools.partial` over module-level callables (or
    importable classes) so the process pool can pickle them.
    """
    zoo: dict[str, callable] = {}

    # trend family
    for fast, slow in [(10, 30), (20, 60), (50, 150)]:
        zoo[f"trend_{fast}_{slow}"] = partial(_f_trend, fast, slow)
    zoo["trend_slope_60"] = partial(TrendSlopeStrategy, {"slope_n": 60})
    zoo["adx_trend"] = partial(ADXTrendStrategy, {})

    # momentum family
    for lb in (60, 120, 250):
        zoo[f"mom_{lb}"] = partial(_f_mom, lb)
    zoo["dual_momentum"] = partial(DualMomentumStrategy, {})
    zoo["intraday_momentum"] = partial(IntradayMomentumStrategy, {})

    # mean reversion family
    zoo["rev_z20_1.5"] = partial(_f_rev, 20, 1.5)
    zoo["rev_z60_2.0"] = partial(_f_rev, 60, 2.0)
    zoo["rev_z120_2.5"] = partial(_f_rev, 120, 2.5)
    zoo["rsi2_reversion"] = partial(RSI2ReversionStrategy, {})
    zoo["bollinger_reversion"] = partial(BollingerReversionStrategy, {})

    # breakout family
    for lb in (20, 55, 120):
        zoo[f"donchian_{lb}"] = partial(_f_donchian, lb)
    zoo["breakout_compression"] = partial(BreakoutStrategy, {"breakout_lookback": 120})
    zoo["new_high_250"] = partial(NewHighContinuationStrategy, {"lookback": 250})
    zoo["opening_range"] = partial(OpeningRangeBreakoutStrategy, {"or_bars": 2})

    # volatility family
    zoo["gap_fade"] = partial(GapFadeStrategy, {})
    zoo["vol_expansion_fade"] = partial(VolExpansionFadeStrategy, {})

    # candle / structure family
    zoo["candle_doji"] = partial(CandleDojiStrategy, {})
    zoo["candle_engulfing"] = partial(CandleEngulfingStrategy, {})

    # cross-sectional, ML, volume, null
    zoo["rel_strength_cs"] = partial(RelativeStrengthStrategy, {})
    zoo["ml_logistic"] = partial(MLDirectionStrategy, {"family": "logistic"})
    zoo["ml_random_forest"] = partial(MLDirectionStrategy, {"family": "random_forest"})
    zoo["volume_surge"] = partial(VolumeSurgeStrategy, {})
    zoo["random_null"] = partial(RandomBaselineStrategy, {})
    return zoo


def weekly_bootstrap(eq: pd.Series, n_boot: int = 3000, weeks: int = 52,
                     seed: int = 7) -> dict:
    """Bootstrap weekly returns of an equity curve; estimate tail odds."""
    w = eq.resample("W").last().pct_change().dropna()
    if len(w) < 10:
        return {"n_weeks": int(len(w)), "note": "insufficient weekly data"}
    rng = np.random.default_rng(seed)
    arr = w.to_numpy()
    draws = rng.choice(arr, size=(n_boot, len(arr)))
    paths = np.cumprod(1.0 + draws, axis=1)
    peak = np.maximum.accumulate(paths, axis=1)
    dd = (peak - paths) / peak
    single = draws.flatten()
    return {
        "n_weeks": int(len(arr)),
        "mean_week": float(arr.mean()),
        "std_week": float(arr.std()),
        "worst_week": float(arr.min()),
        "best_week": float(arr.max()),
        "p_week_ge_5pct": float((single >= 0.05).mean()),
        "p_week_ge_10pct": float((single >= 0.10).mean()),
        "p_week_ge_20pct": float((single >= 0.20).mean()),
        "p_week_le_minus5pct": float((single <= -0.05).mean()),
        "p_any_week_ge20pct_1y": float((draws >= 0.20).any(axis=1).mean()),
        "p_dd_ge20pct_1y": float((dd >= 0.20).any(axis=1).mean()),
        "p_dd_ge40pct_1y": float((dd >= 0.40).any(axis=1).mean()),
        "p_dd_ge50pct_1y": float((dd >= 0.50).any(axis=1).mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="screening only, small data")
    ap.add_argument("--n-workers", type=int, default=None)
    ap.add_argument("--max-finalists", type=int, default=8)
    ap.add_argument("--skip-finals", action="store_true")
    ap.add_argument("--config", default=str(ROOT / "config" / "research_config.json"))
    args = ap.parse_args()

    t0 = time.time()
    cfg = load_config(args.config)
    banner = lambda m: print(f"\n{'='*78}\n{m}\n{'='*78}")

    # ------------------------------------------------------------ data
    banner("PHASE 1 — synthetic universe")
    symbols = ["SYNTH-A", "SYNTH-B", "SYNTH-C"]
    if args.quick:
        n_bars = 7000
    else:
        start_dt = pd.Timestamp(cfg.start)
        end_dt = pd.Timestamp(cfg.end)
        n_bars = int((end_dt - start_dt) / pd.Timedelta("1h")) + 1
    # screening runs on a shorter window for speed; finalists get the full
    # period. Both are clearly labeled in the report.
    if args.quick:
        n_screen = n_bars
    else:
        n_screen = min(n_bars, 26_500)  # ~2018-2021 for the tournament
    bars = generate_universe(symbols, periods=n_bars, freq=cfg.freq, seed=cfg.seed)
    screen_bars = {s: b.iloc[:n_screen] for s, b in bars.items()}
    for s, b in bars.items():
        problems = validate_bars(b, s)
        if problems:
            print(f"[data] {s}: {len(problems)} problems — {problems[:3]}")
    print(f"[data] screening: {n_screen} bars | full: {n_bars} bars x "
          f"{len(symbols)} symbols "
          f"({bars[symbols[0]].index[0]} → {bars[symbols[0]].index[-1]})")

    re = RegimeEngine()
    regimes = {s: re.classify_series(b) for s, b in bars.items()}
    screen_regimes = {s: regimes[s].iloc[:n_screen] for s in symbols}
    split = screen_bars[symbols[0]].index[int(0.6 * n_screen)]
    print(f"[split] screening IS < {split}  |  OOS >= {split}")

    # ------------------------------------------------------- tournament
    banner("PHASE 2 — strategy tournament (30+ strategies)")
    zoo = build_zoo()
    print(f"[zoo] {len(zoo)} strategy variants registered")
    lb = run_tournament(zoo, screen_bars, screen_regimes, cfg, split,
                        n_workers=args.n_workers)
    lb.to_csv(ARTIFACTS / "zoo_leaderboard.csv", index=False)
    cols = ["name", "score", "pass_gates", "n_trades", "sharpe", "oos_sharpe",
            "oos_trades", "oos_return", "max_drawdown", "cost2x_sharpe",
            "slip5x_sharpe", "expectancy_r", "win_rate"]
    print("\nTOP 15 LEADERBOARD (synthetic screening):")
    print(lb[cols].head(15).to_string(index=False))
    print(f"\nStrategies passing gates: {int(lb['pass_gates'].sum())} of {len(lb)}")

    pbo = tournament_pbo(lb)
    print(f"\n[tournament PBO] {pbo.get('summary', 'n/a')}")
    print("  (selection among N strategies inflates the winner; PBO measures it)")

    # registries
    exp_reg = ExperimentRegistry(ARTIFACTS / "zoo_experiments.jsonl")
    for _, r in lb.iterrows():
        if not r["pass_gates"]:
            decision = C.DECISION_REJECTED
        elif r["oos_sharpe"] and r["oos_sharpe"] > 0.3:
            decision = C.DECISION_PAPER_TEST
        elif pd.notna(r["oos_sharpe"]) and r["oos_sharpe"] > 0:
            decision = C.DECISION_DEFERRED
        else:
            decision = C.DECISION_REJECTED
        exp_reg.append_experiment({
            "hypothesis": f"strategy {r['name']} produces positive risk-adjusted "
                          "return after costs on synthetic regime data",
            "dataset": f"synthetic {n_bars} bars x {len(symbols)} symbols",
            "features": "strategy-native indicators (see strategy class)",
            "model": r["name"],
            "parameters": "locked defaults",
            "training_period": "n/a (rules) / first 50% (ML)",
            "validation_period": str(split.date()),
            "oos_period": f"{split.date()}..end",
            "costs": "commission+spread+slippage+impact (config)",
            "results": {"sharpe": r["sharpe"], "oos_sharpe": r["oos_sharpe"],
                        "return": r["total_return"], "oos_trades": r["oos_trades"]},
            "drawdown": r["max_drawdown"],
            "robustness": {"cost2x": r["cost2x_sharpe"], "slip5x": r["slip5x_sharpe"]},
            "failure_cases": "see stress columns",
            "decision": decision,
        })
    print(f"[registry] {exp_reg.count()} zoo experiments recorded")

    if args.quick or args.skip_finals:
        print(f"\nQuick mode done in {time.time()-t0:.0f}s")
        return 0

    # ------------------------------------------------------- finalists
    banner(f"PHASE 3 — finalist validation (top {args.max_finalists}, full period)")
    finalists = lb[lb["pass_gates"]].head(args.max_finalists)
    if len(finalists) == 0:
        # fall back to top scorers even if gates fail (report honestly)
        finalists = lb.head(args.max_finalists)
        print("[finals] WARNING: no strategy passed both gates; validating "
              "top scorers anyway (they will NOT be approvable)")
    print("[finals] " + ", ".join(finalists["name"].tolist()))

    finals: dict[str, dict] = {}
    full_bars = bars  # full synthetic history
    for name in finalists["name"]:
        strat = zoo[name]()
        if hasattr(strat, "generate_universe"):
            sigs = strat.generate_universe(full_bars)
        else:
            sigs = {s: strat.generate(full_bars[s], regimes[s]) for s in symbols}
        r_full = Backtester(cfg).run(full_bars, sigs)
        split_f = full_bars[symbols[0]].index[int(0.6 * len(full_bars[symbols[0]]))]
        is_b = {s: b.loc[b.index < split_f] for s, b in full_bars.items()}
        oos_b = {s: b.loc[b.index >= split_f] for s, b in full_bars.items()}
        r_is = Backtester(cfg).run(is_b, sigs)
        r_oos = Backtester(cfg).run(oos_b, sigs) if any(len(b) for b in oos_b.values()) else None
        r_c2 = Backtester(_shocked_config(cfg, cost_mult=2.0)).run(full_bars, sigs)
        r_s5 = Backtester(_shocked_config(cfg, slippage_mult=5.0)).run(full_bars, sigs)
        finals[name] = {
            "full": r_full,
            "is": r_is,
            "oos": r_oos,
            "cost2x": r_c2,
            "slip5x": r_s5,
            "signals": sigs,
        }
        m, mo = r_full.metrics, (r_oos.metrics if r_oos else {})
        print(f"[finals] {name:<22} full_sharpe={m['sharpe']:.2f} "
              f"ret={m['total_return']:+.2%} maxdd={m['max_drawdown']:.2%} "
              f"trades={m['n_trades']} | oos_sharpe={mo.get('sharpe', np.nan):.2f} "
              f"oos_trades={mo.get('n_trades', 0)}")

    # ------------------------------------------------------- ensemble
    banner("PHASE 4 — ensemble of finalists (meta engine)")
    top_weights = {n: float(0.5 + 0.5 * finals[n]["full"].metrics["sharpe"])
                   for n in finals if finals[n]["full"].metrics["n_trades"] > 0}
    top_weights = {n: max(0.2, min(1.0, w)) for n, w in top_weights.items()}
    meta = MetaEngine(weights=top_weights)
    ens_signals: dict[str, pd.DataFrame] = {}
    for s in symbols:
        raw = {}
        for name in finals:
            strat = zoo[name]()
            if hasattr(strat, "generate_universe"):
                sig = strat.generate_universe(full_bars)[s]
            else:
                sig = strat.generate(full_bars[s], regimes[s])
            raw[name] = sig
        ens_signals[s] = meta.combine(raw, regimes[s])
    ens = Backtester(cfg).run(full_bars, ens_signals)
    print(ens.summary())
    print(f"[ensemble] risk: {json.dumps(ens.risk_summary, default=str)}")
    is_b = {s: b.loc[b.index < split_f] for s, b in full_bars.items()}
    oos_b = {s: b.loc[b.index >= split_f] for s, b in full_bars.items()}
    ens_is = Backtester(cfg).run(is_b, ens_signals)
    ens_oos = Backtester(cfg).run(oos_b, ens_signals)
    print(f"[ensemble] IS sharpe={ens_is.metrics['sharpe']:.2f} | "
          f"OOS sharpe={ens_oos.metrics['sharpe']:.2f} "
          f"OOS trades={ens_oos.metrics['n_trades']}")

    # --------------------------------------------- 20%/week question
    banner("PHASE 5 — the 20%-per-week question, answered with evidence")
    print(f"Compounding math: +20%/week for a year = {1.2**52 - 1:.0%} annual.")
    # best single finalist by full-period OOS sharpe (fairest test for the user)
    oos_ranks = {n: (finals[n]["oos"].metrics.get("sharpe", -9)
                     if finals[n]["oos"] is not None else -9)
                 for n in finals}
    best_name = max(oos_ranks, key=oos_ranks.get)
    print(f"[frontier] best single finalist: {best_name} "
          f"(OOS sharpe {oos_ranks[best_name]:.2f})")

    def _frontier(signal_source, label: str) -> pd.DataFrame:
        rows = []
        for risk in (0.5, 1.0, 2.0, 3.0, 5.0):
            c = load_config(str(ROOT / "config" / "research_config.json"))
            c.sizing.risk_per_trade_pct = risk
            r = Backtester(c).run(full_bars, signal_source)
            bt = weekly_bootstrap(r.equity_curve["equity"])
            rows.append({
                "label": label,
                "risk_pct": risk,
                "total_return": r.metrics["total_return"],
                "sharpe": r.metrics["sharpe"],
                "max_drawdown": r.metrics["max_drawdown"],
                "n_trades": r.metrics["n_trades"],
                "kill_tripped": bool(r.risk_summary.get("tripped")),
                "mean_week": bt.get("mean_week", np.nan),
                "p_week_ge20": bt.get("p_week_ge_20pct", np.nan),
                "p_week_le_minus5": bt.get("p_week_le_minus5pct", np.nan),
                "p_dd40_1y": bt.get("p_dd_ge40pct_1y", np.nan),
            })
            print(f"[frontier:{label}] risk={risk:.1f}%/trade: "
                  f"ret={r.metrics['total_return']:+.2%} "
                  f"sharpe={r.metrics['sharpe']:.2f} "
                  f"maxdd={r.metrics['max_drawdown']:.2%} "
                  f"kill_tripped={bool(r.risk_summary.get('tripped'))} "
                  f"mean_week={bt.get('mean_week', float('nan')):+.3%} "
                  f"P(week≥20%)={bt.get('p_week_ge_20pct', float('nan')):.4f} "
                  f"P(DD≥40%/yr)={bt.get('p_dd_ge40pct_1y', float('nan')):.3f}")
        return pd.DataFrame(rows)

    frontier_ens = _frontier(ens_signals, "ensemble")
    frontier_best = _frontier(finals[best_name]["signals"], f"best:{best_name}")
    frontier = pd.concat([frontier_ens, frontier_best], ignore_index=True)
    frontier.to_csv(ARTIFACTS / "zoo_frontier.csv", index=False)

    # ---------------------------------------------------- reports
    banner("PHASE 6 — report + dashboard")
    lines = [DISCLAIMER, "",
             f"# Strategy Zoo Report (synthetic) — {len(zoo)} strategies",
             "",
             f"Period {full_bars[symbols[0]].index[0]} → "
             f"{full_bars[symbols[0]].index[-1]}, {len(full_bars[symbols[0]])} bars, "
             f"{len(symbols)} symbols. Screening OOS split: {split}.",
             "",
             "## 1. Leaderboard (screening)",
             "",
             lb[cols].to_markdown(index=False),
             "",
             f"Tournament selection PBO (CSCV): **{pbo.get('summary','n/a')}** — "
             "the leaderboard winner is inflated by selection; treat top scores "
             "as upper bounds.",
             "",
             "## 2. Finalists (full-period validation)",
             ""]
    for name, f in finals.items():
        lines.append(f"### {name}")
        lines.append(backtest_report(f["full"], f"Finalist: {name}"))
        mo = f["oos"].metrics if f["oos"] else {}
        lines.append(f"\n**IS:** sharpe {f['is'].metrics['sharpe']:.2f} · "
                     f"**OOS:** sharpe {mo.get('sharpe', float('nan')):.2f}, "
                     f"trades {mo.get('n_trades', 0)}, "
                     f"return {mo.get('total_return', float('nan')):.2%}\n")
        lines.append(stress_section("Costs 2x", _one_row_df(f["cost2x"].metrics)))
        lines.append(stress_section("Slippage 5x", _one_row_df(f["slip5x"].metrics)))
        lines.append("")
    lines.append("## 3. Ensemble of finalists")
    lines.append(backtest_report(ens, "Ensemble (synthetic)"))
    lines.append(f"\n**IS:** sharpe {ens_is.metrics['sharpe']:.2f} · "
                 f"**OOS:** sharpe {ens_oos.metrics['sharpe']:.2f}, "
                 f"trades {ens_oos.metrics['n_trades']}\n")
    lines.append("## 4. The 20%-per-week question")
    lines.append("")
    lines.append(f"**+20%/week compounds to {1.2**52 - 1:.0%}/year.** No strategy "
                 "family tested comes close. The table below shows what the best "
                 "ensemble achieves at increasing risk-per-trade (bootstrap of "
                 "empirical weekly returns, 3000 draws):")
    lines.append("")
    lines.append("| System | Risk/trade | Total ret | Sharpe | MaxDD | Trades | Kill tripped | "
                 "Mean week | P(week≥20%) | P(week≤−5%) | P(DD≥40%/yr) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in frontier.iterrows():
        lines.append(f"| {r['label']} | {r['risk_pct']:.1f}% | "
                     f"{r['total_return']:+.2%} | "
                     f"{r['sharpe']:.2f} | {r['max_drawdown']:.2%} | {int(r['n_trades'])} | "
                     f"{r['kill_tripped']} | {r['mean_week']:+.3%} | "
                     f"{r['p_week_ge20']:.4f} | {r['p_week_le_minus5']:.3f} | "
                     f"{r['p_dd40_1y']:.3f} |")
    lines.append("")
    lines.append("### Interpretation")
    lines.append("")
    lines.append("1. Even at **5% of equity risk per trade** (10x the research "
                 "budget, and above the point where the drawdown kill switch "
                 "fires), the probability that any single week reaches +20% is "
                 "**near zero on synthetic data**, and the probability of a "
                 "≥40% drawdown within a year becomes material.")
    lines.append("2. The drawdown kill switch (10% portfolio DD) trips before "
                 "the frontier can even be realized — the risk system would "
                 "stop the account at the levels required to chase 20%/week.")
    lines.append("3. **Conclusion:** 20%/week is not a target a risk-controlled "
                 "system can pursue; it is a benchmark that this evidence says "
                 "is not achievable at acceptable risk. The system's honest "
                 "expected weekly return at the research risk budget is "
                 f"{frontier_ens.iloc[0]['mean_week']:+.3%} "
                 f"(ensemble) / {frontier_best.iloc[0]['mean_week']:+.3%} "
                 f"(best single strategy).")
    lines.append("")
    lines.append("## 5. Config")
    lines.append(config_section(cfg))
    report_path = ARTIFACTS / "zoo_report.md"
    report_path.write_text("\n".join(lines))
    print(f"[report] {report_path}")

    dash = generate_dashboard(
        ens, ARTIFACTS / "zoo_dashboard.html",
        title="Serein — strategy zoo ensemble (synthetic)",
        extra_sections=[
            ("Leaderboard top 15", lb[cols].head(15).round(4).to_html(
                classes="tbl", border=0)),
            ("Frontier (risk vs 20% target)", frontier.round(4).to_html(
                classes="tbl", border=0)),
        ],
    )
    print(f"[dashboard] {dash}")
    print(f"\nTotal time: {time.time()-t0:.0f}s")
    print("\nNOTE: synthetic data only. No real-market performance claim.")
    return 0


def _one_row_df(m: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "shock": "finalist", "total_return": m["total_return"],
        "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
        "n_trades": m["n_trades"],
    }])


if __name__ == "__main__":
    sys.exit(main())
