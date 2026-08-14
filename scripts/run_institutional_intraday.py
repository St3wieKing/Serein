#!/usr/bin/env python3
"""Research harness for the institutional-inspired intraday strategy.

All generated results are synthetic engineering evidence. The script explicitly
cannot test or reproduce Citadel's proprietary strategy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serein.backtest.engine import Backtester
from serein.backtest.robustness import cscv_pbo
from serein.backtest.stress import stress_costs, stress_latency, stress_slippage
from serein.backtest.uncertainty import block_bootstrap_equity, trade_expectancy_bootstrap
from serein.config import BacktestConfig, CostModel, RiskLimits, SizingParams
from serein.data.intraday_synthetic import generate_intraday_universe
from serein.strategies.institutional_intraday import (
    InstitutionalIntradayStrategy, IntradayMetaLabelStrategy,
)

ART = ROOT/"artifacts"


def config() -> BacktestConfig:
    return BacktestConfig(
        freq="5min", initial_equity=100_000, max_holding_bars=24,
        stop_atr_mult=1.5, target_rr=1.8, allow_shorts=True, seed=2026,
        costs=CostModel(commission_per_share=.003, half_spread_bps=1.5,
                        slippage_bps=2.0, impact_coeff=2.0),
        sizing=SizingParams(risk_per_trade_pct=.25, confidence_floor=.52,
                            max_confidence_mult=1.2, target_annual_vol_pct=10,
                            max_notional_frac=.20, max_adv_share=.01,
                            min_order_notional=500),
        risk=RiskLimits(max_positions=3, max_gross_exposure_frac=.60,
                        max_net_exposure_frac=.40, max_per_symbol_frac=.20,
                        max_leverage=1.0, daily_loss_limit_pct=.75,
                        weekly_loss_limit_pct=2.0, max_portfolio_drawdown_pct=6.0,
                        max_consecutive_losses=5, max_daily_trades=6,
                        max_trading_freq_per_hour=2, emergency_equity_floor_frac=.90),
    )


def window(bars, start=None, end=None):
    return {s: b.loc[(b.index >= start if start is not None else True)
                     & (b.index < end if end is not None else True)] for s, b in bars.items()}


def evaluate(name, bars, signals, cfg):
    r = Backtester(cfg).run(bars, signals)
    m = r.metrics
    return {"name": name, "trades": m["n_trades"], "return": m["total_return"],
            "sharpe": m["sharpe"], "max_dd": m["max_drawdown"],
            "win_rate": m["win_rate"], "profit_factor": m["profit_factor"],
            "expectancy_r": m["expectancy_r"], "costs": m["costs_total"],
            "profitable_days": m.get("profitable_days_pct"),
            "weekly_mean": m.get("weekly_mean"),
            "risk_tripped": ",".join(r.risk_summary.get("tripped", []))}


def filtered(signals, allowed):
    out = {s: x.copy() for s, x in signals.items()}
    for x in out.values():
        mask = ~x.reason.str.split("+").str[0].isin(allowed)
        x.loc[mask, "direction"] = 0; x.loc[mask, "confidence"] = 0.0
    return out


def fmt_table(df):
    d = df.copy()
    for c in ("return", "max_dd", "win_rate", "profitable_days", "weekly_mean"):
        if c in d: d[c] = d[c].map(lambda x: "n/a" if pd.isna(x) else f"{x:.2%}")
    for c in ("sharpe", "profit_factor", "expectancy_r"):
        if c in d: d[c] = d[c].map(lambda x: "n/a" if pd.isna(x) else f"{x:.2f}")
    return d.to_markdown(index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=320)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    if args.days < 200:
        raise SystemExit("at least 200 days required")
    symbols = ["SPY", "QQQ", "IWM"]
    bars, truth = generate_intraday_universe(symbols, days=args.days, seed=args.seed)
    dates = pd.DatetimeIndex(sorted(bars["SPY"].index.normalize().unique()))
    train_end = dates[int(.50*len(dates))]
    val_end = dates[int(.75*len(dates))]
    cfg = config()

    strategies = {
        "rules": InstitutionalIntradayStrategy(),
        "meta_logistic": IntradayMetaLabelStrategy({"train_end": train_end, "family": "logistic"}),
        "meta_gradient_boosting": IntradayMetaLabelStrategy({"train_end": train_end, "family": "gradient_boosting"}),
    }
    sigs = {n: st.generate_universe(bars) for n, st in strategies.items()}
    diagnostics = {n: getattr(st, "diagnostics", {}) for n, st in strategies.items()}
    val_b = window(bars, train_end, val_end); test_b = window(bars, val_end, None)
    val = pd.DataFrame([evaluate(n, val_b, sig, cfg) for n, sig in sigs.items()])

    # Champion is selected on validation only. OOS remains untouched until now.
    eligible = val[(val.trades >= 20) & (val.sharpe.notna())]
    if len(eligible):
        champion = str(eligible.sort_values(["sharpe", "max_dd"], ascending=False).iloc[0]["name"])
    else:
        champion = "rules"
    test = pd.DataFrame([evaluate(n, test_b, sig, cfg) for n, sig in sigs.items()])

    # Controlled setup ablation on locked OOS.
    abl = []
    for setup in ("opening_breakout", "vwap_pullback", "vwap_reversion"):
        abl.append(evaluate(setup, test_b, filtered(sigs["rules"], {setup}), cfg))
    ablation = pd.DataFrame(abl)

    # OOS stress of the validation-selected champion.
    cs = sigs[champion]
    costs = stress_costs(test_b, cs, cfg, multipliers=(1, 2, 5))
    slips = stress_slippage(test_b, cs, cfg, multipliers=(1, 2, 5))
    latency = stress_latency(test_b, cs, cfg, delays=(0, 1, 3))

    # The predeclared OR ablation was strongest only after OOS was viewed, so it
    # is a POST-OOS challenger, never retroactively called the champion. Stress
    # and fresh synthetic seeds are reported to decide whether it deserves a
    # future real-data experiment—not to claim an edge.
    orb_sig = filtered(sigs["rules"], {"opening_breakout"})
    orb_result = Backtester(cfg).run(test_b, orb_sig)
    orb_uncertainty = {
        "equity": block_bootstrap_equity(orb_result.equity_curve.equity,
                                           block=5, n_boot=2000, seed=42),
        "expectancy": trade_expectancy_bootstrap(orb_result.trades,
                                                   n_boot=5000, seed=42),
    }
    orb_costs = stress_costs(test_b, orb_sig, cfg, multipliers=(1, 2, 5))
    orb_slips = stress_slippage(test_b, orb_sig, cfg, multipliers=(1, 2, 5))
    orb_latency = stress_latency(test_b, orb_sig, cfg, delays=(0, 1, 3))

    # Six OOS subperiods feed a small CSCV diagnostic. Three candidates is the
    # bare minimum; report rather than over-interpret it.
    matrix = []
    nrows = len(test_b["SPY"])
    for name, sig in sigs.items():
        scores = []
        for loc in np.array_split(np.arange(nrows), 6):
            seg = {s: b.iloc[loc] for s, b in test_b.items()}
            scores.append(evaluate(name, seg, sig, cfg)["sharpe"] or 0.0)
        matrix.append(scores)
    pbo_obj = cscv_pbo(pd.DataFrame(matrix).fillna(0), n_partitions=6,
                       max_trials=500, seed=42)
    pbo = {"pbo": pbo_obj.pbo, "logit": pbo_obj.logit,
           "n_configs": pbo_obj.n_configs, "n_partitions": pbo_obj.n_partitions}

    # Replication across independent synthetic worlds for the locked rule set.
    replication = []
    orb_replication = []
    for seed in (101, 202, 303, 404, 505):
        rb, _ = generate_intraday_universe(symbols, days=120, seed=seed,
                                            start="2022-01-03")
        rs = InstitutionalIntradayStrategy().generate_universe(rb)
        replication.append(evaluate(f"seed_{seed}", rb, rs, cfg))
        orb_replication.append(evaluate(f"orb_seed_{seed}", rb,
                                        filtered(rs, {"opening_breakout"}), cfg))
    replication = pd.DataFrame(replication)
    orb_replication = pd.DataFrame(orb_replication)

    champ_oos = test[test.name == champion].iloc[0]
    passes_numeric = (champ_oos.trades >= 30 and champ_oos.sharpe > .5
                      and champ_oos.profit_factor > 1.1 and champ_oos.max_dd > -.06
                      and costs.loc[costs.shock == "costs x2", "total_return"].iloc[0] > 0
                      and slips.loc[slips.shock == "slippage x5", "total_return"].iloc[0] > 0)
    decision = "NOT APPROVED — synthetic data cannot establish market edge"
    if not passes_numeric:
        decision += "; numeric research gates also failed"

    report = f"""# Institutional-Inspired Intraday Strategy Research Report

**Date:** 2026-08-14  
**Data:** SYNTHETIC session-aware 5-minute bars, {args.days} business days × 3 symbols.  
**Boundary:** train < {train_end.date()}, validation < {val_end.date()}, locked OOS thereafter.  
**Decision:** **{decision}.**

This is not Citadel's strategy. Exact hedge-fund algorithms, data, execution, and
portfolio construction are proprietary and unknown. Public principles were
translated into falsifiable components.

## Validation leaderboard (used once for champion selection)

{fmt_table(val)}

Selected champion: **{champion}**

## Locked out-of-sample results

{fmt_table(test)}

## Setup ablation on locked OOS

{fmt_table(ablation)}

## Cost stress

{costs.to_markdown(index=False)}

## Slippage stress

{slips.to_markdown(index=False)}

## Latency stress

{latency.to_markdown(index=False)}

## Independent synthetic-world replication — full rule router

{fmt_table(replication)}

## Post-OOS opening-breakout challenger

This component was identified after inspecting the ablation table. It is therefore
selection-contaminated and cannot replace the validation-selected champion. Fresh
synthetic seeds are only a robustness screen for the next research cycle.

### Challenger uncertainty

```json
{json.dumps(orb_uncertainty, indent=2, default=float)}
```

### Challenger stress: costs

{orb_costs.to_markdown(index=False)}

### Challenger stress: slippage

{orb_slips.to_markdown(index=False)}

### Challenger stress: latency

{orb_latency.to_markdown(index=False)}

### Challenger independent synthetic worlds

{fmt_table(orb_replication)}

## ML training diagnostics

```json
{json.dumps(diagnostics, indent=2, default=str)}
```

## Multiple-selection diagnostic

```json
{json.dumps(pbo, indent=2, default=float)}
```

## Hard behaviors

- 0.25% maximum research risk per trade; no leverage.
- 0.75% daily and 2% weekly loss stops; 6% portfolio drawdown kill.
- At most 3 positions, 6 trades/day, and 1% of bar volume.
- Structural stops and predeclared targets; stop-first same-bar assumption.
- Mandatory 15:55 liquidation; no overnight positions.
- ML can reject trades only. It cannot bypass or loosen Risk Engine limits.
- No martingale, averaging down, recovery grid, or PnL-driven sizing.

## Evidence boundary

Synthetic success validates software behavior only. Real point-in-time intraday
bars, spreads, corporate actions, market calendar, borrow, halts, and a pristine
holdout are required before paper promotion. “Bulletproof” is impossible; the
correct objective is bounded loss, graceful degradation, and fail-closed behavior.
"""
    ART.mkdir(exist_ok=True)
    (ART/"institutional_intraday_report.md").write_text(report)
    val.to_csv(ART/"institutional_intraday_validation.csv", index=False)
    test.to_csv(ART/"institutional_intraday_oos.csv", index=False)
    payload = {"champion": champion, "decision": decision, "diagnostics": diagnostics,
               "pbo": pbo, "opening_range_uncertainty": orb_uncertainty}
    (ART/"institutional_intraday_summary.json").write_text(json.dumps(payload, indent=2, default=float))
    print(report)


if __name__ == "__main__":
    main()
