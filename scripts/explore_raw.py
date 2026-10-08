"""Session 0: confirm the dataset on disk really matches what we expect
before writing any cleaning code against it.

Run against the full raw file (default) or the sample:
    python scripts/explore_raw.py
    python scripts/explore_raw.py --path data/sample_raw.csv
"""
import argparse

import pandas as pd

DEFAULT_PATH = "data/PS_20174392719_1491204439457_log.csv"

# Explicit dtypes for two reasons: (1) it cuts memory use roughly in half
# compared to pandas' default guesses on a file this size, and (2) it forces
# us to look at every column and decide what it should be, instead of
# silently trusting whatever pandas infers.
DTYPES = {
    "step": "int32",
    "type": "category",
    "amount": "float64",
    "nameOrig": "string",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "nameDest": "string",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
    "isFraud": "int8",
    "isFlaggedFraud": "int8",
}


def main(path: str) -> None:
    df = pd.read_csv(path, dtype=DTYPES)

    print(f"File: {path}")
    print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print()
    print("Columns and dtypes:")
    print(df.dtypes)
    print()
    print("Transaction type counts:")
    print(df["type"].value_counts())
    print()

    n_fraud = (df["isFraud"] == 1).sum()
    n_flagged = (df["isFlaggedFraud"] == 1).sum()
    print(f"isFraud == 1: {n_fraud:,} rows ({n_fraud / len(df):.4%})")
    print(f"isFlaggedFraud == 1: {n_flagged:,} rows ({n_flagged / len(df):.4%})")

    disagreement = ((df["isFraud"] == 1) & (df["isFlaggedFraud"] == 0)).sum()
    print(f"Fraud but NOT flagged by the system: {disagreement:,} rows")

    # Balance-math check: for a TRANSFER or CASH_OUT, the sender's new balance
    # should equal old balance minus the amount sent. A small tolerance
    # absorbs float rounding, not real discrepancies.
    is_transfer_or_cashout = df["type"].isin(["TRANSFER", "CASH_OUT"])
    expected_new_balance = df["oldbalanceOrg"] - df["amount"]
    mismatch = is_transfer_or_cashout & (
        (expected_new_balance - df["newbalanceOrig"]).abs() > 0.01
    )
    print(f"Balance-math mismatches (TRANSFER/CASH_OUT): {mismatch.sum():,} rows")

    print()
    print("First 3 rows:")
    print(df.head(3).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=DEFAULT_PATH)
    args = parser.parse_args()
    main(args.path)
