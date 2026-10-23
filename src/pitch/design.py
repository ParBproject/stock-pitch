"""Design system: tokens (design/tokens.json) -> CSS variables, components CSS, WCAG contrast checks, style guide."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = json.loads((ROOT / "design" / "tokens.json").read_text())
FONT_DIR = ROOT / "deck" / "assets" / "fonts"


# ---------- WCAG 2.x contrast ----------
def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_report() -> list[dict]:
    c = TOKENS["color"]
    out = []
    for fg, bg, need in TOKENS["contrast_pairs"]:
        ratio = contrast(c[fg], c[bg])
        out.append({"fg": fg, "bg": bg, "ratio": round(ratio, 2), "required": need, "pass": ratio >= need})
    return out


# ---------- CSS ----------
def tokens_css() -> str:
    t = TOKENS
    lines = [
        "/* Generated from design/tokens.json by src/pitch/design.py. Do not edit by hand. */",
        '@font-face{font-family:"Inter";src:url("fonts/Inter.ttf") format("truetype");font-weight:100 900;font-display:swap}',
        '@font-face{font-family:"JetBrains Mono";src:url("fonts/JetBrainsMono.ttf") format("truetype");font-weight:100 800;font-display:swap}',
        ":root{",
    ]
    lines += [f"  --c-{k}:{v};" for k, v in t["color"].items()]
    lines += [f"  --chart-{i + 1}:{v};" for i, v in enumerate(t["chart"])]
    lines += [f'  --font-sans:"{t["font"]["sans"]}",system-ui,sans-serif;', f'  --font-mono:"{t["font"]["mono"]}",ui-monospace,monospace;']
    lines += [f"  --fs-{i + 1}:{s}px;" for i, s in enumerate(t["font"]["scale"])]
    lines += [f"  --fw-{k}:{v};" for k, v in t["font"]["weight"].items()]
    lines += [f"  --lh-{k}:{v};" for k, v in t["font"]["line_height"].items()]
    lines += [f"  --sp-{i}:{s}px;" for i, s in enumerate(t["space"]["steps"])]
    g = t["grid"]
    lines += [f"  --grid-cols:{g['columns']};", f"  --grid-gutter:{g['gutter']}px;", f"  --grid-margin:{g['margin']}px;"]
    lines += [f"  --r-{k}:{v}px;" for k, v in t["radius"].items()]
    m = t["motion"]
    lines += [f"  --mo-fast:{m['fast']}ms;", f"  --mo-base:{m['base']}ms;", f"  --mo-slow:{m['slow']}ms;", f"  --mo-ease:{m['easing']};"]
    lines += ["}", "@media (prefers-reduced-motion:reduce){:root{--mo-fast:0ms;--mo-base:0ms;--mo-slow:0ms}}"]
    return "\n".join(lines) + "\n"


COMPONENTS_CSS = """/* Core components. Every value comes from a token in tokens.css. */
*{box-sizing:border-box}
html,body{margin:0;background:var(--c-bg);color:var(--c-fg);font:var(--fw-regular) var(--fs-3)/var(--lh-body) var(--font-sans)}
h1,h2,h3{line-height:var(--lh-tight);letter-spacing:-.01em;margin:0}
h1{font-size:var(--fs-6);font-weight:var(--fw-bold)}h2{font-size:var(--fs-5);font-weight:var(--fw-bold)}h3{font-size:var(--fs-4);font-weight:var(--fw-semibold)}
.kicker{color:var(--c-accent);text-transform:uppercase;letter-spacing:.14em;font-size:var(--fs-1);font-weight:var(--fw-semibold)}
.muted,.note{color:var(--c-muted)}.note{font-size:var(--fs-2)}.note b,.note em{color:var(--c-fg)}
.num,.n{font-family:var(--font-mono);font-variant-numeric:tabular-nums;color:var(--c-fg-strong);font-weight:var(--fw-medium)}
.na{color:var(--c-muted)}
code{font-family:var(--font-mono);color:var(--c-accent-strong);font-size:.92em}
.grid{display:grid;grid-template-columns:repeat(var(--grid-cols),1fr);column-gap:var(--grid-gutter);row-gap:var(--sp-3)}
.span-3{grid-column:span 3}.span-4{grid-column:span 4}.span-5{grid-column:span 5}.span-6{grid-column:span 6}.span-7{grid-column:span 7}
.span-8{grid-column:span 8}.span-12{grid-column:1/-1}
.card{background:var(--c-surface);border:1px solid var(--c-line);border-radius:var(--r-md);padding:var(--sp-4)}
.stat{background:var(--c-surface);border:1px solid var(--c-line);border-radius:var(--r-md);padding:var(--sp-4) var(--sp-5);
transition:border-color var(--mo-base) var(--mo-ease),transform var(--mo-base) var(--mo-ease)}
.stat:hover{border-color:var(--c-accent);transform:translateY(-2px)}
.stat b{display:block;font-family:var(--font-mono);font-size:var(--fs-6);font-weight:var(--fw-semibold);color:var(--c-fg-strong)}
.stat span{color:var(--c-muted);font-size:var(--fs-2)}
.stat.hl{border-color:var(--c-accent);box-shadow:0 0 0 1px var(--c-accent) inset}
.badge{display:inline-block;padding:var(--sp-1) var(--sp-2);border-radius:999px;font-size:var(--fs-1);font-weight:var(--fw-semibold);
background:var(--c-accent-tint);color:var(--c-accent-strong)}
.badge.neg{background:transparent;border:1px solid var(--c-negative);color:var(--c-negative)}
.badge.warn{background:transparent;border:1px solid var(--c-warning);color:var(--c-warning)}
.btn{display:inline-block;font:var(--fw-semibold) var(--fs-2) var(--font-sans);padding:var(--sp-2) var(--sp-3);border-radius:var(--r-sm);
border:1px solid var(--c-accent);background:var(--c-accent-tint);color:var(--c-accent-strong);cursor:pointer;text-decoration:none;
transition:background var(--mo-fast) var(--mo-ease)}
.btn:hover{background:var(--c-surface-2)}.btn:focus-visible{outline:2px solid var(--c-accent-strong);outline-offset:2px}
.btn.ghost{border-color:var(--c-line);background:transparent;color:var(--c-fg)}
.callout{border-left:3px solid var(--c-warning);background:var(--c-surface);padding:var(--sp-3) var(--sp-4);border-radius:0 var(--r-sm) var(--r-sm) 0}
.callout.risk{border-left-color:var(--c-negative)}
table{border-collapse:collapse;width:100%;font-size:var(--fs-3)}
th,td{padding:var(--sp-2) var(--sp-3);border-bottom:1px solid var(--c-line);text-align:left}
th{color:var(--c-muted);font-weight:var(--fw-medium);font-size:var(--fs-2)}
tr.hl td{background:var(--c-accent-tint)}tr.med td{color:var(--c-accent-strong)}
table.sm{font-size:var(--fs-2)}td.src,td.gap{color:var(--c-muted);font-size:var(--fs-1)}
img.fig{width:100%;border-radius:var(--r-sm);border:1px solid var(--c-line)}
"""

DECK_CSS = """/* Deck layout on the 12-column grid, 8px spacing scale. */
.slide{width:1280px;height:720px;margin:var(--sp-4) auto;padding:var(--sp-8) var(--grid-margin);position:relative;
border:1px solid var(--c-line);border-radius:var(--r-lg);overflow:hidden;
background:radial-gradient(1200px 500px at 100% 0,rgba(16,185,129,.07),transparent 60%),var(--c-bg);
opacity:0;transform:translateY(8px);transition:opacity var(--mo-slow) var(--mo-ease),transform var(--mo-slow) var(--mo-ease)}
.slide.in{opacity:1;transform:none}
.slide::after{content:attr(data-idx);position:absolute;right:var(--sp-4);bottom:var(--sp-3);color:var(--c-muted);font:var(--fs-1) var(--font-mono)}
.slide h2{margin:var(--sp-1) 0 var(--sp-4)}
.lede{font-size:var(--fs-5);line-height:1.3;max-width:1000px;margin:0 0 var(--sp-5)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:var(--grid-gutter);margin:var(--sp-5) 0}
.two{display:grid;grid-template-columns:repeat(12,1fr);column-gap:var(--grid-gutter);align-items:start}
.two>:first-child{grid-column:span 6}.two>:last-child{grid-column:span 6}
ol.big li,ul.big li{font-size:var(--fs-4);margin:0 0 var(--sp-3)}ul.risks li{font-size:var(--fs-3);margin:0 0 var(--sp-2)}
nav.deck-nav{position:fixed;bottom:var(--sp-2);left:50%;transform:translateX(-50%);color:var(--c-muted);font-size:var(--fs-1)}
@media (prefers-reduced-motion:reduce){.slide{opacity:1;transform:none;transition:none}}
@media print{@page{size:1280px 720px;margin:0}.slide{margin:0;border:0;border-radius:0;page-break-after:always;opacity:1;transform:none}
nav.deck-nav{display:none}}
"""


def write_css(out: Path = ROOT / "deck" / "assets") -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "tokens.css").write_text(tokens_css())
    (out / "components.css").write_text(COMPONENTS_CSS)
    (out / "deck.css").write_text(DECK_CSS)


PASS, FAIL = "<span class=badge>pass</span>", '<span class="badge neg">fail</span>'


def style_guide_html() -> str:
    from pitch.deck import fmt

    t, c = TOKENS, TOKENS["color"]
    d = json.loads((ROOT / "results" / "summary.json").read_text())
    sc, co = d["scenarios"], d["comps"]
    bear, base, bull = (fmt(sc[k]["target"], "usd2") for k in ("bear", "base", "bull"))
    up, beta = fmt(d["valuation"]["upside"], "spct1"), fmt(d["valuation"]["wacc_inputs"]["beta"]["value"], "d2")
    ev_t, ev_p, pe_m = fmt(co[d["ticker"]]["ev_ebitda"], "x1"), fmt(co["ELV"]["ev_ebitda"], "x1"), fmt(d["comps_peer_median"]["pe"], "x1")
    sw = "".join(
        f'<div class="card sw"><div class="chip" style="background:{v}"></div><b>{k}</b><span class="num">{v}</span></div>' for k, v in c.items()
    )
    rows = "".join(
        f"<tr><td><span style='color:{c[r['fg']]};background:{c[r['bg']]};padding:4px 8px;border-radius:4px'>{r['fg']} on {r['bg']}</span></td>"
        f"<td class=num>{r['ratio']:.2f}:1</td><td class=num>{r['required']}:1</td>"
        f"<td>{PASS if r['pass'] else FAIL}</td></tr>"
        for r in contrast_report()
    )
    scale = "".join(
        f'<div class="ts"><span class="num muted">{s}px</span><span style="font-size:{s}px">Long UNH: the price implies little growth</span></div>'
        for s in t["font"]["scale"]
    )
    cols = "".join(f'<div class="col span-1 num">{i + 1}</div>' for i in range(t["grid"]["columns"]))
    space = "".join(f'<div class="sp"><div style="width:{s}px"></div><span class="num muted">{s}</span></div>' for s in t["space"]["steps"][1:])
    m = t["motion"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>stock-pitch design system</title>
<link rel="stylesheet" href="assets/tokens.css"><link rel="stylesheet" href="assets/components.css">
<style>
body{{max-width:1200px;margin:0 auto;padding:var(--sp-7) var(--sp-5)}}section{{margin:0 0 var(--sp-8)}}h2{{margin:var(--sp-1) 0 var(--sp-4)}}
.sws{{display:grid;grid-template-columns:repeat(7,1fr);gap:var(--sp-2)}}.sw{{padding:var(--sp-2)}}.sw b{{display:block;font-size:var(--fs-2)}}
.sw span{{font-size:var(--fs-1);color:var(--c-muted)}}.chip{{height:48px;border-radius:var(--r-sm);border:1px solid var(--c-line);margin-bottom:var(--sp-2)}}
.ts{{display:flex;gap:var(--sp-4);align-items:baseline;padding:var(--sp-2) 0;border-bottom:1px solid var(--c-line)}}.ts .num{{width:56px;font-size:var(--fs-1)}}
.col{{background:var(--c-accent-tint);color:var(--c-accent-strong);text-align:center;padding:var(--sp-2) 0;border-radius:var(--r-sm);font-size:var(--fs-1)}}
.span-1{{grid-column:span 1}}.sp{{display:flex;align-items:center;gap:var(--sp-3);margin:var(--sp-1) 0}}.sp div{{height:16px;background:var(--c-accent);border-radius:2px}}
.row{{display:flex;gap:var(--sp-3);align-items:center;flex-wrap:wrap}}
</style></head><body>
<div class="kicker">stock-pitch</div><h1>Design system</h1>
<p class="muted">Generated from <code>design/tokens.json</code>. The deck, the figures and this page all use the same tokens.</p>
<section><div class="kicker">Color</div><h2>Palette</h2><div class="sws">{sw}</div></section>
<section><div class="kicker">Accessibility</div><h2>WCAG AA contrast</h2><table class="sm"><thead><tr><th>Pair</th><th>Ratio</th><th>Required</th><th></th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">Text pairs need at least 4.5:1 (AA, normal text). UI boundaries need at least 3:1. The pytest suite checks these.</p></section>
<section><div class="kicker">Type</div><h2>{t["font"]["sans"]}, with {t["font"]["mono"]} for numbers</h2>{scale}
<p>Tabular numbers: <span class="num">{base} · {up} · {beta}</span> line up in columns.</p></section>
<section><div class="kicker">Layout</div><h2>12-column grid on an 8px scale</h2><div class="grid">{cols}</div><div style="margin-top:var(--sp-4)">{space}</div></section>
<section><div class="kicker">Components</div><h2>Core UI</h2>
<div class="grid"><div class="stat span-4"><b>{bear}</b><span>bear</span></div><div class="stat hl span-4"><b>{base}</b><span>base</span></div>
<div class="stat span-4"><b>{bull}</b><span>bull</span></div></div>
<div class="row" style="margin:var(--sp-4) 0"><a class="btn" href="index.html">Open the deck</a><a class="btn ghost" href="pitch.pdf">PDF</a>
<span class="badge">supports long</span><span class="badge neg">bear case below price</span><span class="badge warn">low beta</span></div>
<div class="callout risk"><b>Risk callout.</b> <span class="muted">Used for anything that could break the thesis.</span></div>
<table class="sm" style="margin-top:var(--sp-4)"><thead><tr><th>Table</th><th>Value</th></tr></thead><tbody><tr class="hl"><td>Highlighted row</td><td class="num">{ev_t}</td></tr>
<tr><td>Regular row</td><td class="num">{ev_p}</td></tr><tr class="med"><td>Peer median</td><td class="num">{pe_m}</td></tr></tbody></table>
<p class="note">Example values on this page are read from <code>results/summary.json</code>. The deck's numbers are tested against <code>results/summary.json</code>.</p></section>
<section><div class="kicker">Motion</div><h2>{m["fast"]} to {m["slow"]} ms, with reduced motion respected</h2>
<p class="muted">Hover the stat cards or buttons. Slides fade in over {m["slow"]} ms. Under <code>prefers-reduced-motion: reduce</code>, every duration becomes 0.</p></section>
<section><div class="kicker">Charts</div><h2>Chart theme</h2><img class="fig" src="assets/06_scenarios.png" alt="Scenario chart in the chart theme"></section>
</body></html>
"""


def build() -> list[dict]:
    write_css()
    (ROOT / "deck" / "style-guide.html").write_text(style_guide_html())
    return contrast_report()
