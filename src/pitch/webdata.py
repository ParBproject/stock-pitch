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


def scenario_panel(summary: dict) -> dict:
    """Precomputed DCF surface for the scenario panel. Every value comes from analysis.dcf_breakdown; the
    browser only looks values up. Exact defaults (base growth, both beta-driven WACCs, scenario growths) are
    inserted into the grids so the panel's defaults reproduce summary.json to the cent."""
    v, sc, bs = summary["valuation"], summary["scenarios"], summary["beta_sensitivity"]
    sp = a.scenario_params()  # exact values; summary.json stores them rounded
    g0, w5 = sp["base"]
    _, wf = a.full_sample_beta_wacc()
    growth = sorted({round(x, 4) for x in np.arange(-0.05, 0.3001, 0.005)} | {sp[k][0] for k in sp})
    wacc = sorted({round(x, 4) for x in np.arange(0.06, 0.1401, 0.0025)} | {w5, wf} | {sp[k][1] for k in sp})
    values = [[round(a.dcf_breakdown(g, w)["per_share"], 2) for w in wacc] for g in growth]
    paths = [[round(x / 1e9, 3) for x in a.dcf_breakdown(g, w5)["fcf_path"]] for g in growth]
    base_year = int(a.fcf_history().index[-1].year)
    return {
        "growth": growth,
        "wacc": wacc,
        "values": values,
        "fcf_paths_bn": paths,
        "fcf0_bn": round(a.dcf_inputs()["fcf0"] / 1e9, 3),
        "years": [base_year + i for i in range(1, a.ASSUMPTIONS["fade_years"]["value"] + 1)],
        "price": v["price"],
        "defaults": {
            "growth": g0,
            "beta": {
                "5y": {"beta": v["wacc_inputs"]["beta"]["value"], "wacc": w5, "label": "5-year beta"},
                "full": {"beta": bs["beta"], "wacc": wf, "label": "Full-sample beta (2014 on)"},
            },
        },
        "scenarios": {k: {"growth": sp[k][0], "wacc": sp[k][1], "target": sc[k]["target"]} for k in ("bear", "base", "bull")},
        "terminal_growth": a.ASSUMPTIONS["terminal_growth"]["value"],
    }


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
        "scenario_panel": scenario_panel(summary),
        "notes": {
            "prices": "Yahoo Finance adjusted close, last trading day of each week (real dates)",
            "dcf_grid": "same two-stage DCF as notebook 04; only stage-1 growth and WACC vary",
        },
    }


def write() -> None:
    out = ROOT / "web" / "public" / "data" / "pitch.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), separators=(",", ":")) + "\n")
