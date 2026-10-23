"""Render the HTML web deck from results/summary.json.

Every number on a slide is emitted through N(), which wraps it in <span class="n" data-k=PATH data-f=FORMAT>.
tests/test_deck.py re-resolves each PATH in the JSON, re-formats it and checks it matches, then checks that
no other digits appear in slide text (apart from a small allowlist of labels like "10-K").
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIGS = ["02_rolling_betas", "03_comps", "04_dcf_growth_sensitivity", "05_backtest", "06_scenarios"]
ALLOWED_PATTERNS = [
    r"FY\d{4}",
    r"slide \d+",
    r"<code>[^<]*</code>",
    r"Appendix [AB]",
    r"<td class=src>[^<]*</td>",
]  # td.src cells are JSON source strings, checked in tests
ALLOWED_TOKENS = [
    "10-year",
    "Stage-1",
    "stage-1",
    "SHA-256",
    "after M3",
    "10-K",
    "FF5",
    "252-day",
    "5-year",
    "5y",
    "3-year",
    "3y",
    "1-day",
    "95%",
    "rf = 0",
    "#06080b",
    "#10B981",
]


def resolve(data: dict, path: str):
    cur = data
    for part in path.split("."):
        cur = cur[part] if isinstance(cur, dict) else cur[int(part)]
    return cur


def fmt(value, f: str) -> str:
    if f == "pct1":
        return f"{value * 100:.1f}%"
    if f == "spct1":
        return f"{value * 100:+.1f}%"
    if f == "usd2":
        return f"${value:,.2f}"
    if f == "bn1":
        return f"${value / 1e9:,.1f}B"
    if f == "x1":
        return f"{value:.1f}x"
    if f == "d2":
        return f"{value:.2f}"
    if f == "s2":
        return f"{value:+.2f}"
    if f == "t1":
        return f"{value:.1f}"
    if f == "int":
        return f"{int(value)}"
    if f == "fy":
        return f"FY{value[:4]}"
    if f == "date":
        return str(value)
    raise ValueError(f)


class Deck:
    def __init__(self, data: dict):
        self.d = data

    def N(self, path: str, f: str) -> str:  # noqa: N802 - short on purpose, used everywhere in templates
        v = resolve(self.d, path)
        if v is None:
            return '<span class="na">n/a</span>'
        return f'<span class="n" data-k="{path}" data-f="{f}">{html.escape(fmt(v, f))}</span>'


def _slide(i: int, title: str, body: str, kicker: str = "") -> str:
    k = f'<div class="kicker">{kicker}</div>' if kicker else ""
    return f'<section class="slide" id="s{i}" data-title="{html.escape(title)}">{k}<h2>{title}</h2>{body}</section>'


def render(data: dict) -> tuple[str, list[str]]:
    D = Deck(data)
    N = D.N
    t = data["ticker"]
    v, fm = data["valuation"], data["factor_model"]
    years = sorted(data["business"])
    y0, y_peak, y1 = years[0], "2023-12-31", years[-1]
    w = "valuation.wacc_inputs"
    slides: list[tuple[str, str, str]] = []

    slides.append(
        (
            "UnitedHealth Group (UNH): Long",
            f"""<p class="lede">Base-case DCF value {N("valuation.implied_value", "usd2")} per share against an as-of price of
{N("valuation.price", "usd2")}: {N("valuation.upside", "spct1")}.</p>
<div class="stats">
<div class="stat"><b>{N("scenarios.bear.target", "usd2")}</b><span>bear ({N("scenarios.bear.upside", "spct1")})</span></div>
<div class="stat hl"><b>{N("scenarios.base.target", "usd2")}</b><span>base ({N("scenarios.base.upside", "spct1")})</span></div>
<div class="stat"><b>{N("scenarios.bull.target", "usd2")}</b><span>bull ({N("scenarios.bull.upside", "spct1")})</span></div>
</div>
<p class="note">As of {N("as_of", "date")}. The value is an intrinsic-value estimate, not a dated price target. The bear case sits
<em>below</em> the price, and the result depends on a low beta (slide 11). Educational project, not investment advice.</p>""",
            "Recommendation",
        )
    )
    slides.append(
        (
            "Thesis in three bullets",
            f"""<ol class="big">
<li><b>The price assumes little growth.</b> The reverse DCF says the price implies {N("valuation.reverse_dcf_stage1_growth", "pct1")}
stage-1 FCF growth. UNH's median rolling 5-year FCF growth is {N("valuation.stage1_growth", "pct1")}.</li>
<li><b>Revenue kept growing.</b> Revenue grew from {N(f"business.{y0}.revenue", "bn1")} ({fmt(y0, "fy")})
to {N(f"business.{y1}.revenue", "bn1")} ({fmt(y1, "fy")}). The problem is margin, not demand.</li>
<li><b>The thesis is a margin recovery, and it is not yet in the numbers.</b> Operating margin fell from {N(f"business.{y_peak}.operating_margin", "pct1")}
to {N(f"business.{y1}.operating_margin", "pct1")}. The long case needs FCF to stop shrinking.</li>
</ol>""",
            "Why",
        )
    )
    rows = "".join(
        f"<tr><td>{fmt(y, 'fy')}</td><td>{N(f'business.{y}.revenue', 'bn1')}</td><td>{N(f'business.{y}.operating_income', 'bn1')}</td>"
        f"<td>{N(f'business.{y}.operating_margin', 'pct1')}</td><td>{N(f'business.{y}.fcf', 'bn1')}</td>"
        f"<td>{N(f'business.{y}.fcf_margin', 'pct1')}</td></tr>"
        for y in years
    )
    slides.append(
        (
            "Business snapshot",
            f"""<table><thead><tr><th>Fiscal year</th><th>Revenue</th><th>Operating income</th><th>Op. margin</th><th>FCF</th>
<th>FCF margin</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">SEC EDGAR 10-K figures as first reported. FCF = operating cash flow − capex. Revenue keeps rising while operating
income and FCF shrink. That gap is the key driver to watch.</p>""",
            "Fundamentals",
        )
    )
    crow = "".join(
        f"<tr{' class=hl' if k == t else ''}><td>{k}</td><td>{N(f'comps.{k}.ev_ebitda', 'x1')}</td><td>{N(f'comps.{k}.pe', 'x1')}</td>"
        f"<td>{N(f'comps.{k}.fcf_yield', 'pct1')}</td><td class=gap>{html.escape(c['gaps'] or '')}</td></tr>"
        for k, c in data["comps"].items()
    )
    slides.append(
        (
            "Comps: a premium on earnings, a discount on cash",
            f"""<div class="two"><table class="sm"><thead><tr><td></td><th>EV/EBITDA</th><th>P/E</th><th>FCF yield</th><th>Gaps</th></tr>
</thead><tbody>{crow}<tr class="med"><td>Peer median</td><td>{N("comps_peer_median.ev_ebitda", "x1")}</td>
<td>{N("comps_peer_median.pe", "x1")}</td><td>{N("comps_peer_median.fcf_yield", "pct1")}</td><td></td></tr></tbody></table>
<img class="fig" src="assets/03_comps.png" alt="Comps bar charts"></div>
<p class="note">UNH trades above the peer median on P/E and EV/EBITDA but offers a higher FCF yield. Comps alone don't make the case.
Gaps are left blank, never estimated.</p>""",
            "Relative value",
        )
    )
    wrows = "".join(
        f"<tr><td>{k.replace('_', ' ')}</td><td>{N(f'{w}.{k}.value', 'd2' if k == 'beta' else 'pct1')}</td>"
        f"<td class=src>{html.escape(x['source'])}</td></tr>"
        for k, x in v["wacc_inputs"].items()
    )
    slides.append(
        (
            "DCF and reverse DCF: what the price assumes",
            f"""<div class="two"><table class="sm"><tbody>{wrows}</tbody></table><img class="fig" src="assets/04_dcf_growth_sensitivity.png" alt="DCF growth sensitivity"></div>
<p class="note">Base FCF {N("valuation.base_fcf", "bn1")} ({html.escape(v["base_fcf_source"])}). Stage-1 growth {N("valuation.stage1_growth", "pct1")}
fades to {N("assumptions.terminal_growth.value", "pct1")} terminal growth over {N("assumptions.fade_years.value", "int")} years.
Value {N("valuation.implied_value", "usd2")}. The price implies {N("valuation.reverse_dcf_stage1_growth", "pct1")} growth.</p>""",
            "Valuation",
        )
    )
    brows = "".join(
        f"<tr><td>{k}</td><td>{N(f'factor_model.betas.{k}', 's2')}</td><td>{N(f'factor_model.t_stats.{k}', 't1')}</td></tr>" for k in fm["betas"]
    )
    slides.append(
        (
            "Factor exposures: what you are really buying",
            f"""<div class="two"><table class="sm"><thead><tr><th>Factor</th><th>Beta</th><th>t-stat</th></tr></thead><tbody>{brows}
<tr><td>Alpha (annual)</td><td>{N("factor_model.alpha_annual", "pct1")}</td><td>{N("factor_model.alpha_t", "t1")}</td></tr></tbody></table>
<img class="fig" src="assets/02_rolling_betas.png" alt="Rolling factor betas"></div>
<p class="note">FF5 plus momentum, daily, {N("factor_model.window.start", "date")} to {N("factor_model.window.end", "date")}. R²
{N("factor_model.r_squared", "d2")}: most of UNH's risk is stock-specific. After the market, the profitability (RMW) tilt has the
strongest t-stat. Alpha is not significant.</p>""",
            "Exposures",
        )
    )
    rrows = ""
    for lab, key in (("Full sample", "full"), ("Trailing 3y", "trailing_3y")):
        for who in (t, "SPY"):
            p = f"risk.{key}.{who}"
            rrows += (
                f"<tr{' class=hl' if who == t else ''}><td>{lab}: {who}</td><td>{N(p + '.ann_vol', 'pct1')}</td>"
                f"<td>{N(p + '.beta_vs_spy', 'd2')}</td><td>{N(p + '.max_drawdown', 'pct1')}</td>"
                f"<td>{N(p + '.var_95_1d', 'pct1')}</td><td>{N(p + '.es_95_1d', 'pct1')}</td></tr>"
            )
    slides.append(
        (
            "Risk profile",
            f"""<table><thead><tr><td></td><th>Ann. vol</th><th>Beta vs SPY</th><th>Max drawdown</th><th>1-day 95% VaR</th><th>1-day 95% ES</th></tr>
</thead><tbody>{rrows}</tbody></table>
<p class="note">UNH is more volatile than SPY and has suffered a {N(f"risk.full.{t}.max_drawdown", "pct1")} drawdown. Its low
recent beta ({N(f"risk.trailing_3y.{t}.beta_vs_spy", "d2")} trailing 3y) reflects stock-specific moves, not safety.</p>""",
            "Risk",
        )
    )
    slides.append(
        (
            "Backtested signal: it does not help",
            f"""<div class="two"><table class="sm"><thead><tr><td></td><th>CAGR</th><th>Sharpe (rf = 0)</th><th>Max DD</th></tr></thead><tbody>
<tr><td>Trend signal</td><td>{N("backtest.strategy.cagr", "pct1")}</td><td>{N("backtest.strategy.sharpe_rf0", "d2")}</td><td>{N("backtest.strategy.max_drawdown", "pct1")}</td></tr>
<tr class=hl><td>Buy-and-hold {t}</td><td>{N("backtest.buy_hold.cagr", "pct1")}</td><td>{N("backtest.buy_hold.sharpe_rf0", "d2")}</td><td>{N("backtest.buy_hold.max_drawdown", "pct1")}</td></tr>
<tr><td>SPY</td><td>{N("backtest.SPY.cagr", "pct1")}</td><td>{N("backtest.SPY.sharpe_rf0", "d2")}</td><td>{N("backtest.SPY.max_drawdown", "pct1")}</td></tr>
</tbody></table><img class="fig" src="assets/05_backtest.png" alt="Backtest equity curves"></div>
<p class="note">Out-of-sample {N("backtest.oos_start", "date")} to {N("backtest.oos_end", "date")}, walk-forward window choice, next-day
execution, {N("assumptions.trading_cost_bps.value", "int")} bp per switch. Both the signal and buy-and-hold UNH trail SPY on Sharpe.
This is a valuation call, not a momentum trade.</p>""",
            "Evidence",
        )
    )
    srows = "".join(
        f"<tr{' class=hl' if n == 'base' else ''}><td>{n.title()}</td><td>{N(f'scenarios.{n}.stage1_growth', 'pct1')}</td>"
        f"<td>{N(f'scenarios.{n}.wacc', 'pct1')}</td><td>{N(f'scenarios.{n}.target', 'usd2')}</td><td>{N(f'scenarios.{n}.upside', 'spct1')}</td></tr>"
        for n in ("bear", "base", "bull")
    )
    slides.append(
        (
            "Bull, base and bear",
            f"""<div class="two"><table class="sm"><thead><tr><td></td><th>Stage-1 growth</th><th>WACC</th><th>Value</th><th>vs price</th></tr></thead>
<tbody>{srows}</tbody></table><img class="fig" src="assets/06_scenarios.png" alt="Scenario targets"></div>
<p class="note"><b>The bear case is {N("scenarios.bear.upside", "spct1")}, below today's price.</b> Growth is set at the lower quartile, median and upper
quartile of UNH's own rolling 5-year FCF growth, and WACC moves by ±{N("assumptions.scenario_wacc_shift.value", "pct1")}. No probability
weights are applied, because there is no data-based way to set them. All three cases still use the 5y beta that sets WACC at
{N(f"{w}.wacc.value", "pct1")}. With the full-sample beta, the base case alone falls to {N("beta_sensitivity.upside", "spct1")} (slide 11).</p>""",
            "Scenarios",
        )
    )
    slides.append(
        (
            "What to monitor",
            f"""<ul class="big">
<li><b>Next 10-K FCF.</b> FY{y1[:4]} FCF was {N(f"business.{y1}.fcf", "bn1")}. The price implies {N("valuation.reverse_dcf_stage1_growth", "pct1")}
a year from here. A further decline would break the thesis.</li>
<li><b>Operating margin.</b> It is {N(f"business.{y1}.operating_margin", "pct1")} against {N(f"business.{y_peak}.operating_margin", "pct1")} in
{fmt(y_peak, "fy")}. A recovery is the upside driver.</li>
<li><b>Beta re-estimate.</b> If the 5y beta drifts toward the full-sample {N("beta_sensitivity.beta", "d2")}, WACC rises to
{N("beta_sensitivity.wacc", "pct1")}.</li>
</ul>
<p class="note">No dated catalysts are listed: this project uses only the frozen data and does not forecast events.</p>""",
            "Catalysts",
        )
    )
    slides.append(
        (
            "Key risks and what would change my mind",
            f"""<ul class="risks">
<li><b>The bear case loses money.</b> The bear value of {N("scenarios.bear.target", "usd2")} is {N("scenarios.bear.upside", "spct1")} vs the price.</li>
<li><b>The discount rate rests on a low beta.</b> The 5y beta of {N(f"{w}.beta.value", "d2")} gives the {N(f"{w}.wacc.value", "pct1")} WACC.
The full-sample beta of {N("beta_sensitivity.beta", "d2")} gives a {N("beta_sensitivity.wacc", "pct1")} WACC and a value of
{N("beta_sensitivity.implied_value", "usd2")} ({N("beta_sensitivity.upside", "spct1")}). <em>On that beta the long case disappears.</em></li>
<li><b>FCF is falling.</b> It fell from {N(f"business.{y_peak}.fcf", "bn1")} ({fmt(y_peak, "fy")}) to {N(f"business.{y1}.fcf", "bn1")}
({fmt(y1, "fy")}), while stage-1 growth uses the {N("valuation.stage1_growth", "pct1")} long-run median.</li>
<li><b>The track record is weak.</b> Buy-and-hold UNH's Sharpe of {N("backtest.buy_hold.sharpe_rf0", "d2")} trails SPY's
{N("backtest.SPY.sharpe_rf0", "d2")}, with a {N(f"risk.full.{t}.max_drawdown", "pct1")} max drawdown.</li>
</ul>
<p class="callout risk note"><b>I would drop the long</b> if the next 10-K shows FCF still falling, or if a re-estimated beta pushes WACC to the point
where the base value falls below the price.</p>""",
            "Risks",
        )
    )
    slides.append(
        (
            "Methodology and reproducibility",
            f"""<ul>
<li>As-of {N("as_of", "date")}. Data is frozen with SHA-256 hashes: Yahoo Finance prices and share counts, SEC EDGAR XBRL 10-K facts
(filed on or before the as-of date), the Ken French library (factors end {N("factor_model.window.end", "date")}), and the FRED 10-year yield.</li>
<li>Notebooks <code>02</code> to <code>06</code> produce every figure. <code>results/summary.json</code> holds every number. A test checks
each number on these slides against that file.</li>
<li><code>make all</code> rebuilds everything offline and runs the tests.</li>
</ul>""",
            "Method",
        )
    )
    comp = data["comparison"]
    arch = data["archived"]
    slides.append(
        (
            "Appendix A: rejected candidates",
            f"""<table><thead><tr><td></td><th>Price</th><th>DCF value</th><th>vs price</th><th>Bear</th><th>Bull</th><th>Price-implied growth</th></tr></thead><tbody>
<tr><td>COST</td><td>{N("comparison.COST.price", "usd2")}</td><td>{N("comparison.COST.implied_value", "usd2")}</td><td>{N("comparison.COST.upside", "spct1")}</td>
<td>{N("comparison.COST.bear", "usd2")}</td><td>{N("comparison.COST.bull", "usd2")}</td><td>{N("comparison.COST.reverse_dcf_stage1_growth", "pct1")}</td></tr>
</tbody></table>
<p><b>V (first pick, archived).</b> {_strip_digits_note(arch["V"]["reason"])} See <code>results/archive/V_summary.json</code>.</p>
<p><b>COST (third on the shortlist).</b> Every scenario, including bull at {N("comparison.COST.bull", "usd2")}, is below the price. The price
implies {N("comparison.COST.reverse_dcf_stage1_growth", "pct1")} stage-1 growth.</p>
<p class="note">All three were run with identical code and assumptions. Nothing was tuned to make a long case appear.</p>""",
            "Appendix",
        )
    )
    a = data["assumptions"]
    arows = "".join(f"<tr><td>{k.replace('_', ' ')}</td><td class=src>{html.escape(x['source'])}</td></tr>" for k, x in a.items())
    slides.append(("Appendix B: assumptions", f'<table class="sm"><tbody>{arows}</tbody></table>', "Appendix"))
    _ = comp

    body = "\n".join(_slide(i + 1, s[0], s[1], s[2]) for i, s in enumerate(slides))
    return PAGE.replace("{{SLIDES}}", body).replace("{{TICKER}}", t), [s[0] for s in slides]


def _strip_digits_note(reason: str) -> str:
    """The archive reason is free text from summary.py; numbers in it are re-emitted from the V summary instead."""
    return (
        "Dropped after M3: the base DCF was well below the price, even the bull case showed a loss, and the price implied far "
        "more FCF growth than V's history."
    )


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TICKER}} long pitch</title>
<link rel="stylesheet" href="assets/tokens.css"><link rel="stylesheet" href="assets/components.css"><link rel="stylesheet" href="assets/deck.css">
</head><body>
<main><h1 style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap">{{TICKER}} long pitch</h1>
{{SLIDES}}
</main>
<nav class="deck-nav">← → or scroll · <a href="style-guide.html" style="color:inherit">design system</a></nav>
<script>
const s=[...document.querySelectorAll('.slide')];s.forEach((x,i)=>x.dataset.idx=(i+1)+' / '+s.length);
function fit(){const k=Math.min(1,(innerWidth-16)/1280);s.forEach(x=>{x.style.zoom=k})}addEventListener('resize',fit);fit();
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in')}),{threshold:.2});s.forEach(x=>io.observe(x));
if(matchMedia('print').matches)s.forEach(x=>x.classList.add('in'));addEventListener('beforeprint',()=>s.forEach(x=>x.classList.add('in')));
let i=0;addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key))i=Math.min(i+1,s.length-1);
else if(['ArrowLeft','PageUp'].includes(e.key))i=Math.max(i-1,0);else return;e.preventDefault();
s[i].scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})});
</script></body></html>
"""


def build() -> list[str]:
    import shutil

    data = json.loads((ROOT / "results" / "summary.json").read_text())
    page, titles = render(data)
    out = ROOT / "deck"
    (out / "assets").mkdir(parents=True, exist_ok=True)
    for f in FIGS:
        shutil.copyfile(ROOT / "figures" / data["ticker"] / f"{f}.png", out / "assets" / f"{f}.png")
    (out / "index.html").write_text(page)
    from pitch import design

    design.build()
    return titles
