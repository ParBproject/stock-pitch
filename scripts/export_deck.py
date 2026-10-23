"""Export deck/index.html to PDF and optional PNG screenshots with headless Chromium (Playwright).

Usage: python scripts/export_deck.py [--shots OUT_DIR SLIDE_NUMBERS...]
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "deck" / "index.html"


def main(argv: list[str]) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1320, "height": 800}, device_scale_factor=1)
        page.goto(DECK.as_uri())
        page.wait_for_load_state("networkidle")
        page.emulate_media(media="print")
        page.pdf(path=str(ROOT / "deck" / "pitch.pdf"), width="1280px", height="720px", print_background=True)
        page.emulate_media(media="screen")
        if argv[:1] == ["--shots"]:
            out = Path(argv[1])
            out.mkdir(parents=True, exist_ok=True)
            for n in argv[2:]:
                el = page.locator(f"#s{n}")
                title = el.get_attribute("data-title").split(":")[0].lower().replace(" ", "_")
                el.screenshot(path=str(out / f"slide{int(n):02d}_{title}.png"))
                print(out / f"slide{int(n):02d}_{title}.png")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
