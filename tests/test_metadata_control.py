from pathlib import Path

import pandas as pd

from src.metadata_control import (
    CONTROL_TABLE_COLUMNS,
    append_control_record,
    calculate_file_sha256,
    file_already_processed,
    load_control_table,
)


def test_calculate_file_sha256_is_stable(
    tmp_path: Path,
) -> None:
    """
    The same file content must always produce the same hash.
    """

    source_file = (
        tmp_path
        / "transactions.csv"
    )

    source_file.write_text(
        "transaction_id,amount\n1,100.00\n",
        encoding="utf-8",
    )

    first_hash = calculate_file_sha256(
        source_file
    )

    second_hash = calculate_file_sha256(
        source_file
    )

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_calculate_file_sha256_changes_with_content(
    tmp_path: Path,
) -> None:
    """
    Changing the source content must change its hash.
    """

    source_file = (
        tmp_path
        / "transactions.csv"
    )

    source_file.write_text(
        "transaction_id,amount\n1,100.00\n",
        encoding="utf-8",
    )

    original_hash = calculate_file_sha256(
        source_file
    )

    source_file.write_text(
        "transaction_id,amount\n1,200.00\n",
        encoding="utf-8",
    )

    updated_hash = calculate_file_sha256(
        source_file
    )

    assert original_hash != updated_hash


def test_file_hash_detects_renamed_duplicate(
    tmp_path: Path,
) -> None:
    """
    Identical content must be considered processed even when
    the duplicate file has a different name.
    """

    original_file = (
        tmp_path
        / "batch_001.csv"
    )

    renamed_file = (
        tmp_path
        / "renamed_batch.csv"
    )

    file_content = (
        "transaction_id,amount\n"
        "1,100.00\n"
    )

    original_file.write_text(
        file_content,
        encoding="utf-8",
    )

    renamed_file.write_text(
        file_content,
        encoding="utf-8",
    )

    original_hash = calculate_file_sha256(
        original_file
    )

    renamed_hash = calculate_file_sha256(
        renamed_file
    )

    control_df = pd.DataFrame(
        [
            {
                "source_file_name": (
                    original_file.name
                ),
                "source_file_size_bytes": (
                    original_file.stat().st_size
                ),
                "source_file_sha256": (
                    original_hash
                ),
                "pipeline_run_id": "run-001",
                "status": "SUCCESS",
                "rows_read": 1,
                "rows_written": 1,
                "processed_at_utc": (
                    pd.Timestamp.now(
                        tz="UTC"
                    )
                ),
                "error_message": pd.NA,
            }
        ]
    )

    already_processed = (
        file_already_processed(
            control_df=control_df,
            source_file_name=(
                renamed_file.name
            ),
            source_file_size_bytes=(
                renamed_file.stat().st_size
            ),
            source_file_sha256=(
                renamed_hash
            ),
        )
    )

    assert already_processed is True


def test_legacy_file_name_and_size_fallback() -> None:
    """
    Old metadata records without hashes must remain usable.
    """

    legacy_control_df = pd.DataFrame(
        [
            {
                "source_file_name": (
                    "transactions.csv"
                ),
                "source_file_size_bytes": 500,
                "pipeline_run_id": (
                    "legacy-run"
                ),
                "status": "SUCCESS",
                "rows_read": 10,
                "rows_written": 10,
                "processed_at_utc": (
                    pd.Timestamp.now(
                        tz="UTC"
                    )
                ),
            }
        ]
    )

    already_processed = (
        file_already_processed(
            control_df=legacy_control_df,
            source_file_name=(
                "transactions.csv"
            ),
            source_file_size_bytes=500,
        )
    )

    assert already_processed is True


def test_load_control_table_migrates_old_schema(
    tmp_path: Path,
) -> None:
    """
    Loading an old control table must add all new columns.
    """

    control_table_path = (
        tmp_path
        / "file_processing_control.parquet"
    )

    legacy_control_df = pd.DataFrame(
        [
            {
                "source_file_name": (
                    "transactions.csv"
                ),
                "source_file_size_bytes": 500,
                "pipeline_run_id": (
                    "legacy-run"
                ),
                "status": "SUCCESS",
                "rows_read": 10,
                "rows_written": 10,
                "processed_at_utc": (
                    pd.Timestamp.now(
                        tz="UTC"
                    )
                ),
            }
        ]
    )

    legacy_control_df.to_parquet(
        control_table_path,
        index=False,
    )

    loaded_control_df = (
        load_control_table(
            control_table_path
        )
    )

    assert (
        loaded_control_df.columns.tolist()
        == CONTROL_TABLE_COLUMNS
    )

    assert (
        "source_file_sha256"
        in loaded_control_df.columns
    )

    assert (
        "error_message"
        in loaded_control_df.columns
    )


def test_append_control_record_persists_new_schema(
    tmp_path: Path,
) -> None:
    """
    A newly appended record must be persisted with the complete
    metadata-control schema.
    """

    control_table_path = (
        tmp_path
        / "metadata"
        / "file_processing_control.parquet"
    )

    control_record = {
        "source_file_name": (
            "batch_001.csv"
        ),
        "source_file_size_bytes": 250,
        "source_file_sha256": (
            "a" * 64
        ),
        "pipeline_run_id": "run-001",
        "status": "SUCCESS",
        "rows_read": 5,
        "rows_written": 5,
        "processed_at_utc": (
            pd.Timestamp.now(
                tz="UTC"
            )
        ),
        "error_message": pd.NA,
    }

    append_control_record(
        control_table_path=(
            control_table_path
        ),
        control_record=control_record,
    )

    persisted_control_df = (
        load_control_table(
            control_table_path
        )
    )

    assert control_table_path.exists()
    assert len(persisted_control_df) == 1

    assert (
        persisted_control_df
        .columns
        .tolist()
        == CONTROL_TABLE_COLUMNS
    )

    assert (
        persisted_control_df.iloc[0][
            "source_file_sha256"
        ]
        == "a" * 64
    )


def test_changed_content_with_same_name_and_size_is_not_skipped(
    tmp_path: Path,
) -> None:
    """
    A modern metadata record must use its SHA-256 hash.

    A file whose content changes must be processed again even when
    its name and byte size remain unchanged.
    """

    source_file = (
        tmp_path
        / "transactions.csv"
    )

    source_file.write_text(
        "transaction_id,amount\n1,100.00\n",
        encoding="utf-8",
    )

    original_size = (
        source_file.stat().st_size
    )

    original_hash = (
        calculate_file_sha256(
            source_file
        )
    )

    control_df = pd.DataFrame(
        [
            {
                "source_file_name": (
                    source_file.name
                ),
                "source_file_size_bytes": (
                    original_size
                ),
                "source_file_sha256": (
                    original_hash
                ),
                "pipeline_run_id": "run-001",
                "status": "SUCCESS",
                "rows_read": 1,
                "rows_written": 1,
                "processed_at_utc": (
                    pd.Timestamp.now(
                        tz="UTC"
                    )
                ),
                "error_message": pd.NA,
            }
        ]
    )

    # The replacement value has the same number of characters,
    # so the file retains the same byte size.
    source_file.write_text(
        "transaction_id,amount\n1,200.00\n",
        encoding="utf-8",
    )

    updated_size = (
        source_file.stat().st_size
    )

    updated_hash = (
        calculate_file_sha256(
            source_file
        )
    )

    assert updated_size == original_size
    assert updated_hash != original_hash

    already_processed = (
        file_already_processed(
            control_df=control_df,
            source_file_name=(
                source_file.name
            ),
            source_file_size_bytes=(
                updated_size
            ),
            source_file_sha256=(
                updated_hash
            ),
        )
    )

    assert already_processed is False