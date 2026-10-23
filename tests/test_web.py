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
