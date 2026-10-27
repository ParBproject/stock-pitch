import json

import pandas as pd
import pytest

from pitch import data
from pitch.config import AS_OF
from pitch.summary import build_pitch
from pitch.universe import ALL_TICKERS, CIKS, PEERS, TICKER

SUMMARY = json.loads((data.ROOT / "results" / "archive" / "V_summary.json").read_text())  # archived V snapshots


def test_manifest_hashes_match():
    data.verify_manifest()


def test_verify_manifest_detects_tampering(tmp_path):
    for p in data.RAW.iterdir():
        (tmp_path / p.name).write_bytes(p.read_bytes())
    with open(tmp_path / "mom_daily.csv", "a") as f:
        f.write("2099-01-01,0.0\n")
    with pytest.raises(ValueError):
        data.verify_manifest(tmp_path)


def test_universe_matches_screen():
    screen = json.loads((data.ROOT / "results" / "screen.json").read_text())
    chosen = next(c for c in screen["candidates"] if c["ticker"] == screen["chosen"])
    assert TICKER == screen["chosen"]
    assert PEERS == chosen["verified_peers"]


def test_prices_point_in_time():
    px = data.load_prices()
    assert list(px.columns) == ALL_TICKERS
    assert px.index.max() == pd.Timestamp(AS_OF)
    assert px.index.is_monotonic_increasing and not px.index.has_duplicates
    assert ((px > 0) | px.isna()).all().all()


def test_returns_have_no_fill():
    r = data.load_returns()
    assert r["PYPL"].first_valid_index() > pd.Timestamp("2015-07-01")  # listed July 2015
    assert r.abs().max().max() < 1.0


def test_factors_are_decimal_and_bounded():
    f = data.load_factors()
    assert list(f.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF", "Mom"]
    assert f.index.max() <= pd.Timestamp(AS_OF)
    assert f.abs().max().max() < 0.25


def test_fundamentals_point_in_time():
    fd = data.load_fundamentals()
    assert set(fd.ticker) == set(CIKS)
    assert (fd.filed <= pd.Timestamp(AS_OF)).all()
    assert (fd.period_end <= pd.Timestamp(AS_OF)).all()
    assert not fd.duplicated(["ticker", "metric", "period_end"]).any()


def test_summary_reproducible_and_pinned():
    assert build_pitch("V") == SUMMARY
    assert SUMMARY["ticker"] == "V" and SUMMARY["as_of"] == "2026-09-30"
    assert SUMMARY["data"]["prices"]["V"] == {"first": "2014-01-02", "last": "2026-09-30", "n_days": 3205}
    assert SUMMARY["data"]["factors"]["last"] == "2026-08-31"
    assert SUMMARY["data"]["fundamentals_fy"]["V"]["revenue"]["n_years"] == 19
