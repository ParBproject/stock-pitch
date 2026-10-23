"""Frozen M1 screen configuration. Changing anything here requires re-running scripts/fetch_data.py."""

import os

AS_OF = "2026-09-30"
PRICE_START = "2014-01-01"
EXCLUDED = ["AAPL", "MSFT", "KO", "JNJ", "CAT", "XOM"]  # tickers used by the DCF project

# Candidate -> proposed same-industry peers. Peer membership is VERIFIED against the
# snapshotted Yahoo Finance industry label; proposed peers that don't match are dropped.
CANDIDATES = {
    "JPM": ["BAC", "C", "WFC", "GS", "MS", "USB", "PNC", "TFC"],
    "COST": ["WMT", "TGT", "DG", "DLTR", "BJ", "PSMT"],
    "UNH": ["ELV", "CI", "HUM", "CNC", "MOH", "CVS"],
    "V": ["MA", "AXP", "PYPL", "COF", "SYF", "ALLY"],
    "HD": ["LOW", "FND", "TSCO", "WSM", "RH"],
}

MIN_YEARS = 10
MIN_PEERS = 5
WEIGHTS = {"coverage": 0.25, "peers": 0.25, "testability": 0.25, "recognisability": 0.25}
# SEC asks for "Name email". Read from env SEC_USER_AGENT (an Actions secret in CI);
# documented fallback is the project contact below.
SEC_USER_AGENT_FALLBACK = "Par Bahrae githubproproject@proton.me"
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT") or SEC_USER_AGENT_FALLBACK
