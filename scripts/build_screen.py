"""Run the offline screen, write results/screen.json and refresh the README section."""

import json

from pitch.readme import render_section, replace_section
from pitch.screen import ROOT, run_screen


def main() -> None:
    res = run_screen()
    (ROOT / "results" / "screen.json").write_text(json.dumps(res, indent=2) + "\n")
    readme = ROOT / "README.md"
    readme.write_text(replace_section(readme.read_text(), render_section(res)))
    print(f"chosen={res['chosen']} shortlist={res['shortlist']}")


if __name__ == "__main__":
    main()
