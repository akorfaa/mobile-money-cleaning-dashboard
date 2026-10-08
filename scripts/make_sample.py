"""Session 0: build a small, reproducible, git-committable sample of the raw
PaySim dataset, so the repo doesn't depend on a ~470MB file nobody can commit.

Fraud rows are rare (well under 1% of the data), so a plain random sample
risks ending up with very few of them - not enough to build meaningful
validation rules or dashboard filters around. Instead this script keeps
EVERY fraud row and adds a random sample of non-fraud rows on top.

A fixed random seed means re-running this script always produces the exact
same file - "reproducible" means someone else (or future you) can regenerate
this sample from the raw download and get byte-for-byte the same result.

Run with: python scripts/make_sample.py
"""
import pandas as pd

RAW_PATH = "data/PS_20174392719_1491204439457_log.csv"
SAMPLE_PATH = "data/sample_raw.csv"
TARGET_NON_FRAUD_ROWS = 100_000
RANDOM_SEED = 42

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


def main() -> None:
    df = pd.read_csv(RAW_PATH, dtype=DTYPES)

    fraud_rows = df[df["isFraud"] == 1]
    non_fraud_rows = df[df["isFraud"] == 0].sample(
        n=TARGET_NON_FRAUD_ROWS, random_state=RANDOM_SEED
    )

    # Sorted back into original row order so the sample still reads like a
    # time-ordered slice of the dataset, not a shuffled bag of rows.
    sample = pd.concat([fraud_rows, non_fraud_rows]).sort_index()
    sample.to_csv(SAMPLE_PATH, index=False)

    print(f"Raw dataset: {len(df):,} rows")
    print(f"Fraud rows kept (all of them): {len(fraud_rows):,}")
    print(f"Non-fraud rows sampled: {len(non_fraud_rows):,}")
    print(f"Sample written to {SAMPLE_PATH}: {len(sample):,} rows")


if __name__ == "__main__":
    main()
