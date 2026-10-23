"""Build results/summary.json (active pitch + comparison) and per-pitch summaries for the others."""

from __future__ import annotations

import json

from pitch.config import AS_OF
from pitch.data import ROOT, load_factors, load_fundamentals, load_manifest, load_prices
from pitch.universe import ACTIVE, BENCHMARK, CONCEPTS, PITCHES

ARCHIVE_REASON = {
    "V": (
        "Dropped after M3: the base DCF gave 199.15 vs a 359.33 price (-44.6%), even the bull case was -25.5%, "
        "and the price implied 28.4% stage-1 FCF growth vs a 12.9% historical median. Frank re-picked from the shortlist "
        "with the same methods and assumptions (no tuning)."
    )
}
COMPARED = ["UNH", "COST"]  # UNH's bear case is below the price, so COST (next on the shortlist) is run the same way
PITCH_FILES = {"V": "results/archive/V_summary.json", "COST": "results/compare/COST_summary.json"}


def _d(ts) -> str:
    return ts.strftime("%Y-%m-%d")


def data_coverage(raw) -> dict:
    prices = load_prices(raw)
    factors = load_factors(raw)
    fund = load_fundamentals(raw)
    px = {}
    for t in prices.columns:
        s = prices[t].dropna()
        px[t] = {"first": _d(s.index[0]), "last": _d(s.index[-1]), "n_days": int(s.size)}
    fy = {}
    for t, g in fund.groupby("ticker"):
        fy[t] = {m: {"n_years": int(len(x)), "first": _d(x.period_end.min()), "last": _d(x.period_end.max())} for m, x in g.groupby("metric")}
        fy[t]["missing_metrics"] = sorted(set(CONCEPTS) - set(fy[t]))
    return {
        "prices": px,
        "factors": {"first": _d(factors.index[0]), "last": _d(factors.index[-1]), "n_days": int(len(factors))},
        "fundamentals_fy": fy,
    }


def build_pitch(ticker: str) -> dict:
    from pitch import analysis as a

    a.set_pitch(ticker)
    raw = PITCHES[ticker]["raw"]
    screen = json.loads((ROOT / "results" / "screen.json").read_text())
    out = {
        "ticker": ticker,
        "as_of": AS_OF,
        "peers": PITCHES[ticker]["peers"],
        "benchmark": BENCHMARK,
        "screen": {"chosen": screen["chosen"], "total": next(c["total"] for c in screen["candidates"] if c["ticker"] == ticker)},
        "data": {"manifest_fetched_at_utc": load_manifest(raw)["fetched_at_utc"], **data_coverage(raw)},
        **analysis_block(),
    }
    sc = out["scenarios"]
    out["verdict"] = {
        "base_upside_positive": out["valuation"]["upside"] > 0,
        "all_scenarios_positive": all(sc[k]["upside"] > 0 for k in ("bear", "base", "bull")),
        "supports_long": out["valuation"]["upside"] > 0,
        "rule": "supports a long thesis if the base-case DCF value is above the as-of price; the bear case is reported alongside",
    }
    return out


def comparison(pitches: dict) -> dict:
    rows = {}
    for t, p in pitches.items():
        v, sc, bt = p["valuation"], p["scenarios"], p["backtest"]
        rows[t] = {
            "price": v["price"],
            "implied_value": v["implied_value"],
            "upside": v["upside"],
            "bear": sc["bear"]["target"],
            "base": sc["base"]["target"],
            "bull": sc["bull"]["target"],
            "wacc": v["wacc_inputs"]["wacc"]["value"],
            "reverse_dcf_stage1_growth": v["reverse_dcf_stage1_growth"],
            "sharpe_buy_hold": bt["buy_hold"]["sharpe_rf0"],
            "sharpe_strategy": bt["strategy"]["sharpe_rf0"],
            "supports_long": p["verdict"]["supports_long"],
        }
    return rows


def build_all() -> dict[str, dict]:
    """Return {relative path: content} for every summary file."""
    pitches = {t: build_pitch(t) for t in ["V", *COMPARED]}
    active = dict(pitches[ACTIVE])
    active["comparison"] = comparison({t: pitches[t] for t in COMPARED})
    active["archived"] = {t: {"reason": r, "summary_file": PITCH_FILES[t]} for t, r in ARCHIVE_REASON.items()}
    active["compared_with"] = {t: PITCH_FILES[t] for t in COMPARED if t != ACTIVE}
    files = {"results/summary.json": active}
    for t, path in PITCH_FILES.items():
        files[path] = pitches[t]
    return files


def analysis_block() -> dict:
    from pitch import analysis as a

    fm, _ = a.factor_model()
    c = a.comps()
    comps = {
        t: {
            "fiscal_year_end": row.fiscal_year_end,
            "market_cap": a.r(row.market_cap, 0),
            "ev_ebitda": a.r(row.ev_ebitda, 2),
            "pe": a.r(row.pe, 2),
            "fcf_yield": a.r(row.fcf_yield),
            "gaps": row.gaps or None,
        }
        for t, row in c.iterrows()
    }
    bt, _ = a.backtest()
    return {
        "assumptions": a.ASSUMPTIONS,
        "factor_model": fm,
        "comps": comps,
        "valuation": a.dcf(),
        "risk": a.risk(),
        "backtest": bt,
        "scenarios": a.scenarios(),
    }
