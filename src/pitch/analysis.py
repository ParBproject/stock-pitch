"""M3 analysis: factor model, comps, DCF and reverse DCF, risk, walk-forward backtest, scenarios.

Every input comes from the frozen snapshots in data/raw. The few modelling choices that are not
data (terminal growth, scenario WACC shift, trading cost, signal grid) are named in ASSUMPTIONS,
so they are visible in results/summary.json and in the deck.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import brentq

from pitch import data as _data
from pitch.config import AS_OF
from pitch.universe import ACTIVE, BENCHMARK, PITCHES

TRADING_DAYS = 252
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]

# The pitch being analysed. Every function below reads it; switch with set_pitch().
_STATE = {"ticker": ACTIVE}


def set_pitch(ticker: str) -> None:
    if ticker not in PITCHES:
        raise KeyError(ticker)
    _STATE["ticker"] = ticker


def _t() -> str:
    return _STATE["ticker"]


def _peers() -> list[str]:
    return PITCHES[_t()]["peers"]


def _fin() -> list[str]:
    """Balance-sheet lenders: EV/EBITDA and FCF yield are not meaningful for them."""
    return PITCHES[_t()]["financials"]


def _raw():
    return PITCHES[_t()]["raw"]


def load_prices():
    return _data.load_prices(_raw())


def load_returns():
    return _data.load_returns(_raw())


def load_factors():
    return _data.load_factors(_raw())


def load_fundamentals():
    return _data.load_fundamentals(_raw())


ASSUMPTIONS = {
    "terminal_growth": {"value": 0.03, "source": "Assumption: roughly long-run nominal US GDP growth; kept below the 10y yield"},
    "fade_years": {"value": 10, "source": "Assumption: growth fades linearly from stage-1 to terminal over 10 years"},
    "scenario_wacc_shift": {"value": 0.005, "source": "Assumption: +/-0.5pp WACC in bear/bull"},
    "trading_cost_bps": {"value": 10, "source": "Assumption: 10 bp per one-way switch (commission plus spread for a mega-cap)"},
    "sma_grid": {"value": [50, 100, 150, 200], "source": "Assumption: candidate trend-filter windows (trading days)"},
    "train_years": {"value": 3, "source": "Assumption: walk-forward training window"},
    "cash_return": {"value": 0.0, "source": "Assumption: cash earns 0 in the backtest (conservative for the strategy)"},
    "beta_window_years": {"value": 5, "source": "Convention: 5y of daily returns for the CAPM beta"},
}


# ---------- helpers ----------
def all_fundamentals() -> pd.DataFrame:
    extra = pd.read_csv(_raw() / "fundamentals_extra.csv", parse_dates=["period_end", "filed"])
    return pd.concat([load_fundamentals(), extra], ignore_index=True)


def fy_table(ticker: str) -> pd.DataFrame:
    f = all_fundamentals()
    return f[f.ticker == ticker].pivot(index="period_end", columns="metric", values="value").sort_index()


def total_debt(ticker: str, period_end: pd.Timestamp) -> float:
    f = all_fundamentals()
    g = f[(f.ticker == ticker) & (f.period_end == period_end)].set_index("metric")
    if "long_term_debt" not in g.index:
        return float("nan")
    debt = float(g.loc["long_term_debt", "value"])
    if g.loc["long_term_debt", "concept"] != "LongTermDebt":  # noncurrent only: add the current portion
        debt += float(g.loc["long_term_debt_current", "value"]) if "long_term_debt_current" in g.index else 0.0
    return debt


def shares() -> pd.DataFrame:
    return pd.read_csv(_raw() / "shares_outstanding.csv").set_index("ticker")


def price_at_asof(ticker: str) -> float:
    return float(load_prices()[ticker].loc[AS_OF])


def rf_10y() -> float:
    d = pd.read_csv(_raw() / "dgs10_daily.csv", parse_dates=["date"]).set_index("date")["DGS10"]
    return float(d.loc[:AS_OF].iloc[-1]) / 100


def r(x: float, n: int = 4) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), n)


# ---------- 02 factor model ----------
def factor_model() -> tuple[dict, pd.DataFrame]:
    f = load_factors()
    ret = load_returns()[_t()]
    df = f.join(ret.rename("ret"), how="inner").dropna()
    y = df["ret"] - df["RF"]
    X = sm.add_constant(df[FACTORS])
    fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    roll = []
    win = TRADING_DAYS
    for end in range(win, len(df) + 1, 5):
        w = df.iloc[end - win : end]
        b = np.linalg.lstsq(sm.add_constant(w[FACTORS]).values, (w["ret"] - w["RF"]).values, rcond=None)[0]
        roll.append(pd.Series(b[1:], index=FACTORS, name=w.index[-1]))
    rolling = pd.DataFrame(roll)
    out = {
        "window": {"start": df.index[0].strftime("%Y-%m-%d"), "end": df.index[-1].strftime("%Y-%m-%d"), "n_days": int(len(df))},
        "betas": {k: r(fit.params[k]) for k in FACTORS},
        "t_stats": {k: r(fit.tvalues[k], 2) for k in FACTORS},
        "alpha_annual": r(fit.params["const"] * TRADING_DAYS),
        "alpha_t": r(fit.tvalues["const"], 2),
        "r_squared": r(fit.rsquared),
        "method": "OLS of daily excess return on FF5 + momentum, Newey-West (5 lags) t-stats; rolling 252-day betas every 5 days",
    }
    return out, rolling


# ---------- 03 comps ----------
def comps() -> pd.DataFrame:
    sh = shares()
    rows = []
    for t in [_t(), *_peers()]:
        fy = fy_table(t)
        last = fy.index[fy["net_income"].notna()].max()
        row = fy.loc[last]
        mcap = price_at_asof(t) * sh.loc[t, "shares_outstanding"]
        debt, cash = total_debt(t, last), row.get("cash", np.nan)
        ebitda = row.get("operating_income", np.nan) + row.get("depreciation_amortization", np.nan)
        fcf = row.get("operating_cash_flow", np.nan) - row.get("capex", np.nan)
        gaps = []
        if t in _fin():
            gaps.append("lender: EV/EBITDA and FCF yield not meaningful (debt and cash flows are operating items)")
            ev_ebitda = fcf_yield = np.nan
        else:
            ev_ebitda = (mcap + debt - cash) / ebitda if ebitda > 0 else np.nan
            fcf_yield = fcf / mcap
        if t not in _fin():
            for m in ("operating_income", "depreciation_amortization", "capex", "cash"):
                if not np.isfinite(row.get(m, np.nan)):
                    gaps.append(f"{m} not reported in XBRL")
            if not np.isfinite(debt):
                gaps.append("total debt not reported in XBRL")
        if row["net_income"] <= 0:
            gaps.append("net loss: P/E not meaningful")
        if np.isfinite(ebitda) and ebitda <= 0:
            gaps.append("negative EBITDA: EV/EBITDA not meaningful")
        rows.append(
            {
                "ticker": t,
                "fiscal_year_end": last.strftime("%Y-%m-%d"),
                "price": price_at_asof(t),
                "market_cap": mcap,
                "ev_ebitda": ev_ebitda,
                "pe": mcap / row["net_income"] if row["net_income"] > 0 else np.nan,
                "fcf_yield": fcf_yield,
                "gaps": "; ".join(gaps),
            }
        )
    return pd.DataFrame(rows).set_index("ticker")


def business_snapshot(years: int = 5) -> dict:
    """Last `years` fiscal years of headline 10-K figures (USD) for the pitched stock, from SEC XBRL."""
    fy = fy_table(_t())
    fy = fy.assign(fcf=fy["operating_cash_flow"] - fy["capex"])
    cols = ["revenue", "operating_income", "net_income", "operating_cash_flow", "capex", "fcf"]
    tail = fy[[c for c in cols if c in fy]].dropna(how="all").tail(years)
    out = {}
    for d, row in tail.iterrows():
        rec = {k: r(v, 0) for k, v in row.items()}
        rec["operating_margin"] = r(row.get("operating_income", np.nan) / row["revenue"])
        rec["fcf_margin"] = r(row["fcf"] / row["revenue"])
        out[d.strftime("%Y-%m-%d")] = rec
    return out


def beta_sensitivity() -> dict:
    """Re-run the base DCF with the full-sample (2014 to as-of) beta instead of the 5y beta. Nothing else changes."""
    w = wacc_inputs()
    rets = load_returns()[[_t(), BENCHMARK]].loc[:AS_OF].dropna()
    beta = rets.cov().iloc[0, 1] / rets[BENCHMARK].var()
    ke = w["risk_free"]["value"] + beta * w["equity_risk_premium"]["value"]
    we = w["equity_weight"]["value"]
    wacc = we * ke + (1 - we) * w["pre_tax_cost_of_debt"]["value"] * (1 - w["tax_rate"]["value"])
    v = dcf_value(stage1_growth(), wacc)
    price = price_at_asof(_t())
    return {
        "beta": r(beta),
        "wacc": r(wacc),
        "implied_value": r(v, 2),
        "upside": r(v / price - 1),
        "source": "same DCF, beta from all daily returns since 2014 vs SPY",
    }


def comps_medians() -> dict:
    """Peer medians (excluding the pitched stock) over the multiples that are reported."""
    c = comps().drop(index=_t())
    return {k: r(c[k].median(), 4) for k in ("ev_ebitda", "pe", "fcf_yield")} | {
        "n": {k: int(c[k].notna().sum()) for k in ("ev_ebitda", "pe", "fcf_yield")}
    }


# ---------- 04 DCF ----------
def fcf_history() -> pd.Series:
    fy = fy_table(_t())
    return (fy["operating_cash_flow"] - fy["capex"]).dropna()


def wacc_inputs() -> dict:
    fy = fy_table(_t())
    last = fy.index.max()
    prev = fy.index[-2]
    px = load_returns()[[_t(), BENCHMARK]].loc[:AS_OF].dropna()
    px = px[px.index > pd.Timestamp(AS_OF) - pd.DateOffset(years=ASSUMPTIONS["beta_window_years"]["value"])]
    beta = px.cov().iloc[0, 1] / px[BENCHMARK].var()
    ff3 = pd.read_csv(_raw() / "ff3_monthly.csv")
    erp = ff3["Mkt-RF"].astype(float).mean() / 100 * 12
    rf = rf_10y()
    debt = total_debt(_t(), last)
    avg_debt = (debt + total_debt(_t(), prev)) / 2
    kd = fy.loc[last, "interest_expense"] / avg_debt
    tax = fy.loc[last, "income_tax"] / fy.loc[last, "pretax_income"]
    mcap = price_at_asof(_t()) * shares().loc[_t(), "shares_outstanding"]
    ke = rf + beta * erp
    we = mcap / (mcap + debt)
    wacc = we * ke + (1 - we) * kd * (1 - tax)
    return {
        "risk_free": {"value": r(rf), "source": f"FRED DGS10 on {AS_OF}"},
        "beta": {"value": r(beta), "source": "5y daily stock vs SPY returns to as-of (OLS slope)"},
        "equity_risk_premium": {
            "value": r(erp),
            "source": f"Ken French Mkt-RF, arithmetic mean 1926-07 to {ff3['month'].iloc[-1]}, x12",
        },
        "cost_of_equity": {"value": r(ke), "source": "CAPM: rf + beta x ERP"},
        "pre_tax_cost_of_debt": {"value": r(kd), "source": f"FY{last.year} interest expense / average total debt (SEC 10-K)"},
        "tax_rate": {"value": r(tax), "source": f"FY{last.year} income tax / pretax income (SEC 10-K)"},
        "equity_weight": {"value": r(we), "source": "market cap (as-of price x Yahoo shares) / (market cap + book debt)"},
        "wacc": {"value": r(wacc), "source": "we x ke + (1 - we) x kd x (1 - t)"},
    }


def stage1_growth() -> float:
    """Median of rolling 5-year FCF CAGRs over the stock's FY history (FY2010 onward, positive FCF only)."""
    s = fcf_history()
    s = s[s.index >= "2010-01-01"]
    cagr = (s / s.shift(5)) ** (1 / 5) - 1
    return float(cagr.dropna().median())


def dcf_value(g1: float, wacc: float, gt: float | None = None) -> float:
    gt = ASSUMPTIONS["terminal_growth"]["value"] if gt is None else gt
    n = ASSUMPTIONS["fade_years"]["value"]
    fy = fy_table(_t())
    last = fy.index.max()
    fcf = fcf_history().iloc[-1]
    pv = 0.0
    for t in range(1, n + 1):
        g = g1 + (gt - g1) * (t - 1) / (n - 1)
        fcf *= 1 + g
        pv += fcf / (1 + wacc) ** t
    pv += fcf * (1 + gt) / (wacc - gt) / (1 + wacc) ** n
    equity = pv - total_debt(_t(), last) + fy.loc[last, "cash"]
    return equity / shares().loc[_t(), "shares_outstanding"]


def dcf() -> dict:
    w = wacc_inputs()
    wacc = w["wacc"]["value"]
    g1 = stage1_growth()
    price = price_at_asof(_t())
    value = dcf_value(g1, wacc)
    implied_g1 = brentq(lambda g: dcf_value(g, wacc) - price, -0.5, 1.0)
    return {
        "base_fcf": r(fcf_history().iloc[-1], 0),
        "base_fcf_source": f"FY{fcf_history().index[-1].year} operating cash flow - capex (SEC 10-K)",
        "stage1_growth": r(g1),
        "stage1_growth_source": "median rolling 5y FCF CAGR, FY2010 onward",
        "wacc_inputs": w,
        "price": r(price, 2),
        "implied_value": r(value, 2),
        "upside": r(value / price - 1),
        "reverse_dcf_stage1_growth": r(implied_g1),
        "convention": "valuation date = as-of; FY+1 FCF discounted one full year (conservative)",
    }


# ---------- 05 risk + backtest ----------
def risk_metrics(ret: pd.Series, bench: pd.Series) -> dict:
    ret, bench = ret.dropna().align(bench.dropna(), join="inner")
    wealth = (1 + ret).cumprod()
    dd = wealth / wealth.cummax() - 1
    var = -ret.quantile(0.05)
    return {
        "ann_vol": r(ret.std() * np.sqrt(TRADING_DAYS)),
        "beta_vs_spy": r(ret.cov(bench) / bench.var()),
        "max_drawdown": r(dd.min()),
        "var_95_1d": r(var),
        "es_95_1d": r(-ret[ret <= -var].mean()),
    }


def risk() -> dict:
    rets = load_returns()
    out = {}
    for label, start in (("full", rets.index[0]), ("trailing_3y", pd.Timestamp(AS_OF) - pd.DateOffset(years=3))):
        w = rets.loc[start:AS_OF]
        out[label] = {
            "start": w.index[0].strftime("%Y-%m-%d"),
            _t(): risk_metrics(w[_t()], w[BENCHMARK]),
            BENCHMARK: risk_metrics(w[BENCHMARK], w[BENCHMARK]),
        }
    return out


def _strategy(ret: pd.Series, price: pd.Series, window: int, cost: float) -> pd.Series:
    pos = (price > price.rolling(window).mean()).astype(float).shift(1).fillna(0.0)
    trades = pos.diff().abs().fillna(pos)
    return pos * ret - trades * cost


def _perf(x: pd.Series) -> dict:
    wealth = (1 + x).cumprod()
    years = len(x) / TRADING_DAYS
    return {
        "cagr": r(wealth.iloc[-1] ** (1 / years) - 1),
        "ann_vol": r(x.std() * np.sqrt(TRADING_DAYS)),
        "sharpe_rf0": r(x.mean() / x.std() * np.sqrt(TRADING_DAYS), 3),
        "max_drawdown": r((wealth / wealth.cummax() - 1).min()),
    }


def backtest() -> tuple[dict, pd.DataFrame]:
    prices = load_prices()
    rets = load_returns()
    p, ret = prices[_t()], rets[_t()].fillna(0.0)
    cost = ASSUMPTIONS["trading_cost_bps"]["value"] / 1e4
    grid = ASSUMPTIONS["sma_grid"]["value"]
    train = ASSUMPTIONS["train_years"]["value"]
    first_year = rets.index[0].year + train
    oos, chosen = [], {}
    for year in range(first_year, pd.Timestamp(AS_OF).year + 1):
        tr = slice(f"{year - train}-01-01", f"{year - 1}-12-31")
        best = max(grid, key=lambda w: _perf(_strategy(ret, p, w, cost).loc[tr])["sharpe_rf0"] or -9)
        chosen[year] = best
        oos.append(_strategy(ret, p, best, cost).loc[f"{year}-01-01" : min(f"{year}-12-31", AS_OF)])
    strat = pd.concat(oos)
    curves = pd.DataFrame({"strategy": strat, "buy_hold": ret.loc[strat.index], "SPY": rets[BENCHMARK].loc[strat.index]})
    out = {
        "oos_start": strat.index[0].strftime("%Y-%m-%d"),
        "oos_end": strat.index[-1].strftime("%Y-%m-%d"),
        "signal": "long the stock when close > SMA(window), else cash; signal acts next day; window re-picked each Jan 1 by best trailing-3y Sharpe",
        "windows_chosen": {str(k): v for k, v in chosen.items()},
        **{k: _perf(curves[k]) for k in curves},
    }
    return out, (1 + curves).cumprod()


# ---------- 06 scenarios ----------
def scenarios() -> dict:
    d = dcf()
    wacc = d["wacc_inputs"]["wacc"]["value"]
    shift = ASSUMPTIONS["scenario_wacc_shift"]["value"]
    s = fcf_history()
    s = s[s.index >= "2010-01-01"]
    cagr = ((s / s.shift(5)) ** (1 / 5) - 1).dropna()
    price = d["price"]
    out = {}
    for name, q, dw in (("bear", 0.25, shift), ("base", 0.5, 0.0), ("bull", 0.75, -shift)):
        g = float(cagr.quantile(q))
        v = dcf_value(g, wacc + dw)
        out[name] = {"stage1_growth": r(g), "wacc": r(wacc + dw), "target": r(v, 2), "upside": r(v / price - 1)}
    out["method"] = "stage-1 growth at the 25th/50th/75th percentile of the stock's rolling 5y FCF CAGRs; WACC +/-0.5pp"
    return out
