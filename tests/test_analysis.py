import json

import pandas as pd
import pytest

from pitch import analysis as a
from pitch import data
from pitch.config import AS_OF
from pitch.readme import M3_END, M3_START, render_m3
from pitch.summary import build_all
from pitch.universe import ACTIVE, BENCHMARK, PITCHES

ROOT = data.ROOT
FILES = {
    "results/summary.json": json.loads((ROOT / "results/summary.json").read_text()),
    "results/archive/V_summary.json": json.loads((ROOT / "results/archive/V_summary.json").read_text()),
    "results/compare/COST_summary.json": json.loads((ROOT / "results/compare/COST_summary.json").read_text()),
}
S = FILES["results/summary.json"]
V = FILES["results/archive/V_summary.json"]
C = FILES["results/compare/COST_summary.json"]


def test_all_summaries_reproduce_offline():
    assert build_all() == FILES


@pytest.mark.parametrize("ticker", ["UNH", "COST"])
def test_new_pitch_snapshots(ticker):
    raw = PITCHES[ticker]["raw"]
    data.verify_manifest(raw)
    px = data.load_prices(raw)
    assert list(px.columns) == [ticker, *PITCHES[ticker]["peers"], BENCHMARK]
    assert px.index.max() == pd.Timestamp(AS_OF)
    fd = data.load_fundamentals(raw)
    assert (fd.filed <= pd.Timestamp(AS_OF)).all() and set(fd.ticker) == set(PITCHES[ticker]["ciks"])


def test_peers_match_screen():
    screen = json.loads((ROOT / "results/screen.json").read_text())
    for c in screen["candidates"]:
        if c["ticker"] in PITCHES:
            assert PITCHES[c["ticker"]]["peers"] == c["verified_peers"]
    assert ACTIVE == screen["shortlist"][1] == "UNH"


def test_same_assumptions_for_every_pitch():
    assert S["assumptions"] == V["assumptions"] == C["assumptions"] == a.ASSUMPTIONS
    for k in ("risk_free", "equity_risk_premium"):
        assert S["valuation"]["wacc_inputs"][k] == V["valuation"]["wacc_inputs"][k] == C["valuation"]["wacc_inputs"][k]


def test_unh_headlines_pinned():
    v, sc = S["valuation"], S["scenarios"]
    assert S["ticker"] == "UNH" and S["as_of"] == "2026-09-30"
    assert (v["price"], v["implied_value"], v["upside"]) == (367.08, 526.64, 0.4347)
    assert v["reverse_dcf_stage1_growth"] == 0.0602
    assert v["wacc_inputs"]["wacc"]["value"] == 0.0799
    assert v["wacc_inputs"]["beta"]["value"] == 0.4067
    assert (sc["bear"]["target"], sc["base"]["target"], sc["bull"]["target"]) == (354.47, 526.64, 764.68)
    assert S["factor_model"]["betas"]["Mkt-RF"] == 0.8186 and S["factor_model"]["r_squared"] == 0.2307
    bt = S["backtest"]
    assert (bt["strategy"]["sharpe_rf0"], bt["buy_hold"]["sharpe_rf0"], bt["SPY"]["sharpe_rf0"]) == (0.291, 0.491, 0.874)
    assert S["verdict"]["supports_long"] and not S["verdict"]["all_scenarios_positive"]


def test_unh_fcf_figures_quoted_in_readme():
    a.set_pitch("UNH")
    fcf = a.fcf_history()
    assert round(fcf.loc["2025-12-31"] / 1e9, 1) == 16.1
    assert round(fcf.loc["2023-12-31"] / 1e9, 1) == 25.7
    a.set_pitch(ACTIVE)


def test_cost_headlines_pinned():
    v, sc = C["valuation"], C["scenarios"]
    assert (v["price"], v["implied_value"], v["upside"]) == (910.34, 410.96, -0.5486)
    assert (sc["bear"]["target"], sc["base"]["target"], sc["bull"]["target"]) == (284.63, 410.96, 496.94)
    assert C["backtest"]["buy_hold"]["sharpe_rf0"] == 0.993
    assert not C["verdict"]["supports_long"]


def test_v_archive_unchanged_from_m3():
    v, sc = V["valuation"], V["scenarios"]
    assert (v["price"], v["implied_value"], v["upside"], v["reverse_dcf_stage1_growth"]) == (359.33, 199.15, -0.4458, 0.2838)
    assert (sc["bear"]["target"], sc["base"]["target"], sc["bull"]["target"]) == (166.71, 199.15, 267.85)
    assert V["factor_model"]["betas"]["Mkt-RF"] == 1.0083
    bt = V["backtest"]
    assert (bt["strategy"]["sharpe_rf0"], bt["buy_hold"]["sharpe_rf0"]) == (0.1, 0.789)
    assert V["risk"]["full"]["V"]["max_drawdown"] == -0.3636
    assert "V" in S["archived"] and S["archived"]["V"]["reason"]


def test_comps_gaps_are_stated_not_filled():
    for t in ("AXP", "COF", "SYF", "ALLY"):
        assert V["comps"][t]["ev_ebitda"] is None and V["comps"][t]["gaps"]
    assert S["comps"]["CNC"]["pe"] is None and "net loss" in S["comps"]["CNC"]["gaps"]
    for t, c in S["comps"].items():
        if c["ev_ebitda"] is None:
            assert c["gaps"], t


def test_every_assumption_has_a_source():
    for s in (S, V, C):
        for block in (s["assumptions"], s["valuation"]["wacc_inputs"]):
            for item in block.values():
                assert item["source"]


def test_readme_m3_matches_summaries():
    readme = (ROOT / "README.md").read_text()
    section = M3_START + readme.split(M3_START, 1)[1].split(M3_END, 1)[0] + M3_END
    assert section == render_m3(FILES)


def test_figures_exist():
    for t in ("UNH", "COST", "V"):
        for name in ("02_rolling_betas", "03_comps", "04_dcf_growth_sensitivity", "05_backtest", "06_scenarios"):
            assert (ROOT / "figures" / t / f"{name}.png").exists()
