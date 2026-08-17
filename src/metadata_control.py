from hashlib import sha256
from pathlib import Path

import pandas as pd


CONTROL_TABLE_COLUMNS = [
    "source_file_name",
    "source_file_size_bytes",
    "source_file_sha256",
    "pipeline_run_id",
    "status",
    "rows_read",
    "rows_written",
    "processed_at_utc",
    "error_message",
]


def create_empty_control_table() -> pd.DataFrame:
    """
    Create an empty metadata control table with the expected columns.
    """

    return pd.DataFrame(
        columns=CONTROL_TABLE_COLUMNS
    )


def normalize_control_table(
    control_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add any missing control-table columns.

    This makes the new control-table design compatible with metadata
    files created by earlier versions of the project.
    """

    normalized_df = control_df.copy()

    for column in CONTROL_TABLE_COLUMNS:
        if column not in normalized_df.columns:
            normalized_df[column] = pd.NA

    return normalized_df[
        CONTROL_TABLE_COLUMNS
    ]


def calculate_file_sha256(
    source_file: Path,
    chunk_size_bytes: int = 1024 * 1024,
) -> str:
    """
    Calculate the SHA-256 content hash of a file.

    The file is read in chunks so this function can safely process
    files that are too large to load entirely into memory.
    """

    source_file = Path(
        source_file
    )

    if not source_file.exists():
        raise FileNotFoundError(
            "Cannot calculate a hash because the file "
            f"does not exist: {source_file}"
        )

    if not source_file.is_file():
        raise ValueError(
            "The supplied source path is not a file: "
            f"{source_file}"
        )

    hash_calculator = sha256()

    with source_file.open("rb") as file_handle:
        while True:
            file_chunk = file_handle.read(
                chunk_size_bytes
            )

            if not file_chunk:
                break

            hash_calculator.update(
                file_chunk
            )

    return hash_calculator.hexdigest()


def load_control_table(
    control_table_path: Path,
) -> pd.DataFrame:
    """
    Load and normalize the pipeline metadata control table.

    If the table does not exist, return an empty DataFrame with
    the expected schema.
    """

    control_table_path = Path(
        control_table_path
    )

    if not control_table_path.exists():
        return create_empty_control_table()

    control_df = pd.read_parquet(
        control_table_path
    )

    return normalize_control_table(
        control_df
    )


def file_already_processed(
    control_df: pd.DataFrame,
    source_file_name: str,
    source_file_size_bytes: int,
    source_file_sha256: str | None = None,
) -> bool:
    """
    Determine whether a source file was already processed successfully.

    Modern metadata records are compared using SHA-256 content hashes.

    File name and size are used only for legacy records created before
    SHA-256 hashing was introduced.
    """

    if control_df.empty:
        return False

    normalized_df = normalize_control_table(
        control_df
    )

    successful_records_df = normalized_df[
        normalized_df["status"] == "SUCCESS"
    ].copy()

    if successful_records_df.empty:
        return False

    hash_values = successful_records_df[
        "source_file_sha256"
    ]

    modern_record_mask = (
        hash_values
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )

    modern_records_df = successful_records_df[
        modern_record_mask
    ]

    legacy_records_df = successful_records_df[
        ~modern_record_mask
    ]

    # Modern records must be compared using their content hash.
    if source_file_sha256:
        hash_matches = modern_records_df[
            modern_records_df[
                "source_file_sha256"
            ]
            == source_file_sha256
        ]

        if not hash_matches.empty:
            return True

    # Name-and-size comparison applies only to legacy records
    # that do not contain a SHA-256 hash.
    legacy_matches = legacy_records_df[
        (
            legacy_records_df[
                "source_file_name"
            ]
            == source_file_name
        )
        & (
            legacy_records_df[
                "source_file_size_bytes"
            ]
            == source_file_size_bytes
        )
    ]

    return not legacy_matches.empty


def append_control_record(
    control_table_path: Path,
    control_record: dict,
) -> None:
    """
    Append one normalized record to the metadata control table.
    """

    control_table_path = Path(
        control_table_path
    )

    control_table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    control_df = load_control_table(
        control_table_path
    )

    new_record_df = normalize_control_table(
        pd.DataFrame(
            [control_record]
        )
    )

    updated_control_df = pd.concat(
        [
            control_df,
            new_record_df,
        ],
        ignore_index=True,
    )

    updated_control_df = normalize_control_table(
        updated_control_df
    )

    updated_control_df.to_parquet(
        control_table_path,
        index=False,
    )