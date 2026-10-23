import re

from pitch import design
from pitch.design import ROOT, TOKENS, contrast


def test_brand_tokens():
    assert TOKENS["color"]["bg"] == "#06080b" and TOKENS["color"]["accent"] == "#10B981"
    assert TOKENS["font"]["sans"] == "Inter" and TOKENS["font"]["mono"] == "JetBrains Mono"
    assert TOKENS["font"]["scale"] == [12, 14, 16, 20, 28, 40]
    assert TOKENS["grid"]["columns"] == 12
    assert all(s % 4 == 0 for s in TOKENS["space"]["steps"]) and TOKENS["space"]["unit"] == 8
    assert TOKENS["grid"]["gutter"] % 8 == 0 and TOKENS["grid"]["margin"] % 8 == 0


def test_motion_range_and_reduced_motion():
    m = TOKENS["motion"]
    assert all(200 <= m[k] <= 300 for k in ("fast", "base", "slow"))
    css = (ROOT / "deck/assets/tokens.css").read_text()
    assert "prefers-reduced-motion:reduce" in css and "--mo-slow:0ms" in css
    assert "prefers-reduced-motion:reduce" in (ROOT / "deck/assets/deck.css").read_text()


def test_wcag_aa_contrast():
    assert round(contrast("#ffffff", "#000000"), 2) == 21.0  # sanity check on the formula
    report = design.contrast_report()
    assert report and all(r["pass"] for r in report), [r for r in report if not r["pass"]]
    assert all(r["required"] >= 4.5 for r in report if r["bg"] != "line")


def test_generated_css_is_current():
    a = ROOT / "deck/assets"
    assert (a / "tokens.css").read_text() == design.tokens_css()
    assert (a / "components.css").read_text() == design.COMPONENTS_CSS
    assert (a / "deck.css").read_text() == design.DECK_CSS


def test_components_use_tokens_only():
    css = design.COMPONENTS_CSS + design.DECK_CSS
    hexes = set(re.findall(r"#[0-9a-fA-F]{3,6}\b", css))
    assert not hexes, hexes  # colors only via var(--c-*)
    sizes = {int(x) for x in re.findall(r"font-size:(\d+)px", css)}
    assert sizes <= set(TOKENS["font"]["scale"])


def test_style_guide_and_fonts():
    assert (ROOT / "deck/style-guide.html").read_text() == design.style_guide_html()
    for f in ("Inter.ttf", "JetBrainsMono.ttf", "OFL-Inter.txt", "OFL-JetBrainsMono.txt"):
        assert (ROOT / "deck/assets/fonts" / f).stat().st_size > 1000


def test_deck_uses_design_system():
    html = (ROOT / "deck/index.html").read_text()
    for f in ("tokens.css", "components.css", "deck.css"):
        assert f"assets/{f}" in html
    assert "<style>" not in html
