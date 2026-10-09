# Build Plan — Mobile Money Data Cleaning + Dashboard

Dataset: PaySim ("Synthetic Financial Datasets For Fraud Detection"), modeled on real
mobile money transaction logs from an East African mobile network operator.
~6.3M rows, 11 columns: step (time unit), type (transaction type), amount,
nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest,
isFraud, isFlaggedFraud.

Each session below is sized for 30-90 minutes. This document is the map, not the
turn-by-turn directions — full numbered steps come at the start of each session.
Check off sessions as we finish them and update `_docs/progress-log.md` at the end
of each one.

> **Environment note (same as Project 1):** no admin rights, so no installers that
> need elevation. PowerShell + venv, whole-file replacements instead of
> find-this-block edits, and a verification command after every step.

---

### Session 0 — Project skeleton, dataset acquisition, first look (45–75 min)
**Goal:** The real PaySim dataset downloaded locally, verified to actually be what
we expect (row count, columns, a few known data-quality quirks present), and a
reproducible, git-committed sample small enough to ship in the repo.
**Why it matters:** Writing cleaning rules against a dataset you've only read
about, without checking it's really what you think it is, is how you end up
debugging the wrong problem later. This also introduces working with a dataset
too large to commit to git directly (470MB+) — a real constraint, not a toy one.
**Covers:** venv + requirements.txt, Kaggle download, a deterministic sampling
script (`scripts/make_sample.py`) producing a committed `data/sample_raw.csv`,
an exploration script (`scripts/explore_raw.py`) confirming shape/dtypes and the
known anomalies (balance mismatches, isFraud vs isFlaggedFraud disagreement),
`.gitignore`, git init + first commit.

- [x] Done

### Session 1 — Cleaning script with validation rules (60–90 min)
**Goal:** A standalone `scripts/clean.py` that reads the raw sample, applies named
validation rules, and raises a clear, specific error (not a silent pass or a
generic exception) whenever a rule is violated — plus a way to run it in
"report" mode that counts violations instead of crashing, so you can see the
scale of each problem before deciding how to handle it.
**Why it matters:** "Clean the data" without rules you can name and test is just
vibes. This is the core skill this project proves — validation logic + decisions
documented, not a silent `.dropna()`.
**Covers:** 5 named rules (valid transaction type, no negative values,
flagged-fraud contract, origin-balance consistency, no duplicate
transactions), a `--mode report` vs `--mode strict` CLI, pytest tests with
rows engineered to fail each rule individually.

**Design change made mid-session:** the original plan was "raise and refuse
to write output if any rule fails." Real data at this scale never hits zero
violations, so that design would never succeed. Replaced with a
clean/quarantine split: `data/cleaned.csv` (every rule passed) and
`data/quarantined.csv` (failed at least one rule, with a `failed_rules`
column naming which). Still "fails loudly" - every bad row is visible and
labeled - just doesn't block the whole pipeline.

**Two findings from the real data (both candidates for Session 2):**
- `no_negative_values`: 16 violations, all identical in shape - $0.00
  CASH_OUT transactions - and all 16 are fraud (100%, though n=16 is too
  small to generalize from alone).
- `origin_balance_consistency`: 18,777 violations (17.35% of the sample).
  Counterintuitively, fraud rate among these rows is 0.11% vs 7.59%
  overall - balance mismatches are NOT a fraud signal, just an unexplained
  (and not rounding-sized - median diff ~160,000) data-quality pattern.

- [x] Done

### Session 2 — Analysis + Streamlit dashboard (60–90 min)
**Goal:** A short written analysis with 2–3 findings backed by specific numbers
from the cleaned data, and a Streamlit app that lets someone explore the same
data interactively (filters by transaction type, amount range, fraud flag;
at least one chart and one summary table).
**Why it matters:** The analysis proves you can read numbers and say something
true and specific about them. The dashboard proves you can hand that analysis
to someone else to explore themselves, instead of them trusting your slides.
**Covers:** `analysis/findings.md`, Streamlit app (`app.py`) with cached data
loading, filters, at least one chart, running it locally.

- [ ] Not started

### Session 3 — Deploy, README, write-up, wrap-up (45–75 min)
**Goal:** The dashboard live on Streamlit Community Cloud with a real URL,
finished README, and a decision-focused write-up for LinkedIn/portfolio.
**Why it matters:** Same bar as Project 1 — a project that only runs on your
machine is a much weaker portfolio piece than one with a live link.
**Covers:** Streamlit Community Cloud account + deploy, `requirements.txt`
pinned for deploy, README (problem, approach, tech stack, how to run locally,
what I'd improve), `docs/writeup.md`, closing `_docs/progress-log.md` entry,
`_docs/roadmap-status.md` update.

- [ ] Not started

---

## Rough time budget
4 sessions x ~45-90 min average ~ 3-6 hours total, spread across spare time.
Noticeably lighter than Project 1 — this is meant to be a palate-cleanser that
proves a different skill, not a second marathon.

## Definition of done for this project
- [ ] `scripts/clean.py` runs end to end and fails loudly on bad data (proven by tests)
- [ ] Pytest suite covers every validation rule, including rows engineered to fail each one
- [ ] `analysis/findings.md` has 2-3 findings, each backed by a specific number
- [ ] Streamlit dashboard runs locally with working filters and at least one chart
- [ ] Live, working Streamlit Community Cloud deployment URL
- [ ] README complete (problem, approach, tech stack, how to run, what I'd improve)
- [ ] Short write-up drafted for LinkedIn/portfolio site
