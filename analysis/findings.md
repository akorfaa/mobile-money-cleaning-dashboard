# Findings — Mobile Money Data Cleaning

Source: `data/cleaned.csv` (89,420 rows) and `data/quarantined.csv` (18,793
rows), both produced by `scripts/clean.py` from the PaySim sample
(`data/sample_raw.csv`, 108,213 rows). Reproduce these numbers with
`python scripts/analyze.py`.

**Sampling caveat:** this sample deliberately kept every fraud row from the
raw dataset plus a random sample of non-fraud rows (Session 0), so none of
the fraud *rates* below reflect real-world prevalence. They're only
meaningful as relative comparisons within this sample - mismatched vs.
non-mismatched, fraud vs. overall median - not as "X% of real transactions
are fraud."

## Finding 1 — A small, specific pattern of zero-amount CASH_OUTs is 100% fraud

16 transactions in the sample are $0.00 CASH_OUTs where the sender's balance
was never tracked (`oldbalanceOrg = 0`). All 16 - every single one - are
labeled fraud. None were caught by PaySim's own `isFlaggedFraud` system.

This reads as blocked or failed fraud attempts that still got logged, rather
than genuine data entry errors - a $0 "cash out" isn't a real money
movement. That's why the cleaning script excludes them from `cleaned.csv`
rather than silently keeping or silently dropping them: they're flagged in
`quarantined.csv` with the reason recorded, so the pattern stays visible.

**Honest limit:** n=16 is far too small to generalize into a rule like "flag
every $0 CASH_OUT as fraud" - it's a specific observation in one sample, not
a statistically validated signal.

## Finding 2 — Balance-math inconsistencies are not a fraud signal

17.35% of TRANSFER/CASH_OUT transactions with a tracked starting balance
(18,777 of 108,213 total rows) fail the balance-math check: the sender's new
balance doesn't equal old balance minus amount sent, by a wide margin
(median discrepancy ~160,000 - not rounding noise).

The intuitive guess would be that messy, inconsistent-looking data is more
likely to be fraudulent. The numbers say the opposite: the fraud rate among
these mismatched rows is **0.1065%**, versus **9.1445%** in the cleaned
data - mismatched rows are roughly 85x *less* likely to be fraud, not more.

This is a real, unexplained data-quality characteristic of the source
dataset (likely a logging/simulation gap in how origin balances were
updated for some transactions), but it is demonstrably unrelated to fraud.
Worth stating plainly: don't assume "looks broken" means "looks suspicious"
without checking.

## Finding 3 — Fraud is narrowly concentrated by transaction type and amount

In the cleaned data, fraud occurs in exactly two transaction types -
**CASH_OUT (4,097 cases)** and **TRANSFER (4,080 cases)** - and nowhere else
(not in PAYMENT, CASH_IN, or DEBIT at all). Fraud also skews toward much
larger amounts: the median fraudulent transaction is **441,873.49** (PaySim's amounts are unitless, not real currency), roughly **8.2x** the median of all cleaned transactions
(54,018.35).

For a fraud-detection system, this means type and amount alone already
narrow the search space enormously before any other signal is considered -
a PAYMENT or CASH_IN, or a small TRANSFER/CASH_OUT, essentially never shows
up as fraud in this data.

## Summary

| Finding | Number | What it means |
|---|---|---|
| Zero-amount CASH_OUTs | 16/16 fraud (100%) | A specific, tiny pattern worth flagging, not generalizing from |
| Balance mismatches | 0.11% fraud vs. 9.14% baseline | Messy ≠ suspicious - don't conflate data quality issues with fraud risk |
| Fraud concentration | 100% in CASH_OUT/TRANSFER, 8.2x median amount | Type + amount alone massively narrow where fraud actually occurs |
