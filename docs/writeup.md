# Write-up: Mobile Money Data Cleaning + Dashboard

## Short version (LinkedIn)

"Clean the data" sounds simple until you try to define what "clean" means
in a way you can actually test. For my second portfolio project, I took a
6.3M-row mobile money transaction dataset (PaySim, modeled on real
transaction logs from an East African mobile network operator) and built a
validation pipeline instead of a generic cleaning script: 5 named rules,
each with pytest tests built from rows engineered to break exactly that
rule.

The interesting part wasn't the code, it was two findings that only showed
up once I started investigating *why* rows were failing validation instead
of just filtering them out. A tiny pattern of $0.00 cash-out transactions
turned out to be 100% fraud. And a much bigger pattern - 17% of transfers
having balance math that doesn't add up - turned out to have almost nothing
to do with fraud at all (0.11% fraud rate vs. 9.14% baseline). Messy-looking
data isn't automatically suspicious data, and it's worth checking that
assumption with numbers instead of assuming it.

Built with Python, pandas, pytest, and Streamlit. Live dashboard:
https://mobile-money-cleaning.streamlit.app · Code:
https://github.com/akorfaa/mobile-money-cleaning-dashboard

## Longer version (portfolio case study)

### The problem with "just clean the data"

A validation rule is only useful if you can say exactly what it checks and
prove it catches what it claims to catch. So instead of writing a script
that drops nulls and calls it done, this project's cleaning step
(`scripts/clean.py`) is 5 named, independently-testable rules, each one
with pytest tests built from hand-constructed rows designed to pass or fail
it specifically - 22 tests total.

### A design that had to change once it met real data

The original plan was strict in the literal sense: if any rule found a
violation, the script would raise an error and refuse to produce output at
all. That's a reasonable design for a dataset you expect to eventually be
perfectly clean. It's the wrong design for 108,213 rows of real financial
data, which will never hit zero violations no matter how carefully the
rules are written - two of them (origin-balance consistency, a rare
zero-amount pattern) found real, persistent characteristics of the data,
not bugs to be iterated away.

So the design changed to a clean/quarantine split:
`data/cleaned.csv` (every rule passed) and `data/quarantined.csv` (failed at
least one, with a column recording exactly which rule and why). This is
still "fail loudly" in spirit - nothing is silently trusted or silently
dropped, every excluded row is visible and labeled - it just doesn't block
the pipeline on data that was never going to be perfectly clean.

### Letting validation failures become the analysis

Two of this project's three findings came directly from asking "why did
these rows fail validation?" rather than from a separate exploratory
analysis pass:

- 16 rows failed the "no negative values" rule, all for the same reason -
  a $0.00 CASH_OUT with an untracked starting balance. All 16 were labeled
  fraud. That's too small a sample to build a rule around (n=16), but it's
  a specific, real pattern worth reporting honestly, including the caveat.
- 18,777 rows (17.35% of TRANSFER/CASH_OUT transactions) failed the
  balance-consistency rule. The instinct is to assume "inconsistent data"
  correlates with "suspicious activity." The numbers say the opposite:
  0.1065% fraud rate among these rows vs. 9.1445% in the cleaned data -
  these rows are *less* likely to be fraud, not more. Worth stating
  plainly rather than letting a reader assume the intuitive-but-wrong
  version.

The third finding - fraud occurring only in CASH_OUT and TRANSFER
transactions, at roughly 8.2x the median transaction amount - came from the
more conventional "look at the cleaned data directly" step, and reproduces
a well-known structural fact about this dataset, which is itself a useful
sanity check that nothing upstream was broken.

### Keeping the CLI script and the dashboard in sync

`app.py` originally read the two CSV outputs of `scripts/clean.py` from
disk. That works locally, but those files are deliberately gitignored (they
are derived output, not source data), so a deployed copy of the app - which
only has what's committed to the repo - would have crashed on launch. The
fix was to have the dashboard derive the same clean/quarantine split in
memory, by importing and calling the same `partition()` function the CLI
script uses, from the one file that is committed
(`data/sample_raw.csv`). One source of truth, one set of rules, used by two
different interfaces (a script and a dashboard) instead of two copies that
could silently drift apart over time.

### What I'd do differently with more time

See the README's "what I'd improve" section - trimming `requirements.txt`
to only what the deployed app needs, root-causing the balance-mismatch
pattern instead of just documenting it as unexplained, and adding a smoke
test for the dashboard itself.
