"""Check every README link (repo paths on disk, URLs over HTTP) and every link on the deployed site."""

import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
SITE = sys.argv[1] if len(sys.argv) > 1 else "https://parbproject.github.io/stock-pitch/"


def status(url: str) -> int:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "stock-pitch-linkcheck"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ("href", "src"):
            if a.get(k) and not a[k].startswith(("#", "mailto:", "data:")):
                self.out.append(a[k])


def main() -> int:
    bad, n = [], 0
    readme = (ROOT / "README.md").read_text()
    for target in re.findall(r"\]\(([^)\s]+)\)", readme):
        n += 1
        if target.startswith("http"):
            code = status(target.split("#")[0])
            ok = code == 200
        else:
            code, ok = "file", (ROOT / target.split("#")[0]).exists()
        print(("ok " if ok else "BAD"), code, "README", target)
        ok or bad.append(target)
    for page in (SITE, urljoin(SITE, "deck/"), urljoin(SITE, "deck/style-guide.html")):
        with urllib.request.urlopen(page, timeout=30) as r:
            p = Links()
            p.feed(r.read().decode())
        for link in sorted(set(p.out)):
            url = urljoin(page, link)
            n += 1
            code = status(url)
            print(("ok " if code == 200 else "BAD"), code, page, link)
            code == 200 or bad.append(url)
    print(f"{n} links checked, {len(bad)} broken")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
