"""M2 universe: the chosen stock, its verified peers (from results/screen.json) and the benchmark."""

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
