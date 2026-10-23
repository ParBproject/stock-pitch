"""Offline loaders for the frozen M2 snapshots in data/raw. Nothing here touches the network."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"


def load_manifest(raw: Path = RAW) -> dict:
    return json.loads((raw / "manifest.json").read_text())


def verify_manifest(raw: Path = RAW) -> None:
    """Raise if any snapshot file differs from the hash recorded when it was frozen."""
    for name, digest in load_manifest(raw)["sha256"].items():
        actual = hashlib.sha256((raw / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"{name}: sha256 mismatch (snapshot changed since it was frozen)")


def _read(name: str, raw: Path) -> pd.DataFrame:
    return pd.read_csv(raw / name, index_col="date", parse_dates=True)


def load_prices(raw: Path = RAW) -> pd.DataFrame:
    """Daily adjusted closes, one column per ticker. NaN before a ticker's listing date."""
    return _read("prices_adj_close.csv", raw)


def load_volume(raw: Path = RAW) -> pd.DataFrame:
    return _read("volume.csv", raw)


def load_returns(raw: Path = RAW) -> pd.DataFrame:
    """Simple daily returns from adjusted closes. No forward fill, so gaps stay NaN."""
    return load_prices(raw).pct_change(fill_method=None).iloc[1:]


def load_factors(raw: Path = RAW) -> pd.DataFrame:
    """Fama/French 5 factors plus momentum, daily, as decimals (the source is in percent)."""
    ff5 = _read("ff5_daily.csv", raw)
    mom = _read("mom_daily.csv", raw)
    return ff5.join(mom, how="inner") / 100.0


def load_fundamentals(raw: Path = RAW) -> pd.DataFrame:
    """Tidy 10-K annual facts: ticker, metric, concept, period_end, value, unit, filed, accn."""
    return pd.read_csv(raw / "fundamentals_annual.csv", parse_dates=["period_end", "filed"])


def fundamentals_wide(metric: str, raw: Path = RAW) -> pd.DataFrame:
    """One metric as a period_end x ticker table, with values as originally reported."""
    df = load_fundamentals(raw)
    return df[df.metric == metric].pivot(index="period_end", columns="ticker", values="value").sort_index()
