import hashlib
import json

from pitch.config import EXCLUDED
from pitch.readme import END, START, render_section
from pitch.screen import ROOT, run_screen

RESULTS = json.loads((ROOT / "results" / "screen.json").read_text())


def test_snapshots_match_manifest():
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((ROOT / "data" / "snapshots" / name).read_bytes()).hexdigest() == digest


def test_screen_is_reproducible_offline():
    assert run_screen() == RESULTS


def test_headline_values_pinned():
    assert RESULTS["as_of"] == "2026-09-30"
    assert RESULTS["chosen"] == "V"
    assert RESULTS["shortlist"] == ["V", "UNH", "COST"]
    totals = {r["ticker"]: r["total"] for r in RESULTS["candidates"]}
    assert totals == {"V": 0.8426, "UNH": 0.7942, "COST": 0.7721, "JPM": 0.8438, "HD": 0.529}


def test_rules_hold():
    for r in RESULTS["candidates"]:
        assert r["ticker"] not in EXCLUDED
        if r["eligible"]:
            assert r["price_history_years"] >= 10 and len(r["verified_peers"]) >= 5
    assert 3 <= len(RESULTS["shortlist"]) <= 5


def test_readme_matches_results():
    readme = (ROOT / "README.md").read_text()
    section = START + readme.split(START, 1)[1].split(END, 1)[0] + END
    assert section == render_section(RESULTS)
