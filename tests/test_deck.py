import json
import re
from html.parser import HTMLParser

from pitch.deck import ALLOWED_PATTERNS, ALLOWED_TOKENS, ROOT, fmt, render, resolve

DATA = json.loads((ROOT / "results" / "summary.json").read_text())
HTML = (ROOT / "deck" / "index.html").read_text()


class Numbers(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found, self._cur, self._in_style = [], None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("style", "script"):
            self._in_style = True
        if tag == "span" and a.get("class") == "n":
            self._cur = [a["data-k"], a["data-f"], ""]

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._in_style = False
        if tag == "span" and self._cur:
            self.found.append(tuple(self._cur))
            self._cur = None

    def handle_data(self, data):
        if self._cur is not None:
            self._cur[2] += data


def test_deck_is_rendered_from_current_summary():
    assert render(DATA)[0] == HTML


def test_every_number_matches_summary_json():
    p = Numbers()
    p.feed(HTML)
    assert len(p.found) > 100
    for key, f, shown in p.found:
        assert shown == fmt(resolve(DATA, key), f), key


def test_no_untagged_numbers_in_slides():
    body = HTML.split("<body>", 1)[1].split("<script>", 1)[0]
    body = re.sub(r'<span class="n"[^>]*>.*?</span>', "", body)
    body = re.sub(r"<img[^>]*>", "", body)
    for pat in ALLOWED_PATTERNS:
        body = re.sub(pat, "", body)
    text = re.sub(r"<[^>]+>", " ", body)
    for tok in ALLOWED_TOKENS:
        text = text.replace(tok, "")
    assert not re.findall(r"\d", text), re.findall(r".{30}\d.{30}", text)[:5]


def test_twelve_slides_plus_appendix_and_required_content():
    titles = render(DATA)[1]
    assert len(titles) == 14 and titles[12].startswith("Appendix A") and titles[13].startswith("Appendix B")
    risks = HTML.split('id="s11"', 1)[1].split("</section>", 1)[0]
    for key in ("scenarios.bear.upside", "valuation.wacc_inputs.beta.value", "valuation.wacc_inputs.wacc.value", "backtest.SPY.sharpe_rf0"):
        assert f'data-k="{key}"' in risks
    assert "FCF is falling" in risks
    scen = HTML.split('id="s9"', 1)[1].split("</section>", 1)[0]
    assert 'data-k="scenarios.bear.upside"' in scen and 'data-k="beta_sensitivity.upside"' in scen
    appendix = HTML.split('id="s13"', 1)[1].split("</section>", 1)[0]
    assert "<b>V (first pick" in appendix and "<b>COST" in appendix


def test_deck_assets_and_pdf_exist():
    for f in ("02_rolling_betas", "03_comps", "04_dcf_growth_sensitivity", "05_backtest", "06_scenarios"):
        assert (ROOT / "deck" / "assets" / f"{f}.png").read_bytes() == (ROOT / "figures" / "UNH" / f"{f}.png").read_bytes()
    assert (ROOT / "deck" / "pitch.pdf").stat().st_size > 50_000


def test_source_cells_are_json_sources():
    import html as h

    sources = {x["source"] for x in DATA["assumptions"].values()} | {x["source"] for x in DATA["valuation"]["wacc_inputs"].values()}
    cells = re.findall(r"<td class=src>([^<]*)</td>", HTML)
    assert cells and all(h.unescape(c) in sources for c in cells)
