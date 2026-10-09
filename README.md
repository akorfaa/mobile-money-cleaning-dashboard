# Mobile Money Data Cleaning + Dashboard

**Live dashboard:** https://mobile-money-cleaning.streamlit.app
**Code:** https://github.com/akorfaa/mobile-money-cleaning-dashboard

## Problem

Real transaction data is never clean by default, and "clean it" is not a
well-defined instruction on its own - it has to mean something specific:
named rules, decisions about what to do with rows that break them, and
honesty about what you excluded and why. This project takes a large,
realistic mobile money transaction dataset (PaySim - modeled on real
transaction logs from an East African mobile network operator) and builds a
cleaning pipeline with named, tested validation rules, then an interactive
dashboard over the result.

## Dataset

[PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) - "Synthetic
Financial Datasets For Fraud Detection." ~6.3M transactions total; this
project works from a reproducible, seeded sample (`scripts/make_sample.py`)
of 108,213 rows - every fraud row in the raw file (8,213, since they're rare)
plus 100,000 random non-fraud rows. Amounts are unitless (synthetic data),
not a real currency.

## Approach

1. **Verify before building** (Session 0): confirmed the downloaded dataset
   actually matched its documented shape and known quirks before writing any
   cleaning logic against assumptions. Caught two real-world snags doing
   this: Kaggle's newer single-token auth isn't supported by the installed
   CLI version (fixed by using "Legacy API Credentials"), and the dataset's
   Kaggle slug had moved to a different owner than the one in the original
   brief.
2. **Validate, don't just clean** (Session 1): 5 named rules in
   `scripts/clean.py` - valid transaction type, no negative values, PaySim's
   own documented flagged-fraud contract, origin-balance consistency
   (refined to only check tracked balances, after finding ~90% of raw
   mismatches were a known dataset characteristic, not errors), and no
   duplicate transactions. Every rule has pytest tests built from rows
   engineered to pass or fail it.
3. **Decide what to do with violations, explicitly** (also Session 1): the
   original design was "raise an error and refuse to produce output if any
   rule fails." Real data at this scale never hits zero violations, so that
   design would never succeed. Replaced with a clean/quarantine split:
   `data/cleaned.csv` (every rule passed) and `data/quarantined.csv` (failed
   at least one, with a `failed_rules` column naming which) - still
   transparent about every excluded row, just not blocking the pipeline.
4. **Let the numbers decide what's a finding** (Session 2): two of the
   project's three findings came directly out of investigating validation
   violations rather than a separate "let's look for insights" pass -
   `analysis/findings.md` has all three with exact numbers.
5. **Make the dashboard deploy-safe** (Session 3): `app.py` originally read
   `data/cleaned.csv`/`data/quarantined.csv` from disk - but those are
   gitignored (derived output), so a deployed copy would have crashed.
   Refactored to derive the clean/quarantine split in memory, from the one
   committed data file (`data/sample_raw.csv`) and the one set of rules
   (`scripts/clean.py`), so the CLI script and the dashboard can never drift
   apart from each other.

## Tech stack

Python, pandas, pytest, Streamlit (deployed on Streamlit Community Cloud).

## How to run locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Regenerate the sample from the raw Kaggle download (optional - the
# sample is already committed to this repo):
# kaggle datasets download -d ealaxi/paysim1 -p data --unzip
# python scripts/make_sample.py

pytest -v                      # 22 tests
python scripts\clean.py --mode report   # see validation rule counts
python scripts\clean.py --mode strict   # write data/cleaned.csv + data/quarantined.csv
python scripts\analyze.py      # print the 3 findings' exact numbers
streamlit run app.py           # open the dashboard locally
```

## What I'd improve with more time

- `requirements.txt` has accumulated packages from all 3 sessions
  (`kaggle`, `pytest`, `jupytext`, etc.) that the deployed app doesn't
  actually need - a trimmed, deploy-only requirements file would build
  faster.
- The origin-balance-consistency mismatch (17.35% of TRANSFER/CASH_OUT rows)
  is documented as "a real, unexplained pattern" rather than root-caused -
  with more time I'd want to dig into whether it correlates with specific
  `step` ranges or `nameDest` patterns (merchant vs. customer) to actually
  explain it, not just quarantine it.
- The dashboard's amount-range slider uses raw min/max, which makes small
  amounts hard to select precisely given a handful of extreme outliers - a
  log-scale slider or a separate "typical range" vs. "full range" toggle
  would be more usable.
- No automated tests for `app.py` itself (only for the underlying
  `scripts/clean.py` logic it imports) - Streamlit apps are harder to unit
  test, but at minimum a smoke test confirming the app starts without
  exceptions would catch a regression before deploy.
