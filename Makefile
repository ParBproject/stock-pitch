PY ?= python
export PYTHONPATH := src

.PHONY: all data screen summary notebooks deck pdf lint test clean

## Offline: rebuild everything from the frozen snapshots, then lint and test.
all: screen notebooks summary deck pdf lint test

## Online: re-fetch snapshots. This changes data and results, so review the diff.
data:
	$(PY) scripts/fetch_data.py
	$(PY) scripts/fetch_m2.py
	PYTHONPATH=src:scripts $(PY) scripts/fetch_m3.py
	PYTHONPATH=src:scripts $(PY) scripts/fetch_pitch.py UNH
	PYTHONPATH=src:scripts $(PY) scripts/fetch_pitch.py COST

screen:
	$(PY) scripts/build_screen.py

summary:
	$(PY) scripts/build_summary.py

deck:
	$(PY) scripts/build_deck.py

## Needs Playwright Chromium (python -m playwright install chromium).
pdf: deck
	$(PY) scripts/export_deck.py

notebooks:
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

lint:
	ruff check .
	ruff format --check .

test:
	$(PY) -m pytest -q

clean:
	rm -rf .pytest_cache .ruff_cache
