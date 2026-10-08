"""Session 1: validate the PaySim sample and split it into rows that pass
every rule ("clean") and rows that don't ("quarantined"), so a dashboard or
analysis built on the clean file can trust it without re-checking these
rules itself.

Two modes:
    --mode report   Count every rule's violations and print a summary.
                     Never writes output. Use this to see the scale of each
                     problem before deciding anything.
    --mode strict    (default) Run the same checks and write TWO files:
                     data/cleaned.csv (rows that passed every rule) and
                     data/quarantined.csv (rows that failed at least one
                     rule, with a new `failed_rules` column naming exactly
                     which rule(s) and why). Nothing is silently dropped or
                     silently passed - every row ends up in one file or the
                     other, and every quarantined row says why it's there.

Run with:
    python scripts/clean.py --mode report
    python scripts/clean.py --mode strict
"""
import argparse

import pandas as pd

INPUT_PATH = "data/sample_raw.csv"
CLEANED_PATH = "data/cleaned.csv"
QUARANTINED_PATH = "data/quarantined.csv"

VALID_TYPES = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}
BALANCE_TOLERANCE = 0.01  # absorbs float rounding, not real discrepancies


def rule_valid_transaction_type(df: pd.DataFrame) -> pd.Series:
    """Every row's `type` must be one of the five known transaction types."""
    return ~df["type"].isin(VALID_TYPES)


def rule_no_negative_values(df: pd.DataFrame) -> pd.Series:
    """Amount must be strictly positive; no balance can be negative.

    Session 1 found every violation of this rule in the real sample was a
    $0.00 CASH_OUT - and every single one of those 16 rows was fraud. That's
    too small a sample to prove a law, but it's a genuine, specific finding:
    these look like blocked/failed fraud attempts logged with a zeroed-out
    amount, not real money movements, so they don't belong in a "clean
    transactions" dataset even though they're meaningful on their own.
    """
    return (
        (df["amount"] <= 0)
        | (df["oldbalanceOrg"] < 0)
        | (df["newbalanceOrig"] < 0)
        | (df["oldbalanceDest"] < 0)
        | (df["newbalanceDest"] < 0)
    )


def rule_flagged_fraud_contract(df: pd.DataFrame) -> pd.Series:
    """PaySim's own documented rule: isFlaggedFraud is only ever set for a
    TRANSFER of more than 200,000. A flagged row that breaks this contract
    means the flagging logic or the data itself is inconsistent - worth
    knowing about, not silently trusting.
    """
    is_flagged = df["isFlaggedFraud"] == 1
    follows_contract = (df["type"] == "TRANSFER") & (df["amount"] > 200_000)
    return is_flagged & ~follows_contract


def rule_origin_balance_consistency(df: pd.DataFrame) -> pd.Series:
    """For TRANSFER/CASH_OUT, the sender's new balance should equal their old
    balance minus the amount sent - but ONLY when their old balance was
    actually tracked (nonzero). Session 0 found ~90% of these rows have
    oldbalanceOrg == 0 (a known dataset characteristic, not a per-row error).
    Restricting the rule to rows where tracking clearly happened cut the
    violation rate to 17.35% - and checking those rows showed the mismatches
    are NOT a fraud signal (0.11% fraud rate among them, versus 7.59%
    overall in this sample) and aren't rounding noise either (median
    difference ~160,000). It's a real, unexplained data-quality pattern in
    the source data, just one unrelated to fraud - so these rows get
    quarantined rather than trusted for balance-dependent analysis, not
    treated as suspicious.
    """
    is_transfer_or_cashout = df["type"].isin(["TRANSFER", "CASH_OUT"])
    was_tracked = df["oldbalanceOrg"] > 0
    expected_new_balance = df["oldbalanceOrg"] - df["amount"]
    mismatch = (expected_new_balance - df["newbalanceOrig"]).abs() > BALANCE_TOLERANCE
    return is_transfer_or_cashout & was_tracked & mismatch


def rule_no_duplicate_transactions(df: pd.DataFrame) -> pd.Series:
    """Catches exact duplicate rows - same sender, receiver, amount, type and
    time step appearing more than once - which suggests a logging/ingestion
    bug rather than two genuinely separate transactions.
    """
    subset = ["step", "type", "amount", "nameOrig", "nameDest"]
    return df.duplicated(subset=subset, keep=False)


RULES = [
    ("valid_transaction_type", rule_valid_transaction_type),
    ("no_negative_values", rule_no_negative_values),
    ("flagged_fraud_contract", rule_flagged_fraud_contract),
    ("origin_balance_consistency", rule_origin_balance_consistency),
    ("no_duplicate_transactions", rule_no_duplicate_transactions),
]


def run_rules(df: pd.DataFrame) -> list[tuple[str, int]]:
    """Run every rule. Return [(rule_name, violation_count), ...] only for
    rules that actually found violations.
    """
    failures = []
    for name, rule_fn in RULES:
        violation_mask = rule_fn(df)
        count = int(violation_mask.sum())
        if count > 0:
            failures.append((name, count))
    return failures


def partition(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split df into (clean_rows, quarantined_rows).

    clean_rows passed every single rule. quarantined_rows failed at least
    one, and gets a new `failed_rules` column: a comma-separated list of
    every rule name that row broke (a row can break more than one rule at
    once, and we want to see all of them, not just the first).
    """
    violations = pd.DataFrame(
        {name: rule_fn(df) for name, rule_fn in RULES}, index=df.index
    )
    is_quarantined = violations.any(axis=1)

    clean_rows = df.loc[~is_quarantined].copy()
    quarantined_rows = df.loc[is_quarantined].copy()
    quarantined_rows["failed_rules"] = violations.loc[is_quarantined].apply(
        lambda row: ", ".join(row.index[row]), axis=1
    )
    return clean_rows, quarantined_rows


def main(mode: str) -> None:
    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {INPUT_PATH}: {len(df):,} rows")

    failures = run_rules(df)

    if not failures:
        print("All validation rules passed - 0 violations.")
    else:
        print(f"{len(failures)} rule(s) found violations:")
        for name, count in failures:
            print(f"  {name}: {count:,} rows ({count / len(df):.4%})")

    if mode == "report":
        return

    clean_rows, quarantined_rows = partition(df)
    clean_rows.to_csv(CLEANED_PATH, index=False)
    quarantined_rows.to_csv(QUARANTINED_PATH, index=False)

    print()
    print(f"Wrote {CLEANED_PATH}: {len(clean_rows):,} rows (passed every rule)")
    print(
        f"Wrote {QUARANTINED_PATH}: {len(quarantined_rows):,} rows "
        "(failed at least one rule - see its failed_rules column)"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["report", "strict"],
        default="strict",
        help="report: count violations, never write output. "
        "strict: write data/cleaned.csv (rows passing every rule) and "
        "data/quarantined.csv (rows failing at least one, with reasons).",
    )
    args = parser.parse_args()
    main(args.mode)