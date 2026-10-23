"""Fetch and freeze all snapshots for one pitch into data/raw_<TICKER> (needs network).

Same sources, point-in-time rules and code paths as V's M2/M3 data. Usage: python scripts/fetch_pitch.py UNH
"""

import hashlib
import json
import sys
from datetime import UTC, datetime

import yfinance as yf
from fetch_m2 import fetch_french, fetch_fundamentals, fetch_prices
from fetch_m3 import fetch_extra

from pitch.config import AS_OF
from pitch.universe import BENCHMARK, PITCHES


def main(ticker: str) -> None:
    p = PITCHES[ticker]
    raw = p["raw"]
    raw.mkdir(parents=True, exist_ok=True)
    tickers = [ticker, *p["peers"], BENCHMARK]
    fetch_prices(raw, tickers)
    fetch_french(raw)
    fetch_fundamentals(raw_dir=raw, ciks=p["ciks"])
    fetch_extra(raw, tickers, p["ciks"])
    files = sorted(f.name for f in raw.glob("*.csv"))
    manifest = {
        "as_of": AS_OF,
        "ticker": ticker,
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": "same as data/raw/manifest.json (Yahoo Finance, Ken French Data Library, SEC EDGAR XBRL, FRED DGS10)",
        "yfinance_version": yf.__version__,
        "sha256": {f: hashlib.sha256((raw / f).read_bytes()).hexdigest() for f in files},
    }
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
