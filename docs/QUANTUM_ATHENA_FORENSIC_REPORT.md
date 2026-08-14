# Quantum Athena forensic review and replication boundary

**Reviewed:** 2026-08-14  
**Primary account:** Myfxbook 12074640  
**Decision:** The monitored trades are probably genuine trades on a real, very
small account. **That does not establish a safe, scalable, or durable edge.** I
found insufficient evidence to call it a scam, but strong evidence that the
headline return materially understates the economic and tail risks.

## 1. Verdict in plain language

| Question | Finding | Confidence |
|---|---|---|
| Does the account exist and place real trades? | Probably yes. Myfxbook labels it Real; MQL5 and SignalStart show matching deposits, withdrawals, trade counts and account economics. | High, but not an independent broker statement |
| Are the published profits fabricated? | No evidence of fabrication. Current MQL5 monitoring shows a live balance/equity and new trades. | Medium-high |
| Is +1,100% to +1,500% a fair description of investor experience? | No. It began with $50, later received $150, uses 1:500 leverage, and experienced 36.78% equity DD. Percentage growth on this scale is not evidence of capacity. | High |
| Is it a scam? | **Not proven.** “Scam” would require evidence of deception or fraud that the public record does not establish. | High |
| Is it low-risk or suitable to copy blindly? | No. It is an explicitly described Gold trend-following grid with basket risk, no visible SL/TP in the sampled rows, high deposit load and copy-execution warnings. | High |
| Can the exact algorithm be replicated? | No. Six proprietary entry strategies and virtual/basket risk logic are undisclosed; closed trades alone identify behavior, not exact decision boundaries. | High |

The correct classification is:

> **Likely authentic high-risk live performance; unproven durability and poor
> evidence of scalability. Not enough evidence to allege fraud, and nowhere near
> enough evidence to approve it as safe.**

## 2. Cross-platform facts

### Myfxbook snapshot (stale after 17 Jun 2026)

- Real USD account, IC Trading, MetaTrader 5, **1:500 leverage**.
- Gain +1,139.19%; absolute gain +789.88%.
- Daily 0.69%; monthly 27.97%; displayed drawdown 23.50%.
- Deposits $200; withdrawals $494.90; balance/equity $1,284.85.
- 659 trades; 625 longs and 34 shorts; 75%/70% wins.
- Average win $4.95; average loss −$5.24; PF 2.83; expectancy $2.40.
- Average duration 48 minutes; Sharpe 0.33.
- Closed and open trades are private on this page.

### Current MQL5 signal snapshot (14 Aug 2026)

- Balance and equity $1,666.70; profit $1,961.60.
- Initial deposit $50 plus one $150 deposit; withdrawals $494.90.
- 782 deals; 76.21% winners; PF 2.95; expected payoff $2.51.
- Average win $4.98 versus average loss −$5.41: payoff ratio **0.92**.
- 744/782 trades are long (**95.14%**).
- Average holding 43 minutes; 29 trades/week; 100% algorithmic.
- Maximum deposit load **41.14%**.
- Balance DD 10.62%, but **equity DD 36.78%** ($306.73).
- MQL5 has repeatedly warned that frequent deals may hurt copying.
- Advertised signal price: $999/month; zero subscribers shown.

### SignalStart snapshot

- Same account economics, now 783 trades and 15.52 lots.
- Advertised price $99/month.
- Vendor description explicitly calls it an **“elite trend-following grid
  system”** with six built-in strategies and XAUUSD specialization.
- Public table exposes the latest ten rows but not all 786 without interactive
  export.

The close agreement across three monitors is why I consider the account activity
probably authentic. Verification proves much less than robustness: it cannot
make a $50 experiment representative of a large account, expose undisclosed
virtual risk rules, eliminate cherry-picked account selection, or guarantee the
same fills for followers.

## 3. What the trades reveal

The ten publicly visible SignalStart rows were captured in
`research/quantum_athena_public_sample.csv` and analyzed by
`serein/research/trade_forensics.py`.

Observed in that **partial sample only**:

- 10/10 buys.
- Same 0.03 lot size throughout; **no lot-multiplying martingale detected**.
- Four simultaneous positions at peak.
- 60% of rows share a close timestamp with another row.
- A four-position basket on 11 Aug opened at different prices and closed within
  the same minute/price region.
- All visible SL and TP fields are blank.
- Median holding time two minutes in this recent sample; one trade lasted 17s.

This is strong observable evidence of grid/basket execution and agrees with the
vendor's own description. It is **not** evidence of classic martingale lot
multiplication: the visible lots are fixed. A fixed-lot grid can still accumulate
large correlated exposure and floating losses.

Blank SL/TP fields do **not** prove there is no protection—the EA may use virtual,
basket, equity, or hidden exits. They do prove that a copier cannot audit a hard
broker-side stop from these rows.

## 4. Return mechanism

The published expectancy is driven by frequency and hit rate, not asymmetric
reward:

```text
p(win)       = 0.7621
average win  = $4.98
average loss = $5.41
trade EV     ≈ 0.7621×4.98 − 0.2379×5.41 = $2.51
payoff ratio = 4.98 / 5.41 = 0.92
```

The strategy appears to combine:

1. a very strong long bias in Gold;
2. selective short-duration entries;
3. multiple fixed-size entries at different prices;
4. basket exits after price moves/reverts favorably;
5. high leverage and a tiny starting account;
6. withdrawal of profits after favorable runs.

At 29 trades/week, published trade EV implies roughly $72.79/week at the recent
lot/equity scale before subscription and follower-specific slippage. That is
about 4.4% of the current $1,666 balance, broadly consistent with its aggressive
headline growth. It should not be projected forward unchanged.

## 5. Material red flags and caveats

### A. Tiny capital base

The run began with **$50**, not institutional capital. Total deposits were $200.
Minimum lot size, broker credit, leverage and fixed costs make percentage results
on tiny accounts highly nonlinear. A 1,500% return produced under $2,000 of
trading profit, not millions of scalable P&L.

### B. Equity drawdown is much larger than balance drawdown

MQL5 reports 10.62% balance DD but 36.78% equity DD. Grid systems often realize
many small winners while adverse baskets remain floating. Balance-only curves
can therefore look substantially smoother than true mark-to-market equity.

### C. 1:500 leverage and 41% deposit load

This is an aggressive capital structure. Leverage does not itself prove a scam,
but it increases sensitivity to Gold gaps, spread spikes, margin changes and
one-directional runs.

### D. Concentration

95.14% of MQL5 trades are long XAUUSD. The sample largely overlaps a strong Gold
regime. The account has not established behavior across a prolonged Gold bear
market or a violent non-reverting selloff.

### E. Basket correlation

“Maximum five consecutive losses” treats tickets separately. Four entries in one
basket are one correlated thesis, not four independent bets. Ticket-level win
rate overstates diversification.

### F. Copying economics

- Some public trades last seconds or minutes.
- MQL5 repeatedly raised “too frequent deals may negatively impact copying.”
- Reported cross-broker slippage varies.
- SignalStart costs $99/month; MQL5 shows $999/month. On a $1,666 account those
  are approximately 5.9% and 60% of balance **every month**, before spread,
  commission and slippage.

### G. Product lifecycle

The original MQL5 product is no longer sold, while Quantum Athena X is promoted
as a successor. The public page does not state why the original was withdrawn.
This is a due-diligence question, not proof of wrongdoing.

### H. Selection/survivorship

The same profile operates several systems. Displayed drawdowns include Quantum
Bitcoin 68.02%, Quantum King 43.73%, and Quantum Queen 38.08%. Selecting the best
surviving account after launching multiple EAs inflates perceived reliability.

### I. Third-party allegations

Some independent/anonymous pages allege grid blow-ups, hidden unfavorable
backtest periods, customer margin calls, or deposits that alter displayed gain.
Other commercial review pages strongly endorse the product. Neither side is an
audited source. These claims are logged as **unverified** and are not used to
label the developer fraudulent.

## 6. What would resolve the uncertainty

Before treating this as durable, require all of the following:

1. Both Myfxbook verification badges visibly green and a current live update.
2. Complete CSV of all closed trades, including lot, entry, exit, SL/TP, swap,
   commission and ticket comments.
3. Minute-by-minute equity and margin history—not balance only.
4. All deposits/withdrawals with timestamps.
5. Basket-level grouping and maximum concurrent exposure.
6. Written definitions of emergency stop, maximum basket size, spacing, lot
   progression, news filter and equity stop.
7. Broker statement or read-only investor access matched to the monitors.
8. All discontinued/failed accounts using the same EA and settings.
9. Independent backtest on tick data from 2015–2026, with 2018–2021 isolated.
10. Forward test on a normal-sized, low-leverage account for at least 12–24
    additional months.
11. Follower fill study after the subscription fee and real copy slippage.

Without that, the exact tail-loss distribution is unknowable.

## 7. Replication attempt

### What cannot honestly be replicated

The six entry models, grid spacing, basket objective, virtual exits, news logic,
risk level and adaptation rules are proprietary/unknown. Inferring exact rules
from a balance curve would be reverse-engineered storytelling.

### What was implemented

`QuantumAthenaSafeProxy` in `serein/strategies/athena_observed.py` captures the
smallest observable hypothesis:

```text
Instrument: XAUUSD
Bias: long by default
Context: EMA20 > EMA100 and EMA100 rising
Setup: prior close dips 0.45 ATR below EMA20
Trigger: current close exceeds prior high
Entry: next bar open
Stop: five-bar swing low minus 0.15 ATR
Target: 1.0R
Position policy: one position, never add to a loser
Risk: normal Serein hard limits; no leverage escalation
No trade: extreme-volatility top 5%, invalid stop, risk veto
```

This is deliberately **not a grid**. It refuses to reproduce the public
account's dangerous combination of 1:500 leverage, accumulated basket exposure
and non-auditable stops.

### Smoke-test result

On 30,000 synthetic five-minute bars—engineering validation only—the safe proxy
produced:

- 53 trades;
- 52.8% win rate;
- −1.0% total return;
- Sharpe −0.72;
- max DD −2.0%;
- PF 0.78;
- expectancy −0.10R;
- approximately $1,502 in modeled costs.

It failed. This neither proves nor disproves Quantum Athena because the data are
synthetic and the proprietary grid logic is absent. It does show that the simple
“buy a trend dip” explanation does not automatically reproduce the headline.
The basket/grid behavior is likely central to the observed win rate—and also to
its tail risk.

## 8. Final decision

- **Fraud/scam determination:** not established.
- **Trade authenticity:** probably real.
- **Marketing-risk concern:** high.
- **Tail-risk concern:** high.
- **Scalability:** unproven.
- **Exact replication:** impossible from public information.
- **Safe proxy:** implemented and rejected in its first synthetic smoke test.
- **Serein promotion:** rejected; research/paper only.

I would not copy or purchase it based on the headline curve. The evidence needed
next is the complete trade/equity export, especially the worst basket—not another
screenshot or percentage-gain chart.

## Sources

- Myfxbook account: https://www.myfxbook.com/members/bogdanion/quantum-athena/12074640
- Current MQL5 signal: https://www.mql5.com/en/signals/2348372
- SignalStart history and description: https://www.signalstart.com/analysis/quantum-athena/289445
- Discontinued original MQL5 listing: https://www.mql5.com/en/market/product/173058
- Myfxbook verification context: https://www.myfxbook.com/community/suggestion-box/fatal-flaw-track-record-verification/33132,1
- Critical third-party backtest (unverified): https://fxprosystems.com/quantum-athena-mt5-ea/
- Critical third-party review (unverified): https://forexrobotlab.com/quantum-athena-mt5-ea-review/
- Favorable commercial review (conflicted/unverified): https://cheaperforex.com/quantum-athena-ea-mt5-download/
