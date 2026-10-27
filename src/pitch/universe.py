"""Each pitch: ticker, verified peers, and the benchmark.

V was the first pick (snapshots in data/raw). Its DCF came in below the price, so it was archived.
Later names use data/raw_<TICKER>.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# Archived first pick. data/raw still holds its snapshots.
TICKER = "V"
PEERS = ["MA", "AXP", "PYPL", "COF", "SYF", "ALLY"]
BENCHMARK = "SPY"
ALL_TICKERS = [TICKER, *PEERS, BENCHMARK]

# SEC Central Index Keys (EDGAR company search).
CIKS = {"V": 1403161, "MA": 1141391, "AXP": 4962, "PYPL": 1633917, "COF": 927628, "SYF": 1601712, "ALLY": 40729}

# metric -> XBRL us-gaap concepts in priority order (first one reported for a fiscal year wins).
CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "total_assets": ["Assets"],
    "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
INSTANT_METRICS = {"total_assets", "stockholders_equity"}


ACTIVE = "UNH"
PITCHES = {
    "V": {
        "peers": PEERS,
        "ciks": CIKS,
        "financials": ["AXP", "COF", "SYF", "ALLY"],
        "raw": _ROOT / "data" / "raw",
    },
    "UNH": {
        "peers": ["ELV", "CI", "HUM", "CNC", "MOH", "CVS"],
        "ciks": {"UNH": 731766, "ELV": 1156039, "CI": 1739940, "HUM": 49071, "CNC": 1071739, "MOH": 1179929, "CVS": 64803},
        "financials": [],
        "raw": _ROOT / "data" / "raw_UNH",
    },
    "COST": {
        "peers": ["WMT", "TGT", "DG", "DLTR", "BJ", "PSMT"],
        "ciks": {"COST": 909832, "WMT": 104169, "TGT": 27419, "DG": 29534, "DLTR": 935703, "BJ": 1531152, "PSMT": 1041803},
        "financials": [],
        "raw": _ROOT / "data" / "raw_COST",
    },
}
