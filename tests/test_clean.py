"""Session 1: one test per validation rule, each with a row engineered to
violate exactly that rule (and a baseline valid row that should never trip
any rule). Also covers partition() and main()'s two modes.
"""
import pandas as pd

from scripts.clean import (
    CLEANED_PATH,
    QUARANTINED_PATH,
    main,
    partition,
    rule_flagged_fraud_contract,
    rule_no_duplicate_transactions,
    rule_no_negative_values,
    rule_origin_balance_consistency,
    rule_valid_transaction_type,
    run_rules,
)


def make_row(**overrides) -> dict:
    """A baseline row that passes every rule. Tests override only the fields
    relevant to the rule they're checking.
    """
    row = {
        "step": 1,
        "type": "TRANSFER",
        "amount": 100.0,
        "nameOrig": "C1",
        "oldbalanceOrg": 1000.0,
        "newbalanceOrig": 900.0,
        "nameDest": "C2",
        "oldbalanceDest": 500.0,
        "newbalanceDest": 600.0,
        "isFraud": 0,
        "isFlaggedFraud": 0,
    }
    row.update(overrides)
    return row


def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def test_baseline_row_passes_every_rule():
    df = make_df(make_row())
    assert run_rules(df) == []


# --- rule_valid_transaction_type ---------------------------------------


def test_valid_transaction_type_flags_unknown_type():
    df = make_df(make_row(type="WIRE"))
    assert rule_valid_transaction_type(df).tolist() == [True]


def test_valid_transaction_type_allows_known_types():
    df = make_df(make_row(type="PAYMENT"))
    assert rule_valid_transaction_type(df).tolist() == [False]


# --- rule_no_negative_values --------------------------------------------


def test_no_negative_values_flags_negative_amount():
    df = make_df(make_row(amount=-5.0))
    assert rule_no_negative_values(df).tolist() == [True]


def test_no_negative_values_flags_zero_amount():
    df = make_df(make_row(amount=0.0))
    assert rule_no_negative_values(df).tolist() == [True]


def test_no_negative_values_flags_negative_balance():
    df = make_df(make_row(oldbalanceDest=-1.0))
    assert rule_no_negative_values(df).tolist() == [True]


def test_no_negative_values_allows_positive_values():
    df = make_df(make_row())
    assert rule_no_negative_values(df).tolist() == [False]


# --- rule_flagged_fraud_contract ----------------------------------------


def test_flagged_fraud_contract_flags_wrong_type():
    df = make_df(make_row(isFlaggedFraud=1, type="PAYMENT", amount=300_000.0))
    assert rule_flagged_fraud_contract(df).tolist() == [True]


def test_flagged_fraud_contract_flags_amount_too_low():
    df = make_df(make_row(isFlaggedFraud=1, type="TRANSFER", amount=100_000.0))
    assert rule_flagged_fraud_contract(df).tolist() == [True]


def test_flagged_fraud_contract_allows_compliant_flag():
    df = make_df(make_row(isFlaggedFraud=1, type="TRANSFER", amount=250_000.0))
    assert rule_flagged_fraud_contract(df).tolist() == [False]


def test_flagged_fraud_contract_ignores_unflagged_rows():
    df = make_df(make_row(isFlaggedFraud=0, type="PAYMENT", amount=5.0))
    assert rule_flagged_fraud_contract(df).tolist() == [False]


# --- rule_origin_balance_consistency ------------------------------------


def test_origin_balance_consistency_flags_real_mismatch():
    df = make_df(
        make_row(
            type="TRANSFER", oldbalanceOrg=1000.0, amount=100.0, newbalanceOrig=850.0
        )
    )
    assert rule_origin_balance_consistency(df).tolist() == [True]


def test_origin_balance_consistency_ignores_untracked_balance():
    df = make_df(
        make_row(
            type="TRANSFER", oldbalanceOrg=0.0, amount=100.0, newbalanceOrig=0.0
        )
    )
    assert rule_origin_balance_consistency(df).tolist() == [False]


def test_origin_balance_consistency_ignores_other_transaction_types():
    df = make_df(
        make_row(
            type="PAYMENT", oldbalanceOrg=1000.0, amount=100.0, newbalanceOrig=850.0
        )
    )
    assert rule_origin_balance_consistency(df).tolist() == [False]


def test_origin_balance_consistency_allows_correct_math():
    df = make_df(
        make_row(
            type="CASH_OUT", oldbalanceOrg=1000.0, amount=100.0, newbalanceOrig=900.0
        )
    )
    assert rule_origin_balance_consistency(df).tolist() == [False]


# --- rule_no_duplicate_transactions -------------------------------------


def test_no_duplicate_transactions_flags_exact_duplicates():
    df = make_df(
        make_row(nameOrig="C1", nameDest="C2"),
        make_row(nameOrig="C1", nameDest="C2"),
    )
    assert rule_no_duplicate_transactions(df).tolist() == [True, True]


def test_no_duplicate_transactions_allows_distinct_rows():
    df = make_df(
        make_row(nameOrig="C1", nameDest="C2", amount=100.0),
        make_row(nameOrig="C1", nameDest="C2", amount=200.0),
    )
    assert rule_no_duplicate_transactions(df).tolist() == [False, False]


# --- run_rules aggregation -----------------------------------------------


def test_run_rules_reports_every_failing_rule():
    df = make_df(make_row(type="WIRE", amount=-5.0))  # breaks two rules at once
    failures = run_rules(df)
    names = {name for name, _count in failures}
    assert names == {"valid_transaction_type", "no_negative_values"}


# --- partition() ----------------------------------------------------------


def test_partition_separates_clean_and_quarantined_rows():
    df = make_df(
        make_row(nameOrig="good"),
        make_row(nameOrig="bad", type="WIRE"),
    )
    clean_rows, quarantined_rows = partition(df)

    assert list(clean_rows["nameOrig"]) == ["good"]
    assert list(quarantined_rows["nameOrig"]) == ["bad"]
    assert quarantined_rows["failed_rules"].tolist() == ["valid_transaction_type"]


def test_partition_lists_every_broken_rule_for_a_row():
    # This row breaks both valid_transaction_type AND no_negative_values.
    df = make_df(make_row(type="WIRE", amount=-5.0))
    _clean_rows, quarantined_rows = partition(df)

    failed = quarantined_rows["failed_rules"].iloc[0]
    assert "valid_transaction_type" in failed
    assert "no_negative_values" in failed


# --- main() integration: report vs strict mode ---------------------------


def test_main_report_mode_never_writes_output(tmp_path, monkeypatch):
    input_path = tmp_path / "input.csv"
    make_df(make_row(type="WIRE"), make_row()).to_csv(input_path, index=False)
    cleaned_path = tmp_path / "cleaned.csv"
    quarantined_path = tmp_path / "quarantined.csv"

    monkeypatch.setattr("scripts.clean.INPUT_PATH", str(input_path))
    monkeypatch.setattr("scripts.clean.CLEANED_PATH", str(cleaned_path))
    monkeypatch.setattr("scripts.clean.QUARANTINED_PATH", str(quarantined_path))

    main("report")

    assert not cleaned_path.exists()
    assert not quarantined_path.exists()


def test_main_strict_writes_both_files(tmp_path, monkeypatch):
    input_path = tmp_path / "input.csv"
    make_df(make_row(nameOrig="good"), make_row(nameOrig="bad", type="WIRE")).to_csv(
        input_path, index=False
    )
    cleaned_path = tmp_path / "cleaned.csv"
    quarantined_path = tmp_path / "quarantined.csv"

    monkeypatch.setattr("scripts.clean.INPUT_PATH", str(input_path))
    monkeypatch.setattr("scripts.clean.CLEANED_PATH", str(cleaned_path))
    monkeypatch.setattr("scripts.clean.QUARANTINED_PATH", str(quarantined_path))

    main("strict")

    cleaned = pd.read_csv(cleaned_path)
    quarantined = pd.read_csv(quarantined_path)
    assert list(cleaned["nameOrig"]) == ["good"]
    assert list(quarantined["nameOrig"]) == ["bad"]
    assert quarantined["failed_rules"].tolist() == ["valid_transaction_type"]