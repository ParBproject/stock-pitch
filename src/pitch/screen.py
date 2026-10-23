"""Offline stock screen over the frozen snapshots in data/snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pitch.config import AS_OF, CANDIDATES, EXCLUDED, MIN_PEERS, MIN_YEARS, WEIGHTS

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "data" / "snapshots"
PEER_CAP = 8  # peer score saturates at 8 verified peers


def load_snapshots(snap: Path = SNAP) -> tuple[pd.DataFrame, dict, dict]:
    prices = pd.read_csv(snap / "prices.csv", index_col="date", parse_dates=True)
    meta = json.loads((snap / "meta.json").read_text())
    sec = json.loads((snap / "sec_fy_coverage.json").read_text())
    return prices, meta, sec


def history_years(series: pd.Series) -> float:
    s = series.dropna()
    if s.empty:
        return 0.0
    return round((s.index[-1] - s.index[0]).days / 365.25, 2)


def score_candidate(t: str, prices: pd.DataFrame, meta: dict, sec: dict, max_cap: float) -> dict:
    industry = meta[t]["industry"]
    peers = [p for p in CANDIDATES[t] if meta[p]["industry"] == industry]
    dropped = [p for p in CANDIDATES[t] if p not in peers]
    peer_years = {p: history_years(prices[p]) for p in peers}
    years = history_years(prices[t])
    sec_years = {k: len(v) for k, v in sec[t].items() if k != "cik"}

    coverage_checks = [years >= MIN_YEARS] + [n >= MIN_YEARS for n in sec_years.values()]
    coverage = sum(coverage_checks) / len(coverage_checks)
    peer_score = min(len(peers), PEER_CAP) / PEER_CAP
    testability = sum(y >= MIN_YEARS for y in peer_years.values()) / len(peers) if peers else 0.0
    recognisability = meta[t]["market_cap"] / max_cap
    parts = {
        "coverage": round(coverage, 4),
        "peers": round(peer_score, 4),
        "testability": round(testability, 4),
        "recognisability": round(recognisability, 4),
    }
    total = round(sum(WEIGHTS[k] * v for k, v in parts.items()), 4)
    eligible = years >= MIN_YEARS and len(peers) >= MIN_PEERS
    return {
        "ticker": t,
        "name": meta[t]["name"],
        "industry": industry,
        "price_history_years": years,
        "sec_fy_years": sec_years,
        "verified_peers": peers,
        "peers_dropped_industry_mismatch": dropped,
        "peer_history_years": peer_years,
        "market_cap_usd": meta[t]["market_cap"],
        "scores": parts,
        "total": total,
        "eligible": eligible,
        "ineligible_reason": None if eligible else f"only {len(peers)} same-industry peers (< {MIN_PEERS})",
    }


def run_screen(snap: Path = SNAP) -> dict:
    prices, meta, sec = load_snapshots(snap)
    assert not set(CANDIDATES) & set(EXCLUDED)
    max_cap = max(meta[t]["market_cap"] for t in CANDIDATES)
    rows = [score_candidate(t, prices, meta, sec, max_cap) for t in CANDIDATES]
    rows.sort(key=lambda r: (r["eligible"], r["total"]), reverse=True)
    shortlist = [r["ticker"] for r in rows if r["eligible"]]
    return {
        "as_of": AS_OF,
        "excluded": EXCLUDED,
        "method": {
            "weights": WEIGHTS,
            "gates": f">= {MIN_YEARS}y price history and >= {MIN_PEERS} peers sharing the Yahoo Finance industry label",
            "coverage": "share of checks met: price history >= 10y; SEC 10-K FY revenue, net income, diluted EPS >= 10 years",
            "peers": f"verified same-industry peers / {PEER_CAP} (capped at 1)",
            "testability": "share of verified peers with >= 10y price history (needed for comps, factor and backtest work)",
            "recognisability": "market cap / largest market cap among candidates (proxy; market cap as of snapshot fetch)",
        },
        "candidates": rows,
        "shortlist": shortlist,
        "chosen": shortlist[0],
    }
