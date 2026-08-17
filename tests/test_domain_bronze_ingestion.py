from pathlib import Path

import pandas as pd
import pytest

import src.domain_bronze_ingestion as domain_ingestion
from src.bronze_ingestion import BRONZE_AUDIT_COLUMNS
from src.domain_bronze_ingestion import (
    ingest_card_and_user_sources,
    ingest_registered_source_domain,
)
from src.metadata_control import load_control_table


def create_sample_card_df() -> pd.DataFrame:
    """Create representative card-source records."""

    return pd.DataFrame(
        {
            "User": [0, 1],
            "CARD INDEX": [0, 0],
            "Card Brand": ["Visa", "Mastercard"],
            "Card Type": ["Debit", "Credit"],
            "Card Number": [
                4532015112830366,
                5425233430109903,
            ],
            "Expires": ["12/2028", "08/2029"],
            "CVV": [123, 456],
            "Has Chip": ["YES", "YES"],
            "Cards Issued": [1, 2],
            "Credit Limit": ["$5,000", "$10,000"],
            "Acct Open Date": ["01/2020", "06/2018"],
            "Year PIN last Changed": [2024, 2023],
            "Card on Dark Web": ["No", "No"],
        }
    )


def create_sample_user_df() -> pd.DataFrame:
    """Create representative banking-user source records."""

    return pd.DataFrame(
        {
            "Person": ["Customer A", "Customer B"],
            "Current Age": [35, 48],
            "Retirement Age": [65, 67],
            "Birth Year": [1991, 1978],
            "Birth Month": [4, 9],
            "Gender": ["Female", "Male"],
            "Address": [
                "100 King Street",
                "200 Queen Street",
            ],
            "Apartment": [12.0, 8.0],
            "City": ["Toronto", "Ottawa"],
            "State": ["ON", "ON"],
            "Zipcode": [10001, 10002],
            "Latitude": [43.6532, 45.4215],
            "Longitude": [-79.3832, -75.6972],
            "Per Capita Income - Zipcode": [
                "$35,000",
                "$42,000",
            ],
            "Yearly Income - Person": [
                "$72,000",
                "$91,000",
            ],
            "Total Debt": [
                "$8,500",
                "$12,250",
            ],
            "FICO Score": [735, 790],
            "Num Credit Cards": [2, 3],
        }
    )


def build_domain_paths(
    tmp_path: Path,
    domain_name: str,
) -> dict[str, Path]:
    """Create isolated paths for one source domain."""

    return {
        "landing_path": (
            tmp_path
            / "landing"
            / domain_name
            / "incoming"
        ),
        "bronze_output_path": (
            tmp_path
            / "bronze"
            / f"{domain_name}_raw.parquet"
        ),
        "control_table_path": (
            tmp_path
            / "metadata"
            / f"{domain_name}_control.parquet"
        ),
    }


def write_source_csv(
    source_df: pd.DataFrame,
    landing_path: Path,
    file_name: str,
) -> Path:
    """Write one test source file to a Landing directory."""

    landing_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_file = (
        landing_path
        / file_name
    )

    source_df.to_csv(
        source_file,
        index=False,
    )

    return source_file


def test_card_domain_ingestion_is_successful_and_idempotent(
    tmp_path: Path,
) -> None:
    """A previously processed card file must be skipped safely."""

    paths = build_domain_paths(
        tmp_path,
        "cards",
    )

    write_source_csv(
        source_df=create_sample_card_df(),
        landing_path=paths["landing_path"],
        file_name="cards_batch_001.csv",
    )

    first_result = (
        ingest_registered_source_domain(
            domain_name="cards",
            **paths,
        )
    )

    second_result = (
        ingest_registered_source_domain(
            domain_name="cards",
            **paths,
        )
    )

    assert first_result["status"] == "SUCCESS"
    assert first_result["files_processed"] == 1
    assert first_result["files_skipped"] == 0
    assert first_result["rows_written"] == 2
    assert first_result["bronze_total_rows"] == 2

    assert second_result["status"] == "SUCCESS"
    assert second_result["files_processed"] == 0
    assert second_result["files_skipped"] == 1
    assert second_result["rows_written"] == 0
    assert second_result["bronze_total_rows"] == 2

    bronze_df = pd.read_parquet(
        paths["bronze_output_path"]
    )

    control_df = load_control_table(
        paths["control_table_path"]
    )

    assert len(bronze_df) == 2
    assert len(control_df) == 1

    assert set(
        BRONZE_AUDIT_COLUMNS
    ).issubset(
        bronze_df.columns
    )

    assert bronze_df[
        "_source_file_sha256"
    ].notna().all()

    assert (
        control_df.iloc[0]["status"]
        == "SUCCESS"
    )


def test_user_domain_ingestion_persists_source_and_audit_columns(
    tmp_path: Path,
) -> None:
    """User records and Bronze lineage columns must be persisted."""

    paths = build_domain_paths(
        tmp_path,
        "users",
    )

    source_file = write_source_csv(
        source_df=create_sample_user_df(),
        landing_path=paths["landing_path"],
        file_name="users_batch_001.csv",
    )

    result = (
        ingest_registered_source_domain(
            domain_name="users",
            **paths,
        )
    )

    bronze_df = pd.read_parquet(
        paths["bronze_output_path"]
    )

    control_df = load_control_table(
        paths["control_table_path"]
    )

    assert result["source_domain"] == "users"
    assert result["status"] == "SUCCESS"
    assert result["rows_read"] == 2
    assert result["rows_written"] == 2
    assert len(bronze_df) == 2

    assert set(
        create_sample_user_df().columns
    ).issubset(
        bronze_df.columns
    )

    assert set(
        BRONZE_AUDIT_COLUMNS
    ).issubset(
        bronze_df.columns
    )

    assert bronze_df[
        "_source_file_name"
    ].unique().tolist() == [
        source_file.name
    ]

    assert len(control_df) == 1

    assert (
        control_df.iloc[0]["rows_written"]
        == 2
    )


def test_unregistered_source_domain_is_rejected(
    tmp_path: Path,
) -> None:
    """Only domains with an approved source contract may run."""

    paths = build_domain_paths(
        tmp_path,
        "unknown",
    )

    with pytest.raises(
        ValueError,
        match="Unknown source domain",
    ):
        ingest_registered_source_domain(
            domain_name="loans",
            **paths,
        )


def test_card_and_user_aggregate_ingestion_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The aggregate job must process both registered domains."""

    card_paths = build_domain_paths(
        tmp_path,
        "cards",
    )

    user_paths = build_domain_paths(
        tmp_path,
        "users",
    )

    write_source_csv(
        source_df=create_sample_card_df(),
        landing_path=card_paths["landing_path"],
        file_name="cards_batch_001.csv",
    )

    write_source_csv(
        source_df=create_sample_user_df(),
        landing_path=user_paths["landing_path"],
        file_name="users_batch_001.csv",
    )

    monkeypatch.setattr(
        domain_ingestion,
        "DOMAIN_RUNTIME_CONFIG",
        {
            "cards": card_paths,
            "users": user_paths,
        },
    )

    result = ingest_card_and_user_sources()

    assert result["status"] == "SUCCESS"
    assert result["domains_discovered"] == 2
    assert result["domains_succeeded"] == 2
    assert result["domains_failed"] == 0
    assert result["files_processed"] == 2
    assert result["files_failed"] == 0
    assert result["rows_read"] == 4
    assert result["rows_written"] == 4

    assert set(
        result["domain_results"]
    ) == {
        "cards",
        "users",
    }

    assert card_paths[
        "bronze_output_path"
    ].exists()

    assert user_paths[
        "bronze_output_path"
    ].exists()


def test_domain_failure_does_not_block_a_valid_domain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One missing domain source must not erase another success."""

    card_paths = build_domain_paths(
        tmp_path,
        "cards",
    )

    user_paths = build_domain_paths(
        tmp_path,
        "users",
    )

    write_source_csv(
        source_df=create_sample_card_df(),
        landing_path=card_paths["landing_path"],
        file_name="cards_batch_001.csv",
    )

    monkeypatch.setattr(
        domain_ingestion,
        "DOMAIN_RUNTIME_CONFIG",
        {
            "cards": card_paths,
            "users": user_paths,
        },
    )

    result = ingest_card_and_user_sources()

    assert result["status"] == "PARTIAL_SUCCESS"
    assert result["domains_succeeded"] == 1
    assert result["domains_failed"] == 1
    assert result["files_processed"] == 1
    assert result["files_failed"] == 1
    assert result["rows_written"] == 2

    assert (
        result["domain_results"]["cards"]["status"]
        == "SUCCESS"
    )

    assert (
        result["domain_results"]["users"]["status"]
        == "FAILED"
    )

    assert "FileNotFoundError" in (
        result["domain_results"]["users"][
            "error_message"
        ]
    )

    assert card_paths[
        "bronze_output_path"
    ].exists()

    assert not user_paths[
        "bronze_output_path"
    ].exists()