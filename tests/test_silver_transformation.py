from pathlib import Path

import pandas as pd

from src.silver_transformation import (
    transform_bronze_to_silver,
)


def create_valid_bronze_df() -> pd.DataFrame:
    """
    Create valid Bronze-style transaction records.
    """

    return pd.DataFrame(
        {
            "User": [0, 1],
            "Card": [0, 1],
            "Year": [2026, 2026],
            "Month": [8, 8],
            "Day": [1, 1],
            "Time": ["10:00", "11:30"],
            "Amount": ["$25.50", "$100.00"],
            "Use Chip": [
                "Chip Transaction",
                "Online Transaction",
            ],
            "Merchant Name": [
                111111111111111111,
                222222222222222222,
            ],
            "Merchant City": [
                "Toronto",
                "Vancouver",
            ],
            "Merchant State": [
                "ON",
                "BC",
            ],
            "Zip": [
                10001.0,
                None,
            ],
            "MCC": [
                5411,
                5812,
            ],
            "Errors?": [
                None,
                "Technical Glitch",
            ],
            "Is Fraud?": [
                "No",
                "Yes",
            ],
            "_source_file_name": [
                "transactions.csv",
                "transactions.csv",
            ],
            "_ingestion_timestamp_utc": pd.to_datetime(
                [
                    "2026-08-01T12:00:00Z",
                    "2026-08-01T12:00:00Z",
                ],
                utc=True,
            ),
            "_pipeline_run_id": [
                "run-001",
                "run-001",
            ],
        }
    )


def test_transform_bronze_to_silver_success(
    tmp_path: Path,
):
    """
    Verify that valid Bronze records are transformed into Silver.
    """

    bronze_input_path = (
        tmp_path / "bronze.parquet"
    )

    silver_output_path = (
        tmp_path / "silver.parquet"
    )

    quarantine_output_path = (
        tmp_path / "quarantine.parquet"
    )

    bronze_df = create_valid_bronze_df()

    bronze_df.to_parquet(
        bronze_input_path,
        index=False,
    )

    result = transform_bronze_to_silver(
        bronze_input_path=bronze_input_path,
        silver_output_path=silver_output_path,
        quarantine_output_path=quarantine_output_path,
    )

    assert result["status"] == "SUCCESS"
    assert result["bronze_rows_read"] == 2
    assert result["silver_rows_written"] == 2
    assert result["quarantine_rows_written"] == 0
    assert result["reconciliation_passed"] is True

    assert silver_output_path.exists()
    assert quarantine_output_path.exists()

    silver_df = pd.read_parquet(
        silver_output_path
    )

    quarantine_df = pd.read_parquet(
        quarantine_output_path
    )

    assert len(silver_df) == 2
    assert len(quarantine_df) == 0

    assert silver_df.loc[
        0,
        "transaction_amount",
    ] == 25.50

    assert silver_df.loc[
        0,
        "transaction_method",
    ] == "CHIP"

    assert silver_df.loc[
        1,
        "transaction_method",
    ] == "ONLINE"

    assert bool(
        silver_df.loc[0, "is_fraud"]
    ) is False

    assert bool(
        silver_df.loc[1, "is_fraud"]
    ) is True

    assert silver_df.loc[
        0,
        "merchant_zip_code",
    ] == "10001"

    assert pd.isna(
        silver_df.loc[
            1,
            "merchant_zip_code",
        ]
    )


def test_transform_quarantines_invalid_records(
    tmp_path: Path,
):
    """
    Verify that invalid records are quarantined while valid records
    continue to Silver.
    """

    bronze_input_path = (
        tmp_path / "bronze_invalid.parquet"
    )

    silver_output_path = (
        tmp_path / "silver_invalid.parquet"
    )

    quarantine_output_path = (
        tmp_path / "quarantine_invalid.parquet"
    )

    bronze_df = create_valid_bronze_df()

    invalid_row = bronze_df.iloc[0].copy()

    invalid_row["User"] = None
    invalid_row["Amount"] = "UNKNOWN"
    invalid_row["Time"] = "99:99"
    invalid_row["Is Fraud?"] = "Maybe"

    bronze_df = pd.concat(
        [
            bronze_df,
            invalid_row.to_frame().T,
        ],
        ignore_index=True,
    )

    bronze_df.to_parquet(
        bronze_input_path,
        index=False,
    )

    result = transform_bronze_to_silver(
        bronze_input_path=bronze_input_path,
        silver_output_path=silver_output_path,
        quarantine_output_path=quarantine_output_path,
    )

    assert result["status"] == "SUCCESS"
    assert result["bronze_rows_read"] == 3
    assert result["silver_rows_written"] == 2
    assert result["quarantine_rows_written"] == 1
    assert result["reconciliation_passed"] is True

    silver_df = pd.read_parquet(
        silver_output_path
    )

    quarantine_df = pd.read_parquet(
        quarantine_output_path
    )

    assert len(silver_df) == 2
    assert len(quarantine_df) == 1

    quarantine_reason = quarantine_df.loc[
        0,
        "quarantine_reason",
    ]

    assert "MISSING_USER_ID" in quarantine_reason
    assert "INVALID_AMOUNT" in quarantine_reason
    assert (
        "INVALID_TRANSACTION_TIMESTAMP"
        in quarantine_reason
    )
    assert (
        "INVALID_FRAUD_FLAG"
        in quarantine_reason
    )


def test_transform_fails_when_bronze_file_missing(
    tmp_path: Path,
):
    """
    Verify that a missing Bronze input raises FileNotFoundError.
    """

    bronze_input_path = (
        tmp_path / "missing_bronze.parquet"
    )

    silver_output_path = (
        tmp_path / "silver.parquet"
    )

    quarantine_output_path = (
        tmp_path / "quarantine.parquet"
    )

    try:
        transform_bronze_to_silver(
            bronze_input_path=bronze_input_path,
            silver_output_path=silver_output_path,
            quarantine_output_path=quarantine_output_path,
        )

        assert False

    except FileNotFoundError:
        assert True