# Final adversarial review — 100 questions

These questions are answered by a gate, experiment, or an explicit **UNKNOWN**;
they are not rhetorical reassurance.

## Edge and causality (1–10)
1. Is continuation causal, or merely a label attached after a rise?
2. Does the trigger predict future return beyond the trend context alone?
3. Is the apparent edge only the synthetic generator's planted trend?
4. Does the setup outperform random entries with identical holding and risk?
5. Does it outperform a slower, simpler trend baseline?
6. Is volume incremental after volatility and time of day are controlled?
7. Is the pullback definition independent of the trigger definition?
8. Are failed breakouts reversals, or delayed trend entries in disguise?
9. Does expected R correlate monotonically with realized R?
10. What observation would falsify the mechanism rather than one parameter?

## Data and leakage (11–20)
11. Is every rolling level shifted before it is breached?
12. Does any centered window or revised field enter a decision?
13. Are timestamps event time, receive time, or bar close time?
14. Does next-open execution remain valid on exchange-session data?
15. Are delisted symbols and historical constituents retained?
16. Are splits, dividends, rolls, halts, and bad ticks handled causally?
17. Does session VWAP reset at the correct exchange session?
18. Are news timestamps available as first-publication rather than edited time?
19. Does truncating data at any decision leave that decision unchanged?
20. Has the final holdout remained unseen after strategy selection?

## Selection and statistics (21–30)
21. How many strategies, filters, exits, and variants were tried in total?
22. Is the reported p-value adjusted for that entire search universe?
23. Does CSCV/PBO remain stable under different partitions?
24. Are OOS trades numerous enough for a Sharpe estimate to mean anything?
25. Are confidence intervals wider than the claimed edge?
26. Is one symbol, month, or year responsible for most profit?
27. Does block bootstrap preserve serial dependence and volatility clusters?
28. Does a parameter plateau exist, or only one winning point?
29. Would a deflated Sharpe reject the candidate?
30. Was the OOS period reused and thereby converted into training data?

## Simplicity and redundancy (31–40)
31. Can volume be removed without material OOS degradation?
32. Can the volatility gate be removed without material degradation?
33. Can trend context be simplified to one lagged return sign?
34. Are EMA fast and slow two parameters expressing one concept?
35. Does each rule remove bad trades without removing more expectancy?
36. Are two strategies merely correlated versions of the same exposure?
37. Does a model add information unavailable in the deterministic setup?
38. Is the strategy explainable from raw prices without indicator mythology?
39. Can an auditor reproduce every decision from one bar snapshot?
40. Is complexity being retained because it sounds professional?

## Stops, targets, and management (41–50)
41. Is the structural stop outside ordinary noise at entry?
42. Is the stop still valid after a gap at the next open?
43. Are targets reachable before the time stop in most regimes?
44. Does 2R beat 1R, 1.5R, 2.5R, 3R, and 4R OOS?
45. Does target optimization merely trade win rate for payoff cosmetically?
46. Do partial exits improve geometric return after extra costs?
47. Does trailing destroy positive skew?
48. Are MFE and MAE distributions stable across periods?
49. Is time exit evidence-based or an arbitrary maximum?
50. Does same-bar stop-first handling materially change the verdict?

## Execution (51–60)
51. Does the edge survive 2×, 3×, and 5× costs?
52. Does it survive 2×, 5×, and 10× slippage?
53. What happens when the spread widens exactly when signals fire?
54. Is displayed volume actually available liquidity?
55. Does the order exceed a safe share of bar volume?
56. Are short borrow, locate failures, and hard-to-borrow fees modeled?
57. Does one-bar latency reverse the result?
58. What happens under partial fills and queue loss?
59. Can a target fill be assumed when only the bar high touches it?
60. Are broker rejects and duplicate orders fail-closed?

## Regimes and adaptation (61–70)
61. Which objective regime creates the losses?
62. Can that regime be identified before, not after, the loss?
63. Does regime classification add edge or just reduce exposure?
64. What happens at abrupt trend-to-range transitions?
65. Does high-volatility gating remove crisis opportunities?
66. Does low volatility make costs dominate gross expectancy?
67. Are strategy weights updated from enough independent trades?
68. Does adaptation chase noise after a losing streak?
69. Is the champion frozen while challengers are evaluated?
70. Can the system remain NO_TRADE indefinitely without weakening gates?

## Risk and survival (71–80)
71. Is 0.5% risk still too large given edge uncertainty?
72. What is the loss if all positions gap through stops together?
73. Are correlations understated during stress?
74. Does confidence sizing amplify calibration error?
75. Could removing confidence scaling improve robustness?
76. Is drawdown scaling procyclical near recovery?
77. What sequence trips the daily, weekly, and portfolio limits?
78. Does a kill switch halt safely and require explicit reset?
79. Can any model or execution path bypass the Risk Engine?
80. Does the strategy survive twenty losses without changing its rules?

## Comparisons and interpretation (81–90)
81. Does it beat cash after costs on a risk-adjusted basis?
82. Does it beat buy-and-hold where that benchmark is appropriate?
83. Does it beat random entries under identical risk constraints?
84. Does it beat the existing slow-trend champion?
85. Is lower drawdown merely lower market exposure?
86. Is win rate being highlighted while expectancy is negative?
87. Are dollar returns masking leverage or copied accounts?
88. Is synthetic performance being mistaken for market evidence?
89. Are influencer claims being treated as hypotheses rather than facts?
90. Are losing strategies and abandoned tests still visible?

## Governance and final decision (91–100)
91. What exact gate promotes a challenger to paper test?
92. What exact evidence demotes the champion?
93. Is the experiment registry append-only and complete?
94. Is the strategy version and parameter hash recorded?
95. Can production run a model not marked approved?
96. Does data drift force NO_TRADE rather than silent continuation?
97. Are live trading, age, identity, and legal requirements fail-closed?
98. What is the single largest unresolved weakness?
99. If half the rules are deleted, is performance similar or better?
100. Is “no sufficiently robust edge found” the evidence-supported answer?

## Current answers that matter most

- 3 and 88: **YES, synthetic-only contamination is the dominant limitation.**
- 24: **NO, quick-run OOS samples are too small.**
- 51–52: stress machinery exists; no v2 candidate currently passes promotion.
- 79: **NO bypass path is intended or tested; Risk Engine remains authoritative.**
- 98: lack of real point-in-time market data with a pristine holdout.
- 100: **YES. Current verdict: no candidate approved.**
