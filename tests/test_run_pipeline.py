from pathlib import Path

import pandas as pd
import pytest

import pipelines.run_pipeline as pipeline


def create_first_source_batch() -> pd.DataFrame:
    """Create the first valid Landing transaction batch."""

    return pd.DataFrame(
        {
            "User": [
                1,
                1,
                2,
            ],
            "Card": [
                10,
                10,
                20,
            ],
            "Year": [
                2024,
                2024,
                2024,
            ],
            "Month": [
                1,
                1,
                1,
            ],
            "Day": [
                1,
                3,
                3,
            ],
            "Time": [
                "10:00",
                "12:30",
                "14:45",
            ],
            "Amount": [
                "$25.50",
                "$40.00",
                "$15.75",
            ],
            "Use Chip": [
                "Chip Transaction",
                "Online Transaction",
                "Online Transaction",
            ],
            "Merchant Name": [
                111111111111111111,
                222222222222222222,
                222222222222222222,
            ],
            "Merchant City": [
                "Toronto",
                "Ottawa",
                "Ottawa",
            ],
            "Merchant State": [
                "ON",
                "ON",
                "ON",
            ],
            "Zip": [
                10001.0,
                10002.0,
                10002.0,
            ],
            "MCC": [
                5411,
                5812,
                5812,
            ],
            "Errors?": [
                None,
                "Technical Glitch",
                None,
            ],
            "Is Fraud?": [
                "No",
                "No",
                "Yes",
            ],
        }
    )


def create_second_source_batch() -> pd.DataFrame:
    """Create a second unique and valid Landing batch."""

    return pd.DataFrame(
        {
            "User": [
                3,
                4,
            ],
            "Card": [
                30,
                40,
            ],
            "Year": [
                2024,
                2024,
            ],
            "Month": [
                1,
                1,
            ],
            "Day": [
                4,
                5,
            ],
            "Time": [
                "09:15",
                "16:30",
            ],
            "Amount": [
                "$100.00",
                "$20.00",
            ],
            "Use Chip": [
                "Swipe Transaction",
                "Chip Transaction",
            ],
            "Merchant Name": [
                333333333333333333,
                111111111111111111,
            ],
            "Merchant City": [
                "Montreal",
                "Toronto",
            ],
            "Merchant State": [
                "QC",
                "ON",
            ],
            "Zip": [
                10003.0,
                10001.0,
            ],
            "MCC": [
                5541,
                5411,
            ],
            # At least one string value is required so pandas reads
            # this source column with its expected object/string type.
            "Errors?": [
                None,
                "Technical Glitch",
            ],
            "Is Fraud?": [
                "No",
                "No",
            ],
        }
    )


def configure_temporary_pipeline_paths(
    tmp_path: Path,
    monkeypatch,
) -> dict[str, Path]:
    """
    Redirect every production pipeline path into an isolated
    temporary test directory.
    """

    data_path = (
        tmp_path / "data"
    )

    paths = {
        "data_path": data_path,
        "landing_path": (
            data_path / "landing"
        ),
        "bronze_path": (
            data_path / "bronze"
        ),
        "silver_path": (
            data_path / "silver"
        ),
        "quarantine_path": (
            data_path / "quarantine"
        ),
        "gold_path": (
            data_path / "gold"
        ),
        "analytics_path": (
            data_path / "analytics"
        ),
        "metadata_path": (
            data_path / "metadata"
        ),
    }

    paths.update(
        {
            "bronze_output_path": (
                paths["bronze_path"]
                / "credit_card_transactions_sample.parquet"
            ),
            "control_table_path": (
                paths["metadata_path"]
                / "file_processing_control.parquet"
            ),
            "silver_output_path": (
                paths["silver_path"]
                / "credit_card_transactions_clean.parquet"
            ),
            "quarantine_output_path": (
                paths["quarantine_path"]
                / "credit_card_transactions_quarantine.parquet"
            ),
            "merchant_output_path": (
                paths["gold_path"]
                / "dim_merchant.parquet"
            ),
            "date_output_path": (
                paths["gold_path"]
                / "dim_date.parquet"
            ),
            "transaction_output_path": (
                paths["gold_path"]
                / "fact_transaction.parquet"
            ),
            "analytics_database_path": (
                paths["analytics_path"]
                / "banking_analytics.duckdb"
            ),
        }
    )

    attribute_to_path_key = {
        "DATA_PATH": "data_path",
        "LANDING_PATH": "landing_path",
        "BRONZE_PATH": "bronze_path",
        "SILVER_PATH": "silver_path",
        "QUARANTINE_PATH": "quarantine_path",
        "GOLD_PATH": "gold_path",
        "ANALYTICS_PATH": "analytics_path",
        "METADATA_PATH": "metadata_path",
        "BRONZE_OUTPUT_PATH": "bronze_output_path",
        "CONTROL_TABLE_PATH": "control_table_path",
        "SILVER_OUTPUT_PATH": "silver_output_path",
        "QUARANTINE_OUTPUT_PATH": (
            "quarantine_output_path"
        ),
        "MERCHANT_OUTPUT_PATH": (
            "merchant_output_path"
        ),
        "DATE_OUTPUT_PATH": (
            "date_output_path"
        ),
        "TRANSACTION_OUTPUT_PATH": (
            "transaction_output_path"
        ),
        "ANALYTICS_DATABASE_PATH": (
            "analytics_database_path"
        ),
    }

    for (
        attribute_name,
        path_key,
    ) in attribute_to_path_key.items():
        monkeypatch.setattr(
            pipeline,
            attribute_name,
            paths[path_key],
        )

    return paths


def test_run_enterprise_banking_pipeline_with_multiple_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Verify multi-file processing and a second idempotent run.
    """

    paths = configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    paths["landing_path"].mkdir(
        parents=True,
        exist_ok=True,
    )

    first_source_file = (
        paths["landing_path"]
        / "batch_001.csv"
    )

    second_source_file = (
        paths["landing_path"]
        / "batch_002.CSV"
    )

    create_first_source_batch().to_csv(
        first_source_file,
        index=False,
    )

    create_second_source_batch().to_csv(
        second_source_file,
        index=False,
    )

    # ---------------------------------------------------------
    # First execution
    # ---------------------------------------------------------

    first_result = (
        pipeline.run_enterprise_banking_pipeline()
    )

    assert (
        first_result["status"]
        == "SUCCESS"
    )

    assert (
        first_result["bronze"]["status"]
        == "SUCCESS"
    )

    assert (
        first_result["bronze"][
            "files_discovered"
        ]
        == 2
    )

    assert (
        first_result["bronze"][
            "files_processed"
        ]
        == 2
    )

    assert (
        first_result["bronze"][
            "files_skipped"
        ]
        == 0
    )

    assert (
        first_result["bronze"][
            "files_failed"
        ]
        == 0
    )

    assert (
        first_result["bronze"][
            "rows_written"
        ]
        == 5
    )

    assert (
        first_result["bronze"][
            "bronze_total_rows"
        ]
        == 5
    )

    assert (
        first_result["silver"][
            "bronze_rows_read"
        ]
        == 5
    )

    assert (
        first_result["silver"][
            "silver_rows_written"
        ]
        == 5
    )

    assert (
        first_result["silver"][
            "quarantine_rows_written"
        ]
        == 0
    )

    assert first_result["silver"][
        "reconciliation_passed"
    ]

    assert (
        first_result["gold"][
            "merchant_rows_written"
        ]
        == 3
    )

    assert (
        first_result["gold"][
            "date_rows_written"
        ]
        == 5
    )

    assert (
        first_result["gold"][
            "transaction_rows_written"
        ]
        == 5
    )

    assert first_result["gold"][
        "persisted_validation"
    ]["is_valid"]

    analytics_result = (
        first_result["analytics"]
    )

    assert (
        analytics_result["status"]
        == "SUCCESS"
    )

    assert analytics_result[
        "validation"
    ]["is_valid"]

    assert (
        analytics_result[
            "validation"
        ]["transaction_rows"]
        == 5
    )

    assert (
        analytics_result[
            "platform_kpis"
        ]["total_transactions"]
        == 5
    )

    assert (
        analytics_result[
            "platform_kpis"
        ]["total_transaction_amount"]
        == 201.25
    )

    assert (
        analytics_result[
            "platform_kpis"
        ]["fraudulent_transactions"]
        == 1
    )

    expected_files = [
        paths["bronze_output_path"],
        paths["control_table_path"],
        paths["silver_output_path"],
        paths["quarantine_output_path"],
        paths["merchant_output_path"],
        paths["date_output_path"],
        paths["transaction_output_path"],
        paths["analytics_database_path"],
    ]

    assert all(
        file_path.exists()
        for file_path in expected_files
    )

    persisted_bronze_df = (
        pd.read_parquet(
            paths["bronze_output_path"]
        )
    )

    persisted_fact_df = (
        pd.read_parquet(
            paths["transaction_output_path"]
        )
    )

    persisted_date_df = (
        pd.read_parquet(
            paths["date_output_path"]
        )
    )

    persisted_merchant_df = (
        pd.read_parquet(
            paths["merchant_output_path"]
        )
    )

    persisted_control_df = (
        pd.read_parquet(
            paths["control_table_path"]
        )
    )

    assert len(persisted_bronze_df) == 5
    assert len(persisted_fact_df) == 5
    assert len(persisted_date_df) == 5
    assert len(persisted_merchant_df) == 3
    assert len(persisted_control_df) == 2

    assert persisted_control_df[
        "source_file_sha256"
    ].notna().all()

    assert persisted_date_df[
        "date_key"
    ].tolist() == [
        20240101,
        20240102,
        20240103,
        20240104,
        20240105,
    ]

    # ---------------------------------------------------------
    # Second execution — verify idempotency
    # ---------------------------------------------------------

    second_result = (
        pipeline.run_enterprise_banking_pipeline()
    )

    assert (
        second_result["status"]
        == "SUCCESS"
    )

    assert (
        second_result["bronze"][
            "files_discovered"
        ]
        == 2
    )

    assert (
        second_result["bronze"][
            "files_processed"
        ]
        == 0
    )

    assert (
        second_result["bronze"][
            "files_skipped"
        ]
        == 2
    )

    assert (
        second_result["bronze"][
            "files_failed"
        ]
        == 0
    )

    assert (
        second_result["bronze"][
            "rows_written"
        ]
        == 0
    )

    assert (
        second_result["bronze"][
            "bronze_total_rows"
        ]
        == 5
    )

    assert (
        second_result["silver"][
            "silver_rows_written"
        ]
        == 5
    )

    assert (
        second_result["gold"][
            "transaction_rows_written"
        ]
        == 5
    )

    assert (
        second_result["analytics"][
            "platform_kpis"
        ]["total_transactions"]
        == 5
    )

    control_df_after_second_run = (
        pd.read_parquet(
            paths["control_table_path"]
        )
    )

    bronze_df_after_second_run = (
        pd.read_parquet(
            paths["bronze_output_path"]
        )
    )

    assert (
        len(control_df_after_second_run)
        == 2
    )

    assert (
        len(bronze_df_after_second_run)
        == 5
    )


def test_pipeline_fails_when_landing_has_no_csv_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    The pipeline must fail clearly when Landing contains no CSV.
    """

    configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        FileNotFoundError,
        match="No CSV files were found",
    ):
        pipeline.run_enterprise_banking_pipeline()


def test_pipeline_blocks_downstream_publish_when_file_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A failed Landing file must prevent downstream publishing.
    """

    paths = configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    paths["landing_path"].mkdir(
        parents=True,
        exist_ok=True,
    )

    valid_source_file = (
        paths["landing_path"]
        / "batch_001_valid.csv"
    )

    invalid_source_file = (
        paths["landing_path"]
        / "batch_002_invalid.csv"
    )

    create_first_source_batch().to_csv(
        valid_source_file,
        index=False,
    )

    pd.DataFrame(
        {
            "unexpected_column": [
                "invalid",
            ]
        }
    ).to_csv(
        invalid_source_file,
        index=False,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Bronze ingestion did not "
            "complete successfully"
        ),
    ):
        pipeline.run_enterprise_banking_pipeline()

    assert paths[
        "bronze_output_path"
    ].exists()

    persisted_bronze_df = (
        pd.read_parquet(
            paths["bronze_output_path"]
        )
    )

    persisted_control_df = (
        pd.read_parquet(
            paths["control_table_path"]
        )
    )

    assert len(persisted_bronze_df) == 3
    assert len(persisted_control_df) == 2

    assert set(
        persisted_control_df[
            "status"
        ].tolist()
    ) == {
        "SUCCESS",
        "FAILED",
    }

    assert not paths[
        "silver_output_path"
    ].exists()

    assert not paths[
        "transaction_output_path"
    ].exists()

    assert not paths[
        "analytics_database_path"
    ].exists()