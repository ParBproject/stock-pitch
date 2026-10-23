import json

from pitch.data import ROOT
from pitch.readme import M3_END, M3_START, render_m3

S = json.loads((ROOT / "results" / "summary.json").read_text())


def test_valuation_headlines_pinned():
    v = S["valuation"]
    assert v["price"] == 359.33
    assert v["implied_value"] == 199.15
    assert v["upside"] == -0.4458
    assert v["reverse_dcf_stage1_growth"] == 0.2838
    assert v["wacc_inputs"]["wacc"]["value"] == 0.1158
    assert v["wacc_inputs"]["risk_free"]["value"] == 0.0529


def test_scenarios_pinned_and_ordered():
    sc = S["scenarios"]
    assert (sc["bear"]["target"], sc["base"]["target"], sc["bull"]["target"]) == (166.71, 199.15, 267.85)
    assert sc["base"]["target"] == S["valuation"]["implied_value"]


def test_factor_model_pinned():
    fm = S["factor_model"]
    assert fm["betas"]["Mkt-RF"] == 1.0083
    assert fm["betas"]["SMB"] == -0.1963
    assert fm["betas"]["RMW"] == 0.2192
    assert fm["window"]["end"] == "2026-08-31"


def test_backtest_pinned_and_out_of_sample():
    bt = S["backtest"]
    assert bt["oos_start"] == "2017-01-03" and bt["oos_end"] == "2026-09-30"
    assert (bt["strategy"]["sharpe_rf0"], bt["buy_hold_V"]["sharpe_rf0"], bt["SPY"]["sharpe_rf0"]) == (0.1, 0.789, 0.874)


def test_risk_pinned():
    v = S["risk"]["full"]["V"]
    assert (v["ann_vol"], v["max_drawdown"], v["var_95_1d"], v["es_95_1d"]) == (0.2396, -0.3636, 0.0227, 0.035)


def test_comps_gaps_are_stated_not_filled():
    for t in ("AXP", "COF", "SYF", "ALLY"):
        c = S["comps"][t]
        assert c["ev_ebitda"] is None and c["fcf_yield"] is None and c["gaps"]
    assert S["comps"]["V"]["pe"] == 33.63


def test_every_assumption_has_a_source():
    for block in (S["assumptions"], S["valuation"]["wacc_inputs"]):
        for item in block.values():
            assert item["source"]


def test_readme_m3_matches_summary():
    readme = (ROOT / "README.md").read_text()
    section = M3_START + readme.split(M3_START, 1)[1].split(M3_END, 1)[0] + M3_END
    assert section == render_m3(S)


def test_figures_exist():
    for name in ("02_rolling_betas", "03_comps", "04_dcf_growth_sensitivity", "05_backtest", "06_scenarios"):
        assert (ROOT / "figures" / f"{name}.png").exists()
