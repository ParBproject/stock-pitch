"""Write results/summary.json plus archived/compared pitch summaries, and refresh the README (offline)."""

import json

from pitch.data import ROOT, verify_manifest
from pitch.readme import M3_END, M3_START, render_m3
from pitch.summary import build_all
from pitch.universe import PITCHES


def main() -> None:
    for p in PITCHES.values():
        verify_manifest(p["raw"])
    files = build_all()
    for rel, content in files.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, indent=2) + "\n")
    readme = ROOT / "README.md"
    head, rest = readme.read_text().split(M3_START, 1)
    readme.write_text(head + render_m3(files) + rest.split(M3_END, 1)[1])
    print("wrote", ", ".join(files))


if __name__ == "__main__":
    main()
