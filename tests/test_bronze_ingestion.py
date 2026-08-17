from pathlib import Path

import pandas as pd

from src.bronze_ingestion import (
    BRONZE_AUDIT_COLUMNS,
    ingest_csv_to_bronze,
    ingest_landing_csv_files,
)
from src.metadata_control import (
    load_control_table,
)


EXPECTED_COLUMNS = [
    "User",
    "Card",
    "Year",
    "Month",
    "Day",
    "Time",
    "Amount",
    "Use Chip",
    "Merchant Name",
    "Merchant City",
    "Merchant State",
    "Zip",
    "MCC",
    "Errors?",
    "Is Fraud?",
]


EXPECTED_DTYPES = {
    "User": "int64",
    "Card": "int64",
    "Year": "int64",
    "Month": "int64",
    "Day": "int64",
    "Time": "str",
    "Amount": "str",
    "Use Chip": "str",
    "Merchant Name": "int64",
    "Merchant City": "str",
    "Merchant State": "str",
    "Zip": "float64",
    "MCC": "int64",
    "Errors?": "str",
    "Is Fraud?": "str",
}


def create_sample_transaction_df(
    user_id: int = 0,
    first_amount: str = "$25.00",
    first_day: int = 1,
) -> pd.DataFrame:
    """
    Create a small source-style transaction DataFrame.
    """

    return pd.DataFrame(
        {
            "User": [
                user_id,
                user_id,
            ],
            "Card": [
                0,
                0,
            ],
            "Year": [
                2026,
                2026,
            ],
            "Month": [
                8,
                8,
            ],
            "Day": [
                first_day,
                first_day,
            ],
            "Time": [
                "10:00",
                "10:05",
            ],
            "Amount": [
                first_amount,
                "$40.50",
            ],
            "Use Chip": [
                "Chip Transaction",
                "Swipe Transaction",
            ],
            "Merchant Name": [
                111111111111111111,
                222222222222222222,
            ],
            "Merchant City": [
                "Toronto",
                "Toronto",
            ],
            "Merchant State": [
                "ON",
                "ON",
            ],
            "Zip": [
                10001.0,
                10002.0,
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
                "No",
            ],
        }
    )


def test_ingest_csv_to_bronze_success_and_skip(
    tmp_path: Path,
) -> None:
    """
    Verify successful ingestion, audit columns, metadata, and
    idempotent duplicate skipping.
    """

    source_file = (
        tmp_path
        / "transactions.csv"
    )

    bronze_output_path = (
        tmp_path
        / "transactions_bronze.parquet"
    )

    control_table_path = (
        tmp_path
        / "file_processing_control.parquet"
    )

    sample_df = (
        create_sample_transaction_df()
    )

    sample_df.to_csv(
        source_file,
        index=False,
    )

    first_result = ingest_csv_to_bronze(
        source_file=source_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    assert (
        first_result["status"]
        == "SUCCESS"
    )

    assert (
        first_result["rows_read"]
        == 2
    )

    assert (
        first_result["rows_written"]
        == 2
    )

    assert (
        first_result["bronze_total_rows"]
        == 2
    )

    assert bronze_output_path.exists()
    assert control_table_path.exists()

    bronze_df = pd.read_parquet(
        bronze_output_path
    )

    assert len(bronze_df) == 2

    for audit_column in (
        BRONZE_AUDIT_COLUMNS
    ):
        assert audit_column in bronze_df.columns

        assert bronze_df[
            audit_column
        ].notna().all()

    control_df = load_control_table(
        control_table_path
    )

    assert len(control_df) == 1

    assert (
        control_df.iloc[0]["status"]
        == "SUCCESS"
    )

    assert (
        control_df.iloc[0]["rows_read"]
        == 2
    )

    assert (
        control_df.iloc[0]["rows_written"]
        == 2
    )

    assert (
        isinstance(
            control_df.iloc[0][
                "source_file_sha256"
            ],
            str,
        )
    )

    assert (
        len(
            control_df.iloc[0][
                "source_file_sha256"
            ]
        )
        == 64
    )

    second_result = ingest_csv_to_bronze(
        source_file=source_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    assert (
        second_result["status"]
        == "SKIPPED"
    )

    assert (
        second_result["rows_read"]
        == 0
    )

    assert (
        second_result["rows_written"]
        == 0
    )

    assert (
        second_result["bronze_total_rows"]
        == 2
    )

    control_df_after_second_run = (
        load_control_table(
            control_table_path
        )
    )

    assert (
        len(
            control_df_after_second_run
        )
        == 1
    )


def test_second_new_file_is_appended_without_losing_history(
    tmp_path: Path,
) -> None:
    """
    A second unique file must be appended while retaining the
    rows previously stored in Bronze.
    """

    first_file = (
        tmp_path
        / "batch_001.csv"
    )

    second_file = (
        tmp_path
        / "batch_002.csv"
    )

    bronze_output_path = (
        tmp_path
        / "transactions_bronze.parquet"
    )

    control_table_path = (
        tmp_path
        / "file_processing_control.parquet"
    )

    create_sample_transaction_df(
        user_id=1,
        first_day=1,
    ).to_csv(
        first_file,
        index=False,
    )

    create_sample_transaction_df(
        user_id=2,
        first_day=2,
    ).to_csv(
        second_file,
        index=False,
    )

    first_result = ingest_csv_to_bronze(
        source_file=first_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    second_result = ingest_csv_to_bronze(
        source_file=second_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    assert (
        first_result["bronze_total_rows"]
        == 2
    )

    assert (
        second_result["bronze_total_rows"]
        == 4
    )

    bronze_df = pd.read_parquet(
        bronze_output_path
    )

    assert len(bronze_df) == 4

    assert set(
        bronze_df[
            "_source_file_name"
        ].unique()
    ) == {
        "batch_001.csv",
        "batch_002.csv",
    }

    control_df = load_control_table(
        control_table_path
    )

    assert len(control_df) == 2

    assert (
        control_df["status"]
        .eq("SUCCESS")
        .all()
    )


def test_renamed_duplicate_is_skipped_using_hash(
    tmp_path: Path,
) -> None:
    """
    Renaming a previously processed file must not duplicate its
    contents in Bronze.
    """

    original_file = (
        tmp_path
        / "batch_001.csv"
    )

    renamed_file = (
        tmp_path
        / "renamed_batch.csv"
    )

    bronze_output_path = (
        tmp_path
        / "transactions_bronze.parquet"
    )

    control_table_path = (
        tmp_path
        / "file_processing_control.parquet"
    )

    sample_df = (
        create_sample_transaction_df()
    )

    sample_df.to_csv(
        original_file,
        index=False,
    )

    sample_df.to_csv(
        renamed_file,
        index=False,
    )

    first_result = ingest_csv_to_bronze(
        source_file=original_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    renamed_result = ingest_csv_to_bronze(
        source_file=renamed_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    assert (
        first_result["status"]
        == "SUCCESS"
    )

    assert (
        renamed_result["status"]
        == "SKIPPED"
    )

    bronze_df = pd.read_parquet(
        bronze_output_path
    )

    assert len(bronze_df) == 2

    control_df = load_control_table(
        control_table_path
    )

    assert len(control_df) == 1


def test_changed_file_with_same_name_and_size_is_appended(
    tmp_path: Path,
) -> None:
    """
    A file with changed content must be processed again even if its
    name and byte size remain unchanged.
    """

    source_file = (
        tmp_path
        / "transactions.csv"
    )

    bronze_output_path = (
        tmp_path
        / "transactions_bronze.parquet"
    )

    control_table_path = (
        tmp_path
        / "file_processing_control.parquet"
    )

    original_df = (
        create_sample_transaction_df(
            first_amount="$25.00",
        )
    )

    original_df.to_csv(
        source_file,
        index=False,
    )

    original_size = (
        source_file.stat().st_size
    )

    first_result = ingest_csv_to_bronze(
        source_file=source_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    updated_df = (
        create_sample_transaction_df(
            first_amount="$35.00",
        )
    )

    updated_df.to_csv(
        source_file,
        index=False,
    )

    updated_size = (
        source_file.stat().st_size
    )

    second_result = ingest_csv_to_bronze(
        source_file=source_file,
        bronze_output_path=(
            bronze_output_path
        ),
        control_table_path=(
            control_table_path
        ),
        expected_columns=EXPECTED_COLUMNS,
        expected_dtypes=EXPECTED_DTYPES,
    )

    assert updated_size == original_size

    assert (
        first_result[
            "source_file_sha256"
        ]
        != second_result[
            "source_file_sha256"
        ]
    )

    assert (
        second_result["status"]
        == "SUCCESS"
    )

    assert (
        second_result["bronze_total_rows"]
        == 4
    )

    bronze_df = pd.read_parquet(
        bronze_output_path
    )

    assert len(bronze_df) == 4

    control_df = load_control_table(
        control_table_path
    )

    assert len(control_df) == 2


def test_ingest_landing_csv_files_processes_all_files(
    tmp_path: Path,
) -> None:
    """
    The Landing ingestion function must discover all CSV files,
    process unique content, and skip everything on the second run.
    """

    landing_path = (
        tmp_path
        / "landing"
    )

    landing_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    bronze_output_path = (
        tmp_path
        / "bronze"
        / "transactions_bronze.parquet"
    )

    control_table_path = (
        tmp_path
        / "metadata"
        / "file_processing_control.parquet"
    )

    first_file = (
        landing_path
        / "batch_001.csv"
    )

    second_file = (
        landing_path
        / "batch_002.CSV"
    )

    create_sample_transaction_df(
        user_id=1,
        first_day=1,
    ).to_csv(
        first_file,
        index=False,
    )

    create_sample_transaction_df(
        user_id=2,
        first_day=2,
    ).to_csv(
        second_file,
        index=False,
    )

    first_batch_result = (
        ingest_landing_csv_files(
            landing_path=landing_path,
            bronze_output_path=(
                bronze_output_path
            ),
            control_table_path=(
                control_table_path
            ),
            expected_columns=(
                EXPECTED_COLUMNS
            ),
            expected_dtypes=(
                EXPECTED_DTYPES
            ),
        )
    )

    assert (
        first_batch_result["status"]
        == "SUCCESS"
    )

    assert (
        first_batch_result[
            "files_discovered"
        ]
        == 2
    )

    assert (
        first_batch_result[
            "files_processed"
        ]
        == 2
    )

    assert (
        first_batch_result[
            "files_skipped"
        ]
        == 0
    )

    assert (
        first_batch_result[
            "files_failed"
        ]
        == 0
    )

    assert (
        first_batch_result[
            "rows_written"
        ]
        == 4
    )

    assert (
        first_batch_result[
            "bronze_total_rows"
        ]
        == 4
    )

    second_batch_result = (
        ingest_landing_csv_files(
            landing_path=landing_path,
            bronze_output_path=(
                bronze_output_path
            ),
            control_table_path=(
                control_table_path
            ),
            expected_columns=(
                EXPECTED_COLUMNS
            ),
            expected_dtypes=(
                EXPECTED_DTYPES
            ),
        )
    )

    assert (
        second_batch_result["status"]
        == "SUCCESS"
    )

    assert (
        second_batch_result[
            "files_processed"
        ]
        == 0
    )

    assert (
        second_batch_result[
            "files_skipped"
        ]
        == 2
    )

    assert (
        second_batch_result[
            "files_failed"
        ]
        == 0
    )

    assert (
        second_batch_result[
            "rows_written"
        ]
        == 0
    )

    assert (
        second_batch_result[
            "bronze_total_rows"
        ]
        == 4
    )

    bronze_df = pd.read_parquet(
        bronze_output_path
    )

    assert len(bronze_df) == 4

    control_df = load_control_table(
        control_table_path
    )

    assert len(control_df) == 2