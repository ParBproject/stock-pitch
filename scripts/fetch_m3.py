"""Fetch the extra valuation snapshots into data/raw and add them to the manifest (needs network).

Files already in the manifest are left untouched. Point-in-time rule: nothing dated or filed after AS_OF.
"""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from fetch_m2 import FRENCH, RAW, fetch_fundamentals, parse_french

from pitch.config import AS_OF
from pitch.universe import ALL_TICKERS, BENCHMARK

EXTRA_CONCEPTS = {
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
    ],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "long_term_debt_current": ["LongTermDebtCurrent"],
    "interest_expense": ["InterestExpenseNonoperating", "InterestExpense", "InterestExpenseDebt"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
}
EXTRA_INSTANT = {"cash", "long_term_debt", "long_term_debt_current"}


def fetch_extra(raw_dir: Path = RAW, tickers: list = ALL_TICKERS, ciks: dict | None = None) -> None:
    fetch_fundamentals(EXTRA_CONCEPTS, EXTRA_INSTANT, "fundamentals_extra.csv", raw_dir, ciks or {})

    rows = []
    for t in tickers:
        if t == BENCHMARK:
            continue
        s = yf.Ticker(t).get_shares_full(start="2025-01-01", end=(pd.Timestamp(AS_OF) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
        s.index = s.index.tz_localize(None).normalize()
        s = s[s.index <= AS_OF].sort_index()
        rows.append({"ticker": t, "shares_date": s.index[-1].strftime("%Y-%m-%d"), "shares_outstanding": int(s.iloc[-1])})
    pd.DataFrame(rows).to_csv(raw_dir / "shares_outstanding.csv", index=False)

    dgs = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2014-01-01&coed={AS_OF}")
    dgs.columns = ["date", "DGS10"]
    dgs["DGS10"] = pd.to_numeric(dgs["DGS10"], errors="coerce")
    dgs.dropna().to_csv(raw_dir / "dgs10_daily.csv", index=False)

    z = zipfile.ZipFile(io.BytesIO(requests.get(FRENCH + "F-F_Research_Data_Factors_CSV.zip", timeout=60).content))
    text = z.read(z.namelist()[0]).decode("latin-1")
    rows, header = [], None
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if header is None and len(parts) > 1 and parts[0] == "" and parts[1]:
            header = ["month", *parts[1:]]
        elif header is not None and len(parts[0]) == 6 and parts[0].isdigit():
            rows.append(parts)
        elif rows:
            break
    ffm = pd.DataFrame(rows, columns=header)
    ffm = ffm[ffm.month <= AS_OF[:4] + AS_OF[5:7]]
    ffm.to_csv(raw_dir / "ff3_monthly.csv", index=False)


def main() -> None:
    from pitch.universe import CIKS

    fetch_extra(RAW, ALL_TICKERS, CIKS)
    man_path = RAW / "manifest.json"
    man = json.loads(man_path.read_text())
    man["sources"].update(
        {
            "fundamentals_extra.csv": "SEC EDGAR XBRL companyfacts, extra 10-K facts filed on/before as_of",
            "shares_outstanding.csv": "Yahoo Finance via yfinance get_shares_full, last count on/before as_of",
            "dgs10_daily.csv": "FRED DGS10, 10-year Treasury constant-maturity yield, percent",
            "ff3_monthly.csv": "Kenneth R. French Data Library, Fama/French 3 factors monthly since 1926-07, percent",
        }
    )
    for f in ["fundamentals_extra.csv", "shares_outstanding.csv", "dgs10_daily.csv", "ff3_monthly.csv"]:
        man["sha256"][f] = hashlib.sha256((RAW / f).read_bytes()).hexdigest()
    man["sha256"] = dict(sorted(man["sha256"].items()))
    man_path.write_text(json.dumps(man, indent=2) + "\n")


if __name__ == "__main__":
    _ = parse_french
    main()
