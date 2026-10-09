"""Session 2: compute the real numbers behind the written analysis.

Reuses the `failed_rules` column from Session 1's quarantine step instead of
re-deriving which rows violated which rule - the labels are already there.

Run with: python scripts/analyze.py
"""
import pandas as pd

CLEANED_PATH = "data/cleaned.csv"
QUARANTINED_PATH = "data/quarantined.csv"


def finding_zero_amount_fraud(quarantined: pd.DataFrame) -> None:
    rows = quarantined[quarantined["failed_rules"].str.contains("no_negative_values")]
    rows = rows[rows["amount"] == 0]
    n = len(rows)
    fraud_n = int((rows["isFraud"] == 1).sum())
    print("Finding 1: zero-amount CASH_OUT transactions")
    print(f"  Count: {n}")
    if n:
        print(f"  Fraud rate: {fraud_n}/{n} = {fraud_n / n:.1%}")
    print()


def finding_balance_mismatch_not_fraud_signal(
    quarantined: pd.DataFrame, cleaned: pd.DataFrame
) -> None:
    rows = quarantined[quarantined["failed_rules"].str.contains("origin_balance_consistency")]
    n = len(rows)
    total = len(cleaned) + len(quarantined)
    fraud_rate_mismatched = rows["isFraud"].mean()
    fraud_rate_cleaned = cleaned["isFraud"].mean()
    print("Finding 2: balance mismatches are not a fraud signal")
    print(f"  Mismatched rows: {n:,} ({n / total:.2%} of all rows)")
    print(f"  Fraud rate among mismatched: {fraud_rate_mismatched:.4%}")
    print(f"  Fraud rate in cleaned data: {fraud_rate_cleaned:.4%}")
    print()


def finding_fraud_concentration(cleaned: pd.DataFrame) -> None:
    fraud = cleaned[cleaned["isFraud"] == 1]
    print("Finding 3: where fraud is concentrated")
    print("  Fraud count by transaction type:")
    print(fraud["type"].value_counts().to_string())
    print()
    print(f"  Median amount, fraud rows: {fraud['amount'].median():,.2f}")
    print(f"  Median amount, all cleaned rows: {cleaned['amount'].median():,.2f}")
    print(f"  Fraud: {len(fraud):,} of {len(cleaned):,} cleaned rows ({len(fraud) / len(cleaned):.4%})")


def main() -> None:
    cleaned = pd.read_csv(CLEANED_PATH)
    quarantined = pd.read_csv(QUARANTINED_PATH)

    finding_zero_amount_fraud(quarantined)
    finding_balance_mismatch_not_fraud_signal(quarantined, cleaned)
    finding_fraud_concentration(cleaned)


if __name__ == "__main__":
    main()