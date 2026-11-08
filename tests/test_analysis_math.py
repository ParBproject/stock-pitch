"""Formula checks for the DCF, WACC, risk, and trend-filter math.

The snapshot tests pin results/summary.json. These tests never read that file.
Every expected number is a short calculation on inputs the test supplies.
"""

import pandas as pd
import pytest
from scipy.optimize import brentq

from pitch import analysis as a
from pitch.config import AS_OF
from pitch.universe import BENCHMARK


def _stub_dcf(monkeypatch, *, fcf0, debt, cash, shares):
    inputs = {"fcf0": float(fcf0), "debt": float(debt), "cash": float(cash), "shares": float(shares)}
    monkeypatch.setattr(a, "dcf_inputs", lambda: inputs)


def test_constant_growth_collapses_to_gordon(monkeypatch):
    """Stage-1 growth equal to terminal growth is a Gordon perpetuity, at any horizon.

    Enterprise value = fcf0 * (1+g) / (wacc-g) = 100 * 1.04 / 0.05 = 2080.
    Equity = 2080 - 250 + 40 = 1870, and 1870 / 8 shares = 233.75.
    """
    _stub_dcf(monkeypatch, fcf0=100, debt=250, cash=40, shares=8)
    g, wacc = 0.04, 0.09
    out = a.dcf_breakdown(g, wacc, gt=g)

    n = a.ASSUMPTIONS["fade_years"]["value"]
    path = [100 * (1 + g) ** t for t in range(1, n + 1)]
    pv = sum(fcf / (1 + wacc) ** t for t, fcf in enumerate(path, start=1))
    # Terminal value is FCF_(n+1) / (wacc-g), discounted from the end of year n.
    pv_tv = path[-1] * (1 + g) / (wacc - g) / (1 + wacc) ** n

    assert out["fcf_path"] == pytest.approx(path)
    assert out["pv_fcf"] == pytest.approx(pv)
    assert out["pv_terminal"] == pytest.approx(pv_tv)
    assert out["pv_fcf"] + out["pv_terminal"] == pytest.approx(2080)
    assert out["equity"] == pytest.approx(2080 - 250 + 40)
    assert out["per_share"] == pytest.approx(233.75)
    assert a.dcf_value(g, wacc, gt=g) == pytest.approx(233.75)


def test_staged_fade_present_value_and_equity_bridge(monkeypatch):
    """Three explicit years, growth 20%, 12.5%, 5%, then a Gordon tail at 5%."""
    monkeypatch.setitem(a.ASSUMPTIONS["fade_years"], "value", 3)
    _stub_dcf(monkeypatch, fcf0=100, debt=50, cash=10, shares=4)
    out = a.dcf_breakdown(0.20, 0.10, gt=0.05)

    # g_t = g1 + (gt - g1) * (t - 1) / (n - 1). Year 1 is g1, year n is gt.
    assert out["fcf_path"] == pytest.approx([120.0, 135.0, 141.75])
    pv = 120 / 1.10 + 135 / 1.10**2 + 141.75 / 1.10**3
    pv_tv = 141.75 * 1.05 / (0.10 - 0.05) / 1.10**3
    assert out["pv_fcf"] == pytest.approx(pv)
    assert out["pv_terminal"] == pytest.approx(pv_tv)
    assert out["equity"] == pytest.approx(pv + pv_tv - 50 + 10)
    assert out["per_share"] == pytest.approx((pv + pv_tv - 50 + 10) / 4)


def test_omitted_terminal_growth_reads_the_assumption(monkeypatch):
    _stub_dcf(monkeypatch, fcf0=100, debt=0, cash=0, shares=1)
    monkeypatch.setitem(a.ASSUMPTIONS["terminal_growth"], "value", 0.01)
    assert a.dcf_value(0.05, 0.08) == pytest.approx(a.dcf_value(0.05, 0.08, gt=0.01))
    assert a.dcf_value(0.05, 0.08) != pytest.approx(a.dcf_value(0.05, 0.08, gt=0.03))


@pytest.mark.parametrize("g1", [0.02, 0.11])
def test_reverse_dcf_growth_round_trips(monkeypatch, g1):
    """The stage-1 growth that sets dcf_value equal to a price is the growth that produced it."""
    _stub_dcf(monkeypatch, fcf0=80, debt=100, cash=30, shares=5)
    wacc, gt = 0.09, 0.03
    price = a.dcf_value(g1, wacc, gt)
    solved = brentq(lambda g: a.dcf_value(g, wacc, gt) - price, -0.5, 1.0)
    assert solved == pytest.approx(g1, abs=1e-8)
    assert a.dcf_value(solved, wacc, gt) == pytest.approx(price)


def test_capm_wacc_on_a_known_beta(monkeypatch):
    """ke = rf + beta * erp, and wacc = we * ke + (1 - we) * kd * (1 - t).

    In-sample benchmark returns are 0.02, -0.01, 0.03, 0.00 (mean 0.01). The stock
    is 0.004 + 1.5 times that benchmark, so the OLS slope is 1.5. A row after the
    as-of date is not part of the sample. ke = 0.04 + 1.5 * 0.06 = 0.13, and
    wacc = 0.75 * 0.13 + 0.25 * 0.05 * 0.80 = 0.1075.
    """
    bench = [0.02, -0.01, 0.03, 0.00]
    stock = [0.004 + 1.5 * b for b in bench]
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2026-10-01"])
    frame = pd.DataFrame({"UNH": stock + [-0.20], BENCHMARK: bench + [0.10]}, index=idx)
    assert idx[-1] > pd.Timestamp(AS_OF)
    monkeypatch.setitem(a._STATE, "ticker", "UNH")
    monkeypatch.setattr(a, "load_returns", lambda: frame)
    rf, erp, we, kd, tax = 0.04, 0.06, 0.75, 0.05, 0.20
    monkeypatch.setattr(
        a,
        "wacc_inputs",
        lambda: {
            "risk_free": {"value": rf},
            "equity_risk_premium": {"value": erp},
            "equity_weight": {"value": we},
            "pre_tax_cost_of_debt": {"value": kd},
            "tax_rate": {"value": tax},
        },
    )

    got_beta, got_wacc = a.full_sample_beta_wacc()
    ke = rf + 1.5 * erp
    assert got_beta == pytest.approx(1.5)
    assert got_wacc == pytest.approx(we * ke + (1 - we) * kd * (1 - tax))
    assert got_wacc == pytest.approx(0.1075)


def test_risk_metrics_on_a_hand_built_series():
    """21 days so the 5% quantile lands on a point: (21 - 1) * 0.05 = 1, the second-worst return.

    Path: -5%, then +25% (the peak), then -40%, then 18 days of +1% that never
    undercut the trough. Max drawdown is the -40% drop. The tail is {-40%, -5%},
    so 95% VaR is 5% and expected shortfall is 22.5%. Benchmark = 0.001 + 0.5 * stock,
    so the slope of stock on the benchmark is 2.
    """
    stock = [-0.05, 0.25, -0.40, *([0.01] * 18)]
    bench = [0.001 + 0.5 * x for x in stock]
    got = a.risk_metrics(pd.Series(stock), pd.Series(bench))

    mean = sum(stock) / len(stock)
    std = (sum((x - mean) ** 2 for x in stock) / (len(stock) - 1)) ** 0.5
    mean_b = sum(bench) / len(bench)
    cov = sum((x - mean) * (b - mean_b) for x, b in zip(stock, bench, strict=True)) / (len(stock) - 1)
    var_b = sum((b - mean_b) ** 2 for b in bench) / (len(bench) - 1)

    assert got["ann_vol"] == round(std * a.TRADING_DAYS**0.5, 4)
    assert round(cov / var_b, 4) == 2.0
    assert got["beta_vs_spy"] == 2.0
    assert got["max_drawdown"] == -0.4
    assert got["var_95_1d"] == 0.05
    assert got["es_95_1d"] == 0.225


def test_sma_signal_is_next_day_and_cost_is_one_way():
    """Price above its 3-day average is a long signal, acted on the next day.

    Days 0-1 have no average. Day 2 ties the average (not a long). Day 3 breaks
    above it, so day 4 is the first long day. Day 5 is still long. Day 6 is cash
    again. Each switch pays the one-way cost; a day that stays long or stays in
    cash does not.
    """
    price = pd.Series([10.0, 10.0, 10.0, 12.0, 12.0, 9.0, 9.0, 9.0])
    ret = pd.Series([0.00, 0.01, -0.02, 0.05, 0.03, -0.04, 0.02, -0.01])
    gross = a._strategy(ret, price, window=3, cost=0.0)
    net = a._strategy(ret, price, window=3, cost=0.001)
    assert gross.tolist() == pytest.approx([0.0, 0.0, 0.0, 0.0, 0.03, -0.04, 0.0, 0.0])
    assert net.tolist() == pytest.approx([0.0, 0.0, 0.0, 0.0, 0.029, -0.04, -0.001, 0.0])


def test_perf_cagr_vol_sharpe_and_drawdown():
    """Four daily returns. Sharpe uses a zero risk-free rate and a 252-day year."""
    x = pd.Series([0.10, -0.05, 0.00, 0.02])
    wealth = 1.10 * 0.95 * 1.00 * 1.02  # 1.0659; the peak is 1.10, so the drawdown is 5%
    years = len(x) / a.TRADING_DAYS
    mean = (0.10 - 0.05 + 0.00 + 0.02) / 4
    std = ((0.10 - mean) ** 2 + (-0.05 - mean) ** 2 + (0.00 - mean) ** 2 + (0.02 - mean) ** 2) / 3
    std **= 0.5
    got = a._perf(x)
    assert got["cagr"] == round(wealth ** (1 / years) - 1, 4)
    assert got["ann_vol"] == round(std * a.TRADING_DAYS**0.5, 4)
    assert got["sharpe_rf0"] == round(mean / std * a.TRADING_DAYS**0.5, 3)
    assert got["max_drawdown"] == -0.05
