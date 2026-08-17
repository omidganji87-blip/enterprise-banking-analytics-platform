import pandas as pd
import pytest

from src.gold_data_model import (
    create_date_dimension,
    create_merchant_dimension,
    create_transaction_fact,
    validate_gold_model,
    validate_silver_source,
    build_gold_data_model,
)


# ------------------------------------------------------------
# Reusable test fixture
# ------------------------------------------------------------

@pytest.fixture
def sample_silver_df():
    """
    Create a small but representative Silver transaction dataset.

    The dataset contains:
    - Three transactions
    - Two merchants
    - Two transaction dates
    - A three-day calendar range
    """

    return pd.DataFrame(
        {
            "user_id": [
                1,
                1,
                2,
            ],
            "card_id": [
                10,
                10,
                20,
            ],
            "transaction_timestamp": pd.to_datetime(
                [
                    "2024-01-01 10:00:00",
                    "2024-01-03 12:30:00",
                    "2024-01-03 14:45:00",
                ]
            ),
            "transaction_amount": [
                25.50,
                40.00,
                15.75,
            ],
            "transaction_method": [
                "Chip",
                "Online",
                "Online",
            ],
            "merchant_id": [
                100,
                200,
                200,
            ],
            "merchant_city": [
                "Toronto",
                "Ottawa",
                "Ottawa",
            ],
            "merchant_state": [
                "ON",
                "ON",
                "ON",
            ],
            "merchant_zip_code": [
                "M5V",
                "K1P",
                "K1P",
            ],
            "merchant_category_code": [
                5411,
                5812,
                5812,
            ],
            "transaction_error": [
                None,
                "Timeout",
                None,
            ],
            "is_fraud": [
                False,
                False,
                True,
            ],
            "_source_file_name": [
                "sample.csv",
                "sample.csv",
                "sample.csv",
            ],
            "_ingestion_timestamp_utc": pd.to_datetime(
                [
                    "2024-02-01 00:00:00",
                    "2024-02-01 00:00:00",
                    "2024-02-01 00:00:00",
                ]
            ),
            "_pipeline_run_id": [
                "test-run-001",
                "test-run-001",
                "test-run-001",
            ],
            "_silver_processed_at_utc": pd.to_datetime(
                [
                    "2024-02-01 00:05:00",
                    "2024-02-01 00:05:00",
                    "2024-02-01 00:05:00",
                ]
            ),
        }
    )


# ------------------------------------------------------------
# Test Silver source validation
# ------------------------------------------------------------

def test_validate_silver_source_accepts_valid_schema(
    sample_silver_df,
):
    """
    A valid Silver DataFrame should pass source validation
    without raising an exception.
    """

    validate_silver_source(sample_silver_df)


def test_validate_silver_source_rejects_missing_columns(
    sample_silver_df,
):
    """
    Source validation should reject a Silver DataFrame when a
    required column is missing.
    """

    invalid_silver_df = sample_silver_df.drop(
        columns=["merchant_id"]
    )

    with pytest.raises(
        ValueError,
        match="required Silver columns are missing",
    ):
        validate_silver_source(invalid_silver_df)


# ------------------------------------------------------------
# Test Merchant dimension
# ------------------------------------------------------------

def test_create_merchant_dimension(sample_silver_df):
    """
    The Merchant dimension should contain one row per unique
    merchant business record.
    """

    dim_merchant_df = create_merchant_dimension(
        sample_silver_df
    )

    assert len(dim_merchant_df) == 2

    assert (
        dim_merchant_df["merchant_key"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        dim_merchant_df["merchant_key"]
        .isna()
        .sum()
        == 0
    )

    assert dim_merchant_df[
        "merchant_key"
    ].tolist() == [1, 2]

    assert set(
        dim_merchant_df["merchant_id"]
    ) == {100, 200}


# ------------------------------------------------------------
# Test Date dimension
# ------------------------------------------------------------

def test_create_date_dimension_builds_complete_calendar(
    sample_silver_df,
):
    """
    The Date dimension should include every calendar day between
    the minimum and maximum transaction dates.

    Transactions occur on January 1 and January 3, so January 2
    must also appear in the Date dimension.
    """

    dim_date_df = create_date_dimension(
        sample_silver_df
    )

    assert len(dim_date_df) == 3

    assert dim_date_df[
        "date_key"
    ].tolist() == [
        20240101,
        20240102,
        20240103,
    ]

    assert (
        dim_date_df["date_key"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        dim_date_df["date_key"]
        .isna()
        .sum()
        == 0
    )

    assert (
        dim_date_df["full_date"].min()
        == pd.Timestamp("2024-01-01")
    )

    assert (
        dim_date_df["full_date"].max()
        == pd.Timestamp("2024-01-03")
    )


# ------------------------------------------------------------
# Test Transaction fact table
# ------------------------------------------------------------

def test_create_transaction_fact_assigns_valid_keys(
    sample_silver_df,
):
    """
    The Transaction fact table should preserve the source grain
    and assign valid transaction, merchant, and date keys.
    """

    dim_merchant_df = create_merchant_dimension(
        sample_silver_df
    )

    fact_transaction_df = create_transaction_fact(
        silver_df=sample_silver_df,
        dim_merchant_df=dim_merchant_df,
    )

    assert len(fact_transaction_df) == 3

    assert fact_transaction_df[
        "transaction_key"
    ].tolist() == [1, 2, 3]

    assert (
        fact_transaction_df["transaction_key"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        fact_transaction_df["merchant_key"]
        .isna()
        .sum()
        == 0
    )

    assert (
        fact_transaction_df["date_key"]
        .isna()
        .sum()
        == 0
    )

    assert fact_transaction_df[
        "merchant_key"
    ].isin(
        dim_merchant_df["merchant_key"]
    ).all()

    assert fact_transaction_df[
        "date_key"
    ].tolist() == [
        20240101,
        20240103,
        20240103,
    ]


# ------------------------------------------------------------
# Test complete in-memory Gold validation
# ------------------------------------------------------------

def test_validate_gold_model_accepts_valid_model(
    sample_silver_df,
):
    """
    A correctly constructed Gold star schema should pass all
    primary-key, foreign-key, and row-count validations.
    """

    dim_merchant_df = create_merchant_dimension(
        sample_silver_df
    )

    dim_date_df = create_date_dimension(
        sample_silver_df
    )

    fact_transaction_df = create_transaction_fact(
        silver_df=sample_silver_df,
        dim_merchant_df=dim_merchant_df,
    )

    validation_result = validate_gold_model(
        dim_merchant_df=dim_merchant_df,
        dim_date_df=dim_date_df,
        fact_transaction_df=fact_transaction_df,
        expected_fact_rows=len(sample_silver_df),
    )

    assert validation_result["is_valid"]
    assert validation_result["actual_fact_rows"] == 3
    assert validation_result["duplicate_merchant_keys"] == 0
    assert validation_result["duplicate_date_keys"] == 0
    assert validation_result["duplicate_transaction_keys"] == 0
    assert validation_result["invalid_merchant_foreign_keys"] == 0
    assert validation_result["invalid_date_foreign_keys"] == 0


# ------------------------------------------------------------
# Test invalid foreign-key detection
# ------------------------------------------------------------

def test_validate_gold_model_rejects_invalid_foreign_key(
    sample_silver_df,
):
    """
    Gold validation should fail when a fact-table merchant key
    does not exist in the Merchant dimension.
    """

    dim_merchant_df = create_merchant_dimension(
        sample_silver_df
    )

    dim_date_df = create_date_dimension(
        sample_silver_df
    )

    fact_transaction_df = create_transaction_fact(
        silver_df=sample_silver_df,
        dim_merchant_df=dim_merchant_df,
    )

    invalid_fact_df = fact_transaction_df.copy()

    invalid_fact_df.loc[
        0,
        "merchant_key",
    ] = 999999

    with pytest.raises(
        ValueError,
        match="Gold model validation failed",
    ):
        validate_gold_model(
            dim_merchant_df=dim_merchant_df,
            dim_date_df=dim_date_df,
            fact_transaction_df=invalid_fact_df,
            expected_fact_rows=len(sample_silver_df),
        )


# ------------------------------------------------------------
# Test complete persisted Gold pipeline
# ------------------------------------------------------------

def test_build_gold_data_model_persists_valid_tables(
    sample_silver_df,
    tmp_path,
):
    """
    Integration test for the complete Gold pipeline.

    The test writes a temporary Silver file, builds the Gold
    tables, reloads them, and verifies the persisted results.
    """

    silver_input_path = (
        tmp_path
        / "silver"
        / "sample_silver.parquet"
    )

    merchant_output_path = (
        tmp_path
        / "gold"
        / "dim_merchant.parquet"
    )

    date_output_path = (
        tmp_path
        / "gold"
        / "dim_date.parquet"
    )

    transaction_output_path = (
        tmp_path
        / "gold"
        / "fact_transaction.parquet"
    )

    silver_input_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sample_silver_df.to_parquet(
        silver_input_path,
        index=False,
    )

    execution_result = build_gold_data_model(
        silver_input_path=silver_input_path,
        merchant_output_path=merchant_output_path,
        date_output_path=date_output_path,
        transaction_output_path=transaction_output_path,
    )

    assert execution_result["status"] == "SUCCESS"
    assert execution_result["silver_rows_read"] == 3
    assert execution_result["merchant_rows_written"] == 2
    assert execution_result["date_rows_written"] == 3
    assert execution_result["transaction_rows_written"] == 3

    assert execution_result[
        "in_memory_validation"
    ]["is_valid"]

    assert execution_result[
        "persisted_validation"
    ]["is_valid"]

    assert merchant_output_path.exists()
    assert date_output_path.exists()
    assert transaction_output_path.exists()

    persisted_merchant_df = pd.read_parquet(
        merchant_output_path
    )

    persisted_date_df = pd.read_parquet(
        date_output_path
    )

    persisted_transaction_df = pd.read_parquet(
        transaction_output_path
    )

    assert len(persisted_merchant_df) == 2
    assert len(persisted_date_df) == 3
    assert len(persisted_transaction_df) == 3