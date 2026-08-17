from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.metadata_control import (
    append_control_record,
    calculate_file_sha256,
    file_already_processed,
    load_control_table,
)
from src.schema_validation import (
    validate_columns,
    validate_dtypes,
)


BRONZE_AUDIT_COLUMNS = [
    "_source_file_name",
    "_source_file_size_bytes",
    "_source_file_sha256",
    "_ingestion_timestamp_utc",
    "_pipeline_run_id",
]


def discover_landing_csv_files(
    landing_path: Path,
) -> list[Path]:
    """
    Discover every CSV file located directly in the Landing directory.

    Files are returned in deterministic alphabetical order.
    """

    landing_path = Path(
        landing_path
    )

    if not landing_path.exists():
        raise FileNotFoundError(
            "The Landing directory does not exist: "
            f"{landing_path}"
        )

    if not landing_path.is_dir():
        raise NotADirectoryError(
            "The supplied Landing path is not a directory: "
            f"{landing_path}"
        )

    csv_files = sorted(
        [
            file_path
            for file_path in landing_path.iterdir()
            if (
                file_path.is_file()
                and file_path.suffix.lower() == ".csv"
            )
        ],
        key=lambda file_path: (
            file_path.name.lower()
        ),
    )

    return csv_files


def load_existing_bronze(
    bronze_output_path: Path,
) -> pd.DataFrame:
    """
    Load the existing consolidated Bronze table.

    If the Bronze table does not exist, return an empty DataFrame.
    """

    bronze_output_path = Path(
        bronze_output_path
    )

    if not bronze_output_path.exists():
        return pd.DataFrame()

    return pd.read_parquet(
        bronze_output_path
    )


def append_to_bronze(
    new_bronze_df: pd.DataFrame,
    bronze_output_path: Path,
) -> int:
    """
    Append a newly ingested batch to the consolidated Bronze table.

    Existing Bronze history is preserved. The function returns the
    total number of rows stored in Bronze after the append.
    """

    bronze_output_path = Path(
        bronze_output_path
    )

    bronze_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing_bronze_df = load_existing_bronze(
        bronze_output_path
    )

    if existing_bronze_df.empty:
        consolidated_bronze_df = (
            new_bronze_df.copy()
        )
    else:
        consolidated_bronze_df = pd.concat(
            [
                existing_bronze_df,
                new_bronze_df,
            ],
            ignore_index=True,
            sort=False,
        )

    temporary_output_path = (
        bronze_output_path.parent
        / (
            bronze_output_path.name
            + ".temporary"
        )
    )

    consolidated_bronze_df.to_parquet(
        temporary_output_path,
        index=False,
    )

    temporary_output_path.replace(
        bronze_output_path
    )

    return len(
        consolidated_bronze_df
    )


def ingest_csv_to_bronze(
    source_file: Path,
    bronze_output_path: Path,
    control_table_path: Path,
    expected_columns: list[str],
    expected_dtypes: dict[str, str],
) -> dict:
    """
    Validate and incrementally ingest one CSV file into Bronze.

    Processing rules
    ----------------
    1. Calculate the file's SHA-256 content hash.
    2. Skip content that was already processed successfully.
    3. Validate source columns and data types.
    4. Add technical ingestion-audit columns.
    5. Append the new batch without deleting Bronze history.
    6. Record successful or failed processing in metadata.
    """

    source_file = Path(
        source_file
    )

    bronze_output_path = Path(
        bronze_output_path
    )

    control_table_path = Path(
        control_table_path
    )

    if not source_file.exists():
        raise FileNotFoundError(
            "The source CSV file does not exist: "
            f"{source_file}"
        )

    if not source_file.is_file():
        raise ValueError(
            "The supplied source path is not a file: "
            f"{source_file}"
        )

    if source_file.suffix.lower() != ".csv":
        raise ValueError(
            "Bronze ingestion accepts CSV files only: "
            f"{source_file}"
        )

    source_file_size_bytes = (
        source_file.stat().st_size
    )

    source_file_sha256 = (
        calculate_file_sha256(
            source_file
        )
    )

    control_df = load_control_table(
        control_table_path
    )

    already_processed = (
        file_already_processed(
            control_df=control_df,
            source_file_name=source_file.name,
            source_file_size_bytes=(
                source_file_size_bytes
            ),
            source_file_sha256=(
                source_file_sha256
            ),
        )
    )

    if already_processed:
        existing_bronze_df = (
            load_existing_bronze(
                bronze_output_path
            )
        )

        return {
            "status": "SKIPPED",
            "source_file_name": (
                source_file.name
            ),
            "source_file_size_bytes": (
                source_file_size_bytes
            ),
            "source_file_sha256": (
                source_file_sha256
            ),
            "reason": (
                "File content was already "
                "processed successfully"
            ),
            "rows_read": 0,
            "rows_written": 0,
            "bronze_total_rows": len(
                existing_bronze_df
            ),
            "bronze_output_path": str(
                bronze_output_path
            ),
        }

    pipeline_run_id = str(
        uuid4()
    )

    ingestion_timestamp = datetime.now(
        timezone.utc
    )

    rows_read = 0

    try:
        transactions_df = pd.read_csv(
            source_file
        )

        rows_read = len(
            transactions_df
        )

        column_result = validate_columns(
            actual_columns=(
                transactions_df
                .columns
                .tolist()
            ),
            expected_columns=(
                expected_columns
            ),
        )

        if not column_result["is_valid"]:
            raise ValueError(
                "Column validation failed: "
                f"{column_result}"
            )

        actual_dtypes = {
            column: str(dtype)
            for column, dtype
            in transactions_df.dtypes.items()
        }

        dtype_result = validate_dtypes(
            actual_dtypes=actual_dtypes,
            expected_dtypes=expected_dtypes,
        )

        if not dtype_result["is_valid"]:
            raise TypeError(
                "Data-type validation failed: "
                f"{dtype_result}"
            )

        new_bronze_df = (
            transactions_df.copy()
        )

        new_bronze_df[
            "_source_file_name"
        ] = source_file.name

        new_bronze_df[
            "_source_file_size_bytes"
        ] = source_file_size_bytes

        new_bronze_df[
            "_source_file_sha256"
        ] = source_file_sha256

        new_bronze_df[
            "_ingestion_timestamp_utc"
        ] = ingestion_timestamp

        new_bronze_df[
            "_pipeline_run_id"
        ] = pipeline_run_id

        bronze_total_rows = (
            append_to_bronze(
                new_bronze_df=(
                    new_bronze_df
                ),
                bronze_output_path=(
                    bronze_output_path
                ),
            )
        )

        control_record = {
            "source_file_name": (
                source_file.name
            ),
            "source_file_size_bytes": (
                source_file_size_bytes
            ),
            "source_file_sha256": (
                source_file_sha256
            ),
            "pipeline_run_id": (
                pipeline_run_id
            ),
            "status": "SUCCESS",
            "rows_read": rows_read,
            "rows_written": len(
                new_bronze_df
            ),
            "processed_at_utc": (
                ingestion_timestamp
            ),
            "error_message": pd.NA,
        }

        append_control_record(
            control_table_path=(
                control_table_path
            ),
            control_record=(
                control_record
            ),
        )

        return {
            "status": "SUCCESS",
            "source_file_name": (
                source_file.name
            ),
            "source_file_size_bytes": (
                source_file_size_bytes
            ),
            "source_file_sha256": (
                source_file_sha256
            ),
            "pipeline_run_id": (
                pipeline_run_id
            ),
            "rows_read": rows_read,
            "rows_written": len(
                new_bronze_df
            ),
            "bronze_total_rows": (
                bronze_total_rows
            ),
            "bronze_output_path": str(
                bronze_output_path
            ),
        }

    except Exception as error:
        failure_record = {
            "source_file_name": (
                source_file.name
            ),
            "source_file_size_bytes": (
                source_file_size_bytes
            ),
            "source_file_sha256": (
                source_file_sha256
            ),
            "pipeline_run_id": (
                pipeline_run_id
            ),
            "status": "FAILED",
            "rows_read": rows_read,
            "rows_written": 0,
            "processed_at_utc": (
                ingestion_timestamp
            ),
            "error_message": (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        }

        append_control_record(
            control_table_path=(
                control_table_path
            ),
            control_record=(
                failure_record
            ),
        )

        raise


def ingest_landing_csv_files(
    landing_path: Path,
    bronze_output_path: Path,
    control_table_path: Path,
    expected_columns: list[str],
    expected_dtypes: dict[str, str],
) -> dict:
    """
    Discover and ingest every CSV file in the Landing directory.

    A failure in one source file is isolated so the remaining files
    can still be evaluated and processed.
    """

    landing_path = Path(
        landing_path
    )

    bronze_output_path = Path(
        bronze_output_path
    )

    control_table_path = Path(
        control_table_path
    )

    source_files = (
        discover_landing_csv_files(
            landing_path
        )
    )

    if not source_files:
        raise FileNotFoundError(
            "No CSV files were found in the "
            f"Landing directory: {landing_path}"
        )

    file_results = []

    files_processed = 0
    files_skipped = 0
    files_failed = 0

    total_rows_read = 0
    total_rows_written = 0

    for source_file in source_files:
        try:
            file_result = (
                ingest_csv_to_bronze(
                    source_file=source_file,
                    bronze_output_path=(
                        bronze_output_path
                    ),
                    control_table_path=(
                        control_table_path
                    ),
                    expected_columns=(
                        expected_columns
                    ),
                    expected_dtypes=(
                        expected_dtypes
                    ),
                )
            )

        except Exception as error:
            files_failed += 1

            file_result = {
                "status": "FAILED",
                "source_file_name": (
                    source_file.name
                ),
                "rows_read": 0,
                "rows_written": 0,
                "error_message": (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            }

        else:
            if (
                file_result["status"]
                == "SUCCESS"
            ):
                files_processed += 1

            elif (
                file_result["status"]
                == "SKIPPED"
            ):
                files_skipped += 1

            total_rows_read += (
                file_result["rows_read"]
            )

            total_rows_written += (
                file_result["rows_written"]
            )

        file_results.append(
            file_result
        )

    existing_bronze_df = (
        load_existing_bronze(
            bronze_output_path
        )
    )

    if files_failed == 0:
        batch_status = "SUCCESS"

    elif (
        files_processed > 0
        or files_skipped > 0
    ):
        batch_status = "PARTIAL_SUCCESS"

    else:
        batch_status = "FAILED"

    return {
        "status": batch_status,
        "landing_path": str(
            landing_path
        ),
        "files_discovered": len(
            source_files
        ),
        "files_processed": (
            files_processed
        ),
        "files_skipped": (
            files_skipped
        ),
        "files_failed": (
            files_failed
        ),
        "rows_read": total_rows_read,
        "rows_written": (
            total_rows_written
        ),
        "bronze_total_rows": len(
            existing_bronze_df
        ),
        "bronze_output_path": str(
            bronze_output_path
        ),
        "file_results": file_results,
    }