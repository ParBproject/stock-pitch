"""Screenshot the built web deck (desktop + mobile) and report console errors. Usage: shoot_web.py URL OUT_DIR"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main(url: str, out: str) -> None:
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        d = b.new_page(viewport={"width": 1440, "height": 900})
        d.on("console", lambda m: m.type == "error" and errors.append(m.text))
        d.on("pageerror", lambda e: errors.append(str(e)))
        d.goto(url)
        d.wait_for_selector("#hero-stats .stat")
        d.wait_for_timeout(800)
        d.screenshot(path=str(o / "desktop_top.png"))
        for sec, name in (("#p-price", "desktop_price_brush"), ("#p-dcf", "desktop_dcf"), ("#p-comps", "desktop_comps_drilldown")):
            d.locator(sec).scroll_into_view_if_needed()
            d.wait_for_timeout(600)
            if sec == "#p-comps":
                box = d.locator("#c-comps").bounding_box()
                d.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.5)
                d.wait_for_timeout(500)
            d.locator(sec).screenshot(path=str(o / f"{name}.png"))
        m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m.on("pageerror", lambda e: errors.append(str(e)))
        m.goto(url)
        m.wait_for_selector("#hero-stats .stat")
        m.wait_for_timeout(800)
        m.screenshot(path=str(o / "mobile_hero.png"))
        m.evaluate("document.getElementById('deck').scrollTo({left: document.getElementById('p-dcf').offsetLeft, behavior: 'auto'})")
        m.wait_for_timeout(800)
        m.screenshot(path=str(o / "mobile_dcf_swiped.png"))
        b.close()
    print("errors:", errors)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
