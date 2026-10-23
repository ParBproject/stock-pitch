"""Write results/summary.json from the frozen snapshots (offline)."""

import json

from pitch.data import ROOT, verify_manifest
from pitch.readme import M3_END, M3_START, render_m3
from pitch.summary import build_summary


def main() -> None:
    verify_manifest()
    s = build_summary()
    (ROOT / "results" / "summary.json").write_text(json.dumps(s, indent=2) + "\n")
    readme = ROOT / "README.md"
    head, rest = readme.read_text().split(M3_START, 1)
    readme.write_text(head + render_m3(s) + rest.split(M3_END, 1)[1])
    print("wrote results/summary.json")


if __name__ == "__main__":
    main()
