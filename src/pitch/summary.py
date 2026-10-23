"""Build results/summary.json. M2 fills the data-coverage block; later milestones fill the rest."""

from __future__ import annotations

import json

from pitch.config import AS_OF
from pitch.data import ROOT, load_factors, load_fundamentals, load_manifest, load_prices
from pitch.universe import BENCHMARK, CONCEPTS, PEERS, TICKER


def _d(ts) -> str:
    return ts.strftime("%Y-%m-%d")


def data_coverage() -> dict:
    prices = load_prices()
    factors = load_factors()
    fund = load_fundamentals()
    px = {}
    for t in prices.columns:
        s = prices[t].dropna()
        px[t] = {"first": _d(s.index[0]), "last": _d(s.index[-1]), "n_days": int(s.size)}
    fy = {}
    for t, g in fund.groupby("ticker"):
        fy[t] = {
            m: {"n_years": int(len(x)), "first": _d(x.period_end.min()), "last": _d(x.period_end.max())}
            for m, x in g.groupby("metric")
        }
        fy[t]["missing_metrics"] = sorted(set(CONCEPTS) - set(fy[t]))
    return {
        "prices": px,
        "factors": {"first": _d(factors.index[0]), "last": _d(factors.index[-1]), "n_days": int(len(factors))},
        "fundamentals_fy": fy,
    }


def build_summary() -> dict:
    screen = json.loads((ROOT / "results" / "screen.json").read_text())
    return {
        "ticker": TICKER,
        "as_of": AS_OF,
        "peers": PEERS,
        "benchmark": BENCHMARK,
        "screen": {"chosen": screen["chosen"], "total": next(c["total"] for c in screen["candidates"] if c["ticker"] == TICKER)},
        "data": {"manifest_fetched_at_utc": load_manifest()["fetched_at_utc"], **data_coverage()},
        # Filled by M3 notebooks. null means "not computed yet", never a placeholder number.
        "factor_model": None,
        "comps": None,
        "valuation": None,
        "risk": None,
        "backtest": None,
    }
