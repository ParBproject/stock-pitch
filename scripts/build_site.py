"""Assemble the GitHub Pages bundle in site/: the Vite web deck at the root, the static deck under deck/.

Web-only tweaks for the hosted static deck (the PDF export is untouched): WOFF2 font subsets instead of TTFs,
lazy-loaded, sized images and WebP figures, and a meta description.
"""

import re
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def main() -> None:
    shutil.rmtree(SITE, ignore_errors=True)
    shutil.copytree(ROOT / "web" / "dist", SITE)
    deck = SITE / "deck"
    shutil.copytree(ROOT / "deck", deck)
    (SITE / ".nojekyll").touch()

    fonts = deck / "assets" / "fonts"
    for name in ("Inter", "JetBrainsMono"):
        shutil.copy(ROOT / "web" / "public" / "assets" / "fonts" / f"{name}.woff2", fonts)
        (fonts / f"{name}.ttf").unlink()
    css = deck / "assets" / "tokens.css"
    t = css.read_text()
    for name in ("Inter", "JetBrainsMono"):
        t = t.replace(f'url("fonts/{name}.ttf") format("truetype")', f'url("fonts/{name}.woff2") format("woff2")')
    assert ".ttf" not in t
    css.write_text(t)

    for png in (deck / "assets").glob("*.png"):
        Image.open(png).save(png.with_suffix(".webp"), "WEBP", quality=85, method=6)

    def img(m: re.Match) -> str:
        src = m.group(1)
        w, h = Image.open(deck / src).size
        return f'<img{m.group(0)[4:-1].replace(src, src[:-4] + ".webp")} width="{w}" height="{h}" loading="lazy" decoding="async">'

    desc = (
        '<meta name="description" content="UNH long pitch: DCF, reverse DCF, comps, factor model, '
        'risk and backtest, every number generated from code.">'
    )
    for page in ("index.html", "style-guide.html"):
        f = deck / page
        h = re.sub(r'<img[^>]*src="(assets/[^"]+\.png)"[^>]*>', img, f.read_text())
        f.write_text(h.replace("</title>", "</title>" + desc, 1))
    print("site/ ready:", sorted(p.name for p in SITE.iterdir()))


if __name__ == "__main__":
    main()
