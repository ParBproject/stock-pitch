"""Fetch and freeze M1 data snapshots (needs network). Tests never call this."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from pitch.config import AS_OF, CANDIDATES, PRICE_START, SEC_USER_AGENT

SNAP = Path(__file__).resolve().parents[1] / "data" / "snapshots"
# SEC Central Index Keys (from EDGAR company search).
CIKS = {"JPM": 19617, "COST": 909832, "UNH": 731766, "V": 1403161, "HD": 354950}
CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss"],
    "eps_diluted": ["EarningsPerShareDiluted"],
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def annual_fy_years(facts: dict, names: list[str]) -> list[int]:
    years: set[int] = set()
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for n in names:
        for unit in gaap.get(n, {}).get("units", {}).values():
            for f in unit:
                if f.get("form") == "10-K" and f.get("fp") == "FY" and f.get("end", "") <= AS_OF:
                    start, end = f.get("start"), f["end"]
                    if start and (pd.Timestamp(end) - pd.Timestamp(start)).days > 350:
                        years.add(int(end[:4]))
    return sorted(years)


def main() -> None:
    SNAP.mkdir(parents=True, exist_ok=True)
    tickers = sorted({t for c, ps in CANDIDATES.items() for t in [c, *ps]})
    end = (pd.Timestamp(AS_OF) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    px = yf.download(tickers, start=PRICE_START, end=end, auto_adjust=True, progress=False)["Close"]
    px.index.name = "date"
    px.round(4).to_csv(SNAP / "prices.csv")

    meta = {}
    for t in tickers:
        info = yf.Ticker(t).info
        meta[t] = {
            "name": info.get("longName"),
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "market_cap": info.get("marketCap"),
        }
    (SNAP / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")

    hdr = {"User-Agent": SEC_USER_AGENT}
    sec = {}
    for t in CANDIDATES:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIKS[t]:010d}.json"
        facts = requests.get(url, headers=hdr, timeout=60).json()
        sec[t] = {"cik": CIKS[t], **{k: annual_fy_years(facts, v) for k, v in CONCEPTS.items()}}
    (SNAP / "sec_fy_coverage.json").write_text(json.dumps(sec, indent=2, sort_keys=True) + "\n")

    files = ["prices.csv", "meta.json", "sec_fy_coverage.json"]
    manifest = {
        "as_of": AS_OF,
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "prices.csv": "Yahoo Finance via yfinance (auto-adjusted close)",
            "meta.json": "Yahoo Finance via yfinance Ticker.info (industry, market cap at fetch time)",
            "sec_fy_coverage.json": "SEC EDGAR XBRL companyfacts (10-K FY facts ending on/before as_of)",
        },
        "yfinance_version": yf.__version__,
        "sha256": {f: sha(SNAP / f) for f in files},
    }
    (SNAP.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
