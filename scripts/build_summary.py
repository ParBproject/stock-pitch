"""Write results/summary.json from the frozen snapshots (offline)."""

import json

from pitch.data import ROOT, verify_manifest
from pitch.summary import build_summary


def main() -> None:
    verify_manifest()
    (ROOT / "results" / "summary.json").write_text(json.dumps(build_summary(), indent=2) + "\n")
    print("wrote results/summary.json")


if __name__ == "__main__":
    main()
