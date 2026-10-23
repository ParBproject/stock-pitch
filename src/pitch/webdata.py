"""Export the data the interactive web deck needs (web/public/data/pitch.json). Every value is computed
from results/summary.json or the frozen snapshots by the same functions the notebooks use."""

from __future__ import annotations

import json

import numpy as np

from pitch import analysis as a
from pitch.data import ROOT
from pitch.universe import ACTIVE, BENCHMARK, PITCHES

GROWTH_GRID = [round(x, 4) for x in np.arange(-0.05, 0.3001, 0.025)]
WACC_GRID = [round(x, 4) for x in np.arange(0.06, 0.1201, 0.005)]


def _series(s, nd=4):
    return [[d.strftime("%Y-%m-%d"), None if not np.isfinite(v) else round(float(v), nd)] for d, v in s.items()]


def _weekly(df):
    """Last trading day of each Friday-ending week, keeping the real date (never later than the data)."""
    return df.groupby(df.index.to_period("W-FRI")).tail(1)


def build() -> dict:
    a.set_pitch(ACTIVE)
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    px = a.load_prices()
    weekly = _weekly(px).loc[:, [ACTIVE, *PITCHES[ACTIVE]["peers"], BENCHMARK]]
    _, rolling = a.factor_model()
    _, curves = a.backtest()
    cw = _weekly(curves)
    fcf = a.fcf_history()
    grid = [[g, w, round(float(a.dcf_value(g, w)), 2)] for g in GROWTH_GRID for w in WACC_GRID]
    return {
        "ticker": ACTIVE,
        "as_of": summary["as_of"],
        "summary": summary,
        "prices_weekly": {t: _series(weekly[t], 2) for t in weekly.columns},
        "rolling_betas": {f: _series(rolling[f], 3) for f in rolling.columns},
        "backtest_weekly": {c: _series(cw[c], 4) for c in cw.columns},
        "fcf_history": _series(fcf, 0),
        "dcf_grid": {"growth": GROWTH_GRID, "wacc": WACC_GRID, "values": grid},
        "notes": {
            "prices": "Yahoo Finance adjusted close, last trading day of each week (real dates)",
            "dcf_grid": "same two-stage DCF as notebook 04; only stage-1 growth and WACC vary",
        },
    }


def write() -> None:
    out = ROOT / "web" / "public" / "data" / "pitch.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), separators=(",", ":")) + "\n")
