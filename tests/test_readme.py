"""Every number in the README comes from results/ JSON: generated blocks must match, and no digits may appear elsewhere."""

import json
import re
from pathlib import Path

from pitch.readme import END, M3_END, M3_START, PITCH_END, PITCH_START, START, render_pitch

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
S = json.loads((ROOT / "results" / "summary.json").read_text())


def test_pitch_block_matches_summary():
    block = PITCH_START + README.split(PITCH_START, 1)[1].split(PITCH_END, 1)[0] + PITCH_END
    assert block == render_pitch(S)


def test_beta_sensitivity_is_stated():
    block = README.split(PITCH_START, 1)[1].split(PITCH_END, 1)[0]
    assert f"${S['beta_sensitivity']['implied_value']:.2f}" in block
    assert f"{S['beta_sensitivity']['beta']:.2f}" in block


def test_no_numbers_outside_generated_blocks():
    text = README
    for a, b in ((PITCH_START, PITCH_END), (M3_START, M3_END), (START, END)):
        text = text.split(a, 1)[0] + text.split(b, 1)[1]
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # code blocks
    text = re.sub(r"`[^`]*`", "", text)  # inline code (paths)
    text = re.sub(r"\]\([^)]*\)", "]", text)  # link targets
    text = re.sub(r"\bM\d\b", "", text)  # milestone names
    text = re.sub(r"\b10-K\b|\bSHA-256\b|\b10-year Treasury\b", "", text)  # names, not figures
    stray = re.findall(r"\d[\d.,%]*", text)
    assert stray == [], f"numbers outside generated blocks: {stray}"


def test_readme_links_to_live_site_and_states_data_and_disclaimer():
    assert "https://parbproject.github.io/stock-pitch/" in README
    assert "Not investment advice" in README
    for src in ("Yahoo Finance", "SEC EDGAR", "FRED", "Ken French"):
        assert src in README
    assert S["as_of"] in README.split(PITCH_START, 1)[1].split(PITCH_END, 1)[0]
    for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", README):
        assert (ROOT / img).exists(), img
