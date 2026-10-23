import json

from pitch.data import ROOT
from pitch.webdata import build

WEB = json.loads((ROOT / "web/public/data/pitch.json").read_text())
SUMMARY = json.loads((ROOT / "results/summary.json").read_text())


def test_web_data_is_current_and_reproducible():
    assert json.loads(json.dumps(build())) == WEB


def test_web_data_embeds_summary_unchanged():
    assert WEB["summary"] == SUMMARY and WEB["ticker"] == SUMMARY["ticker"] == "UNH"


def test_no_dates_after_as_of():
    for block in ("prices_weekly", "rolling_betas", "backtest_weekly"):
        for series in WEB[block].values():
            assert series[-1][0] <= WEB["as_of"]
    assert WEB["prices_weekly"]["UNH"][-1] == [WEB["as_of"], SUMMARY["valuation"]["price"]]


def test_dcf_grid_contains_base_case_consistency():
    g = WEB["dcf_grid"]
    assert len(g["values"]) == len(g["growth"]) * len(g["wacc"])
    vals = [v for _, _, v in g["values"]]
    assert min(vals) < SUMMARY["valuation"]["price"] < max(vals)


def test_web_app_uses_design_tokens():
    css = (ROOT / "web/public/assets/tokens.css").read_text()
    assert "--c-accent:#10B981" in css and "--c-bg:#06080b" in css and "Inter.woff2" in css
    app = (ROOT / "web/src/app.css").read_text()
    assert "max-width:720px" in app and "scroll-snap-type:x mandatory" in app


# ---------- M7 scenario panel ----------
def _panel():
    import json
    from pathlib import Path

    return json.loads(Path("web/public/data/pitch.json").read_text())


def test_panel_defaults_match_summary():
    d = _panel()
    p, s = d["scenario_panel"], d["summary"]
    v = lambda g, w: p["values"][p["growth"].index(g)][p["wacc"].index(w)]  # noqa: E731
    b5, bf = p["defaults"]["beta"]["5y"], p["defaults"]["beta"]["full"]
    assert v(p["defaults"]["growth"], b5["wacc"]) == s["valuation"]["implied_value"]
    assert v(p["defaults"]["growth"], bf["wacc"]) == s["beta_sensitivity"]["implied_value"]
    wi = s["valuation"]["wacc_inputs"]
    assert round(b5["wacc"], 4) == wi["wacc"]["value"] and round(b5["beta"], 4) == wi["beta"]["value"]
    assert round(bf["wacc"], 4) == s["beta_sensitivity"]["wacc"] and round(bf["beta"], 4) == s["beta_sensitivity"]["beta"]
    assert p["defaults"]["growth"] == s["valuation"]["stage1_growth"] or round(p["defaults"]["growth"], 4) == s["valuation"]["stage1_growth"]
    assert p["price"] == s["valuation"]["price"]
    for k in ("bear", "base", "bull"):
        sc, ref = p["scenarios"][k], s["scenarios"][k]
        assert v(sc["growth"], sc["wacc"]) == ref["target"]
        assert round(sc["growth"], 4) == ref["stage1_growth"] and round(sc["wacc"], 4) == ref["wacc"]


def test_panel_surface_is_the_notebook_dcf():
    from pitch import analysis

    d = _panel()
    p = d["scenario_panel"]
    analysis.set_pitch(d["summary"]["ticker"])
    for gi, wi in [(0, 0), (len(p["growth"]) // 2, len(p["wacc"]) // 3), (-1, -1)]:
        g, w = p["growth"][gi], p["wacc"][wi]
        assert abs(p["values"][gi][wi] - analysis.dcf_value(g, w)) < 0.01
    assert len(p["fcf_paths_bn"]) == len(p["growth"])
