"""Serein — an adaptive, autonomous trading-research framework.

Design doctrine (from the project mandate):
  * Preserving capital comes before maximizing returns.
  * Never fabricate performance, tests, or research.
  * The system must be able to conclude "there is no attractive trade".
  * Risk Engine is the ultimate authority; no model can override it.
  * Paper-trading-only until every validation gate has been passed
    and (where applicable) legal/brokerage eligibility is confirmed.

This package is a RESEARCH FRAMEWORK. It contains no live-broker adapter
and must remain PAPER_TRADING_ONLY.
"""

__version__ = "0.1.0"

PAPER_TRADING_ONLY = True
"""Hard system-wide flag. No code path may ever transmit a real order."""

MODE = "RESEARCH"
