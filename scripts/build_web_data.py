"""Write web/public/data/pitch.json and copy the design-system CSS and fonts into the web app (offline)."""

import shutil

from pitch.data import ROOT
from pitch.webdata import write

if __name__ == "__main__":
    write()
    dst = ROOT / "web" / "public" / "assets"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in ("tokens.css", "components.css"):
        shutil.copyfile(ROOT / "deck" / "assets" / f, dst / f)
    # Web fonts: Latin subsets as WOFF2 (the TTFs stay for matplotlib and the static deck).
    from fontTools import subset

    (dst / "fonts").mkdir()
    for name in ("Inter", "JetBrainsMono"):
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "tnum", "calt"]
        font = subset.load_font(str(ROOT / "deck/assets/fonts" / f"{name}.ttf"), opts)
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=list(range(0x20, 0x7F)) + [0xA0, 0xB1, 0xB7, 0xB2, 0x2013, 0x2014, 0x2019, 0x201C, 0x201D, 0x2192, 0x2190, 0x2212])
        sub.subset(font)
        subset.save_font(font, str(dst / "fonts" / f"{name}.woff2"), opts)
        shutil.copyfile(ROOT / "deck/assets/fonts" / f"OFL-{name}.txt", dst / "fonts" / f"OFL-{name}.txt")
    css = (dst / "tokens.css").read_text()
    css = css.replace('url("fonts/Inter.ttf") format("truetype")', 'url("fonts/Inter.woff2") format("woff2")')
    css = css.replace('url("fonts/JetBrainsMono.ttf") format("truetype")', 'url("fonts/JetBrainsMono.woff2") format("woff2")')
    (dst / "tokens.css").write_text(css)
    print("wrote web/public/data/pitch.json and web/public/assets/")
