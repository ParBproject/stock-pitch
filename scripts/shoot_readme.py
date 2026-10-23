"""Capture the README screenshots and panel GIF from a running web deck (default: the live site)."""

import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://parbproject.github.io/stock-pitch/"
OUT = Path(__file__).resolve().parents[1] / "docs" / "img"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(URL)
        pg.wait_for_timeout(1500)
        pg.screenshot(path=OUT / "hero.png")
        pg.evaluate("document.getElementById('p-panel').scrollIntoView()")
        pg.wait_for_timeout(2000)
        pg.screenshot(path=OUT / "panel.png")
        frames = []
        n = pg.evaluate("document.getElementById('sp-g').max")
        g0 = pg.evaluate("document.getElementById('sp-g').value")
        sweep = list(range(int(g0), int(n) // 6, -3)) + list(range(int(n) // 6, int(n) - 4, 3)) + list(range(int(n) - 4, int(g0), -3))
        for gi in sweep:
            pg.evaluate(f"(()=>{{const e=document.getElementById('sp-g');e.value={gi};e.dispatchEvent(new Event('input'))}})()")
            pg.wait_for_timeout(120)
            frames.append(Image.open(io.BytesIO(pg.locator("#p-panel").screenshot())).convert("RGB"))
        for k in ("full", "5y"):
            pg.click(f"#sp-beta button[data-k='{k}']")
            pg.wait_for_timeout(500)
            img = Image.open(io.BytesIO(pg.locator("#p-panel").screenshot())).convert("RGB")
            frames += [img] * 8
        frames = [f.resize((f.width * 2 // 3, f.height * 2 // 3)) for f in frames]
        pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in frames]
        pal[0].save(OUT / "panel.gif", save_all=True, append_images=pal[1:], duration=110, loop=0, optimize=True)
        for name, sel in (("prices", "#p-price"), ("comps", "#p-comps")):
            pg.evaluate(f"document.querySelector('{sel}').scrollIntoView()")
            pg.wait_for_timeout(1500)
            pg.screenshot(path=OUT / f"{name}.png")
        m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        m.goto(URL)
        m.wait_for_timeout(1200)
        m.evaluate("document.getElementById('p-panel').scrollIntoView()")
        m.wait_for_timeout(1500)
        m.click("#sp-handle")
        m.wait_for_timeout(600)
        m.screenshot(path=OUT / "mobile-panel.png")
        b.close()
    print("wrote", sorted(x.name for x in OUT.iterdir()))


if __name__ == "__main__":
    main()
