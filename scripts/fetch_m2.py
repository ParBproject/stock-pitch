"""Fetch and freeze M2 snapshots into data/raw (needs network). Tests never call this.

Point-in-time rule: only data dated on/before AS_OF, and SEC facts filed on/before AS_OF.
"""

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from pitch.config import AS_OF, PRICE_START, SEC_USER_AGENT
from pitch.universe import ALL_TICKERS, CIKS, CONCEPTS, INSTANT_METRICS

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FRENCH_FILES = {
    "ff5_daily.csv": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
    "mom_daily.csv": "F-F_Momentum_Factor_daily_CSV.zip",
}


def fetch_prices(raw_dir: Path = RAW, tickers: list = ALL_TICKERS) -> None:
    end = (pd.Timestamp(AS_OF) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(tickers, start=PRICE_START, end=end, auto_adjust=False, progress=False)
    adj = raw["Adj Close"][tickers].round(4)
    adj.index.name = "date"
    adj.to_csv(raw_dir / "prices_adj_close.csv")
    vol = raw["Volume"][tickers]
    vol.index.name = "date"
    vol.to_csv(raw_dir / "volume.csv")


def parse_french(text: str) -> pd.DataFrame:
    """Keep the first (daily) table: rows whose first field is an 8-digit date. Values are percent."""
    rows, header = [], None
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if header is None and len(parts) > 1 and parts[0] == "" and parts[1]:
            header = ["date", *parts[1:]]
            continue
        if header is not None:
            if len(parts[0]) == 8 and parts[0].isdigit():
                rows.append(parts)
            elif rows:
                break
    df = pd.DataFrame(rows, columns=header)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").astype(float)
    df.columns = [c.strip() for c in df.columns]
    return df.loc[PRICE_START:AS_OF]


def fetch_french(raw_dir: Path = RAW) -> None:
    for out, name in FRENCH_FILES.items():
        z = zipfile.ZipFile(io.BytesIO(requests.get(FRENCH + name, timeout=60).content))
        text = z.read(z.namelist()[0]).decode("latin-1")
        parse_french(text).to_csv(raw_dir / out)


def fetch_fundamentals(
    concepts: dict = CONCEPTS, instant: set = INSTANT_METRICS, out: str = "fundamentals_annual.csv", raw_dir: Path = RAW, ciks: dict = CIKS
) -> None:
    hdr = {"User-Agent": SEC_USER_AGENT}
    rows = []
    for t, cik in ciks.items():
        facts = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=hdr, timeout=60).json()
        gaap = facts["facts"].get("us-gaap", {})
        for metric, names in concepts.items():
            for priority, name in enumerate(names):
                for unit, items in gaap.get(name, {}).get("units", {}).items():
                    for f in items:
                        if f.get("form") != "10-K" or f["end"] > AS_OF or f["filed"] > AS_OF:
                            continue
                        if metric not in instant:
                            if not f.get("start") or (pd.Timestamp(f["end"]) - pd.Timestamp(f["start"])).days < 350:
                                continue
                        rows.append(
                            {
                                "ticker": t,
                                "metric": metric,
                                "concept": name,
                                "priority": priority,
                                "period_end": f["end"],
                                "value": f["val"],
                                "unit": unit,
                                "filed": f["filed"],
                                "accn": f["accn"],
                            }
                        )
    df = pd.DataFrame(rows)
    # As originally reported: earliest filing per (ticker, metric, period_end), then best-priority concept.
    df = df.sort_values(["ticker", "metric", "period_end", "priority", "filed"])
    df = df.drop_duplicates(["ticker", "metric", "period_end"], keep="first").drop(columns="priority")
    df.to_csv(raw_dir / out, index=False)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    fetch_prices()
    fetch_french()
    fetch_fundamentals()
    files = sorted(p.name for p in RAW.glob("*.csv"))
    manifest = {
        "as_of": AS_OF,
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "prices_adj_close.csv": "Yahoo Finance via yfinance, split/dividend-adjusted close",
            "volume.csv": "Yahoo Finance via yfinance, daily share volume",
            "ff5_daily.csv": "Kenneth R. French Data Library, Fama/French 5 factors (2x3) daily, percent",
            "mom_daily.csv": "Kenneth R. French Data Library, momentum factor daily, percent",
            "fundamentals_annual.csv": "SEC EDGAR XBRL companyfacts, 10-K annual facts filed on/before as_of",
        },
        "yfinance_version": yf.__version__,
        "sha256": {f: hashlib.sha256((RAW / f).read_bytes()).hexdigest() for f in files},
    }
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
