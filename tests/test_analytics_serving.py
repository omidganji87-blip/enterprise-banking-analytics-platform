from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src.analytics_serving import (
    ANALYTICS_VIEW_NAMES,
    build_analytics_serving_layer,
    validate_analytics_inputs,
)


def write_sample_gold_tables(
    base_path: Path,
) -> dict[str, Path]:
    """
    Create a small, valid Gold dimensional model for testing.
    """

    gold_path = base_path / "gold"

    gold_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    merchant_path = (
        gold_path / "dim_merchant.parquet"
    )

    date_path = (
        gold_path / "dim_date.parquet"
    )

    transaction_path = (
        gold_path / "fact_transaction.parquet"
    )

    dim_merchant_df = pd.DataFrame(
        {
            "merchant_key": [
                1,
                2,
            ],
            "merchant_id": [
                100,
                200,
            ],
            "merchant_city": [
                "Toronto",
                "Ottawa",
            ],
            "merchant_state": [
                "ON",
                "ON",
            ],
            "merchant_zip_code": [
                "M5V",
                "K1P",
            ],
            "merchant_category_code": [
                5411,
                5812,
            ],
        }
    )

    full_dates = pd.to_datetime(
        [
            "2024-01-01",
            "2024-01-02",
            "2024-01-03",
        ]
    )

    dim_date_df = pd.DataFrame(
        {
            "date_key": [
                20240101,
                20240102,
                20240103,
            ],
            "full_date": full_dates,
            "calendar_year": [
                2024,
                2024,
                2024,
            ],
            "calendar_quarter": [
                1,
                1,
                1,
            ],
            "calendar_month_number": [
                1,
                1,
                1,
            ],
            "calendar_month_name": [
                "January",
                "January",
                "January",
            ],
            "calendar_day_of_month": [
                1,
                2,
                3,
            ],
            "calendar_day_of_week_number": [
                1,
                2,
                3,
            ],
            "calendar_day_name": [
                "Monday",
                "Tuesday",
                "Wednesday",
            ],
            "is_weekend": [
                False,
                False,
                False,
            ],
        }
    )

    fact_transaction_df = pd.DataFrame(
        {
            "transaction_key": [
                1,
                2,
                3,
            ],
            "date_key": [
                20240101,
                20240103,
                20240103,
            ],
            "merchant_key": [
                1,
                2,
                2,
            ],
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
                "CHIP",
                "ONLINE",
                "ONLINE",
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
        }
    )

    dim_merchant_df.to_parquet(
        merchant_path,
        index=False,
    )

    dim_date_df.to_parquet(
        date_path,
        index=False,
    )

    fact_transaction_df.to_parquet(
        transaction_path,
        index=False,
    )

    return {
        "merchant_path": merchant_path,
        "date_path": date_path,
        "transaction_path": transaction_path,
    }


def test_validate_analytics_inputs_rejects_missing_files(
    tmp_path,
):
    """
    Analytics input validation should reject missing Gold files.
    """

    with pytest.raises(
        FileNotFoundError,
        match="Gold files are missing",
    ):
        validate_analytics_inputs(
            merchant_input_path=(
                tmp_path / "missing_merchant.parquet"
            ),
            date_input_path=(
                tmp_path / "missing_date.parquet"
            ),
            transaction_input_path=(
                tmp_path / "missing_fact.parquet"
            ),
        )


def test_build_analytics_serving_layer_success(
    tmp_path,
):
    """
    Verify that the analytics database and all expected SQL
    views are created from a valid Gold model.
    """

    gold_paths = write_sample_gold_tables(
        tmp_path
    )

    database_path = (
        tmp_path
        / "analytics"
        / "banking_analytics.duckdb"
    )

    result = build_analytics_serving_layer(
        merchant_input_path=gold_paths[
            "merchant_path"
        ],
        date_input_path=gold_paths[
            "date_path"
        ],
        transaction_input_path=gold_paths[
            "transaction_path"
        ],
        analytics_database_path=database_path,
    )

    assert result["status"] == "SUCCESS"
    assert database_path.exists()

    assert result["views_created"] == (
        ANALYTICS_VIEW_NAMES
    )

    validation = result["validation"]

    assert validation["is_valid"]
    assert validation["merchant_rows"] == 2
    assert validation["date_rows"] == 3
    assert validation["transaction_rows"] == 3
    assert validation["duplicate_merchant_keys"] == 0
    assert validation["duplicate_date_keys"] == 0
    assert validation["duplicate_transaction_keys"] == 0
    assert validation["invalid_merchant_foreign_keys"] == 0
    assert validation["invalid_date_foreign_keys"] == 0

    platform_kpis = result["platform_kpis"]

    assert platform_kpis["total_transactions"] == 3
    assert platform_kpis[
        "total_transaction_amount"
    ] == pytest.approx(81.25)

    assert platform_kpis[
        "average_transaction_amount"
    ] == pytest.approx(27.08)

    assert platform_kpis[
        "fraudulent_transactions"
    ] == 1

    assert platform_kpis[
        "fraud_transaction_rate_percent"
    ] == pytest.approx(33.33)

    # Reopen the database to prove that the production function
    # closed its write connection and persisted all views.
    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    try:
        available_views = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }

        assert set(
            ANALYTICS_VIEW_NAMES
        ).issubset(available_views)

        method_rows = connection.execute(
            """
            SELECT
                SUM(transaction_count)
            FROM vw_transaction_method_summary
            """
        ).fetchone()[0]

        annual_rows = connection.execute(
            """
            SELECT
                SUM(transaction_count)
            FROM vw_annual_transaction_summary
            """
        ).fetchone()[0]

        assert method_rows == 3
        assert annual_rows == 3

    finally:
        connection.close()


def test_build_analytics_serving_layer_rejects_invalid_fk(
    tmp_path,
):
    """
    Analytics validation should reject a fact table containing
    a merchant foreign key that is absent from dim_merchant.
    """

    gold_paths = write_sample_gold_tables(
        tmp_path
    )

    fact_df = pd.read_parquet(
        gold_paths["transaction_path"]
    )

    fact_df.loc[
        0,
        "merchant_key",
    ] = 999999

    fact_df.to_parquet(
        gold_paths["transaction_path"],
        index=False,
    )

    database_path = (
        tmp_path
        / "analytics"
        / "invalid_analytics.duckdb"
    )

    with pytest.raises(
        ValueError,
        match="Analytics serving-layer validation failed",
    ):
        build_analytics_serving_layer(
            merchant_input_path=gold_paths[
                "merchant_path"
            ],
            date_input_path=gold_paths[
                "date_path"
            ],
            transaction_input_path=gold_paths[
                "transaction_path"
            ],
            analytics_database_path=database_path,
        )

    # The failed function must still release its connection.
    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    connection.close()