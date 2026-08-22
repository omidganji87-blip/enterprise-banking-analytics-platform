from pathlib import Path

import pandas as pd
import pytest

import pipelines.run_pipeline as pipeline


def create_first_transaction_batch() -> pd.DataFrame:
    """Create the first valid transaction batch."""

    return pd.DataFrame(
        {
            "User": [1, 1, 2],
            "Card": [10, 10, 20],
            "Year": [2024, 2024, 2024],
            "Month": [1, 1, 1],
            "Day": [1, 3, 3],
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
            "MCC": [5411, 5812, 5812],
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


def create_second_transaction_batch() -> pd.DataFrame:
    """Create a second unique transaction batch."""

    return pd.DataFrame(
        {
            "User": [3, 4],
            "Card": [30, 40],
            "Year": [2024, 2024],
            "Month": [1, 1],
            "Day": [4, 5],
            "Time": ["09:15", "16:30"],
            "Amount": ["$100.00", "$20.00"],
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
            "Merchant State": ["QC", "ON"],
            "Zip": [10003.0, 10001.0],
            "MCC": [5541, 5411],
            "Errors?": [
                None,
                "Technical Glitch",
            ],
            "Is Fraud?": ["No", "No"],
        }
    )


def create_card_batch() -> pd.DataFrame:
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
            "Credit Limit": [
                "$5,000",
                "$10,000",
            ],
            "Acct Open Date": [
                "01/2020",
                "06/2018",
            ],
            "Year PIN last Changed": [
                2024,
                2023,
            ],
            "Card on Dark Web": ["No", "No"],
        }
    )


def create_user_batch() -> pd.DataFrame:
    """Create representative banking-user records."""

    return pd.DataFrame(
        {
            "Person": [
                "Customer A",
                "Customer B",
            ],
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


def write_source_csv(
    source_df: pd.DataFrame,
    landing_path: Path,
    file_name: str,
) -> Path:
    """Write one CSV file to an isolated Landing path."""

    landing_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_file = landing_path / file_name

    source_df.to_csv(
        source_file,
        index=False,
    )

    return source_file


def configure_temporary_pipeline_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Path]:
    """Redirect every pipeline path to a temporary directory."""

    data_path = tmp_path / "data"

    paths = {
        "data_path": data_path,
        "landing_path": (
            data_path
            / "landing"
            / "transactions"
            / "incoming"
        ),
        "card_landing_path": (
            data_path
            / "landing"
            / "cards"
            / "incoming"
        ),
        "user_landing_path": (
            data_path
            / "landing"
            / "users"
            / "incoming"
        ),
        "bronze_path": data_path / "bronze",
        "silver_path": data_path / "silver",
        "quarantine_path": (
            data_path / "quarantine"
        ),
        "gold_path": data_path / "gold",
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
                / "credit_card_transactions_raw.parquet"
            ),
            "card_bronze_output_path": (
                paths["bronze_path"]
                / "credit_cards_raw.parquet"
            ),
            "user_bronze_output_path": (
                paths["bronze_path"]
                / "banking_users_raw.parquet"
            ),
            "control_table_path": (
                paths["metadata_path"]
                / "transaction_control.parquet"
            ),
            "card_control_table_path": (
                paths["metadata_path"]
                / "card_control.parquet"
            ),
            "user_control_table_path": (
                paths["metadata_path"]
                / "user_control.parquet"
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

    pipeline_path_map = {
        "DATA_PATH": "data_path",
        "LANDING_PATH": "landing_path",
        "BRONZE_PATH": "bronze_path",
        "SILVER_PATH": "silver_path",
        "QUARANTINE_PATH": "quarantine_path",
        "GOLD_PATH": "gold_path",
        "ANALYTICS_PATH": "analytics_path",
        "METADATA_PATH": "metadata_path",
        "BRONZE_OUTPUT_PATH": (
            "bronze_output_path"
        ),
        "CONTROL_TABLE_PATH": (
            "control_table_path"
        ),
        "SILVER_OUTPUT_PATH": (
            "silver_output_path"
        ),
        "QUARANTINE_OUTPUT_PATH": (
            "quarantine_output_path"
        ),
        "MERCHANT_OUTPUT_PATH": (
            "merchant_output_path"
        ),
        "DATE_OUTPUT_PATH": "date_output_path",
        "TRANSACTION_OUTPUT_PATH": (
            "transaction_output_path"
        ),
        "ANALYTICS_DATABASE_PATH": (
            "analytics_database_path"
        ),
    }

    for attribute_name, path_key in (
        pipeline_path_map.items()
    ):
        monkeypatch.setattr(
            pipeline,
            attribute_name,
            paths[path_key],
        )

    monkeypatch.setattr(
        pipeline.domain_bronze,
        "DOMAIN_RUNTIME_CONFIG",
        {
            "cards": {
                "landing_path": (
                    paths["card_landing_path"]
                ),
                "bronze_output_path": (
                    paths[
                        "card_bronze_output_path"
                    ]
                ),
                "control_table_path": (
                    paths[
                        "card_control_table_path"
                    ]
                ),
            },
            "users": {
                "landing_path": (
                    paths["user_landing_path"]
                ),
                "bronze_output_path": (
                    paths[
                        "user_bronze_output_path"
                    ]
                ),
                "control_table_path": (
                    paths[
                        "user_control_table_path"
                    ]
                ),
            },
        },
    )

    return paths


def write_required_domain_sources(
    paths: dict[str, Path],
) -> None:
    """Write the required card and user Landing files."""

    write_source_csv(
        source_df=create_card_batch(),
        landing_path=paths[
            "card_landing_path"
        ],
        file_name="cards_batch_001.csv",
    )

    write_source_csv(
        source_df=create_user_batch(),
        landing_path=paths[
            "user_landing_path"
        ],
        file_name="users_batch_001.csv",
    )


def test_run_enterprise_banking_pipeline_with_multiple_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify all source domains and a second idempotent run."""

    paths = configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    write_source_csv(
        source_df=(
            create_first_transaction_batch()
        ),
        landing_path=paths["landing_path"],
        file_name="batch_001.csv",
    )

    write_source_csv(
        source_df=(
            create_second_transaction_batch()
        ),
        landing_path=paths["landing_path"],
        file_name="batch_002.CSV",
    )

    write_required_domain_sources(paths)

    first_result = (
        pipeline
        .run_enterprise_banking_pipeline()
    )

    assert first_result["status"] == "SUCCESS"

    transaction_bronze = first_result[
        "bronze"
    ]

    assert transaction_bronze["status"] == "SUCCESS"
    assert transaction_bronze["files_discovered"] == 2
    assert transaction_bronze["files_processed"] == 2
    assert transaction_bronze["files_skipped"] == 0
    assert transaction_bronze["files_failed"] == 0
    assert transaction_bronze["rows_written"] == 5
    assert transaction_bronze["bronze_total_rows"] == 5

    domain_bronze = first_result[
        "domain_bronze"
    ]

    assert domain_bronze["status"] == "SUCCESS"
    assert domain_bronze["domains_discovered"] == 2
    assert domain_bronze["domains_succeeded"] == 2
    assert domain_bronze["domains_failed"] == 0
    assert domain_bronze["files_processed"] == 2
    assert domain_bronze["files_skipped"] == 0
    assert domain_bronze["rows_written"] == 4

    assert first_result["silver"][
        "bronze_rows_read"
    ] == 5

    assert first_result["silver"][
        "silver_rows_written"
    ] == 5

    assert first_result["silver"][
        "quarantine_rows_written"
    ] == 0

    assert first_result["silver"][
        "reconciliation_passed"
    ]

    assert first_result["gold"][
        "merchant_rows_written"
    ] == 3

    assert first_result["gold"][
        "date_rows_written"
    ] == 5

    assert first_result["gold"][
        "transaction_rows_written"
    ] == 5

    assert first_result["gold"][
        "persisted_validation"
    ]["is_valid"]

    assert first_result["analytics"][
        "status"
    ] == "SUCCESS"

    assert first_result["analytics"][
        "validation"
    ]["is_valid"]

    assert first_result["analytics"][
        "platform_kpis"
    ]["total_transactions"] == 5

    assert len(
        first_result["analytics"][
            "views_created"
        ]
    ) == 6

    assert len(
        pd.read_parquet(
            paths["bronze_output_path"]
        )
    ) == 5

    assert len(
        pd.read_parquet(
            paths["card_bronze_output_path"]
        )
    ) == 2

    assert len(
        pd.read_parquet(
            paths["user_bronze_output_path"]
        )
    ) == 2

    second_result = (
        pipeline
        .run_enterprise_banking_pipeline()
    )

    assert second_result["status"] == "SUCCESS"
    assert second_result["bronze"]["files_processed"] == 0
    assert second_result["bronze"]["files_skipped"] == 2
    assert second_result["bronze"]["rows_written"] == 0
    assert second_result["bronze"]["bronze_total_rows"] == 5

    assert second_result[
        "domain_bronze"
    ]["status"] == "SUCCESS"

    assert second_result[
        "domain_bronze"
    ]["files_processed"] == 0

    assert second_result[
        "domain_bronze"
    ]["files_skipped"] == 2

    assert second_result[
        "domain_bronze"
    ]["rows_written"] == 0

    assert second_result["silver"][
        "silver_rows_written"
    ] == 5

    assert second_result["gold"][
        "transaction_rows_written"
    ] == 5

    assert second_result["analytics"][
        "platform_kpis"
    ]["total_transactions"] == 5

    assert len(
        pd.read_parquet(
            paths["control_table_path"]
        )
    ) == 2

    assert len(
        pd.read_parquet(
            paths["card_control_table_path"]
        )
    ) == 1

    assert len(
        pd.read_parquet(
            paths["user_control_table_path"]
        )
    ) == 1


def test_pipeline_fails_when_landing_has_no_csv_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty transaction Landing area must stop the pipeline."""

    paths = configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        FileNotFoundError,
        match="No CSV files were found",
    ):
        pipeline.run_enterprise_banking_pipeline()

    assert not paths["bronze_output_path"].exists()
    assert not paths["card_bronze_output_path"].exists()
    assert not paths["user_bronze_output_path"].exists()
    assert not paths["silver_output_path"].exists()
    assert not paths["transaction_output_path"].exists()
    assert not paths["analytics_database_path"].exists()


def test_pipeline_blocks_downstream_publish_when_transaction_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed transaction file must block every later stage."""

    paths = configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    valid_source_df = (
        create_first_transaction_batch()
    )

    invalid_source_df = (
        create_second_transaction_batch()
        .drop(columns=["Is Fraud?"])
    )

    write_source_csv(
        source_df=valid_source_df,
        landing_path=paths["landing_path"],
        file_name="batch_001_valid.csv",
    )

    write_source_csv(
        source_df=invalid_source_df,
        landing_path=paths["landing_path"],
        file_name="batch_002_invalid.csv",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Transaction Bronze ingestion did not "
            "complete successfully"
        ),
    ):
        pipeline.run_enterprise_banking_pipeline()

    bronze_df = pd.read_parquet(
        paths["bronze_output_path"]
    )

    control_df = pd.read_parquet(
        paths["control_table_path"]
    )

    assert len(bronze_df) == 3
    assert len(control_df) == 2

    assert set(
        control_df["status"].tolist()
    ) == {"SUCCESS", "FAILED"}

    assert not paths["card_bronze_output_path"].exists()
    assert not paths["user_bronze_output_path"].exists()
    assert not paths["silver_output_path"].exists()
    assert not paths["transaction_output_path"].exists()
    assert not paths["analytics_database_path"].exists()


def test_pipeline_blocks_downstream_publish_when_domain_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing required domain must block Silver and later layers."""

    paths = configure_temporary_pipeline_paths(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    write_source_csv(
        source_df=(
            create_first_transaction_batch()
        ),
        landing_path=paths["landing_path"],
        file_name="batch_001.csv",
    )

    write_source_csv(
        source_df=create_card_batch(),
        landing_path=paths[
            "card_landing_path"
        ],
        file_name="cards_batch_001.csv",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Card and user Bronze ingestion did not "
            "complete successfully"
        ),
    ):
        pipeline.run_enterprise_banking_pipeline()

    assert paths["bronze_output_path"].exists()
    assert paths["card_bronze_output_path"].exists()
    assert not paths["user_bronze_output_path"].exists()

    assert not paths["silver_output_path"].exists()
    assert not paths["transaction_output_path"].exists()
    assert not paths["analytics_database_path"].exists()