# stock-pitch

A long-only equity pitch built like a quant research project: every number in the deck comes from
committed data snapshots and code in this repo, and tests pin the headline figures.

Planned deliverables: an interactive HTML web deck (with PDF export) and a static scenario panel on
GitHub Pages. This repo is built one milestone at a time.

## M1: stock selection

Five liquid US large-caps were screened on four equally weighted criteria using frozen free data
(Yahoo Finance prices and industry labels, SEC EDGAR XBRL company facts). Candidates need at least
10 years of price history and at least 5 peers that share their Yahoo Finance industry label.

<!-- screen:start -->
**Chosen stock: V** (as of 2026-09-30). Shortlist: V, UNH, COST.

| Ticker | Industry | Peers | Coverage | Peer set | Testability | Recognisability | Total | Eligible |
|---|---|---|---|---|---|---|---|---|
| V | Credit Services | 6 | 0.75 | 0.75 | 1.00 | 0.87 | 0.843 | yes |
| UNH | Healthcare Plans | 6 | 1.00 | 0.75 | 1.00 | 0.43 | 0.794 | yes |
| COST | Discount Stores | 6 | 1.00 | 0.75 | 0.83 | 0.50 | 0.772 | yes |
| JPM | Banks - Diversified | 3 | 1.00 | 0.38 | 1.00 | 1.00 | 0.844 | no: only 3 same-industry peers (< 5) |
| HD | Home Improvement Retail | 2 | 1.00 | 0.25 | 0.50 | 0.37 | 0.529 | no: only 2 same-industry peers (< 5) |

Excluded (used by the DCF project): AAPL, MSFT, KO, JNJ, CAT, XOM.
<!-- screen:end -->

Scores and method live in [`results/screen.json`](results/screen.json); this table is rendered from
it by `scripts/build_screen.py`, and `tests/` checks they match. Snapshot sources and SHA-256 hashes are
in [`data/manifest.json`](data/manifest.json).

## Reproduce

```bash
pip install -e ".[dev]"
python scripts/build_screen.py      # offline, from data/snapshots
pytest && ruff check .
python scripts/fetch_data.py        # optional: re-fetch snapshots (network; changes results)
```

Not investment advice. Educational portfolio project.
