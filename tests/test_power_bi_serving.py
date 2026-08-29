from pathlib import Path

import pandas as pd
import pytest

from src.power_bi_serving import (
    DIM_DATE_ANALYTICS_COLUMNS,
    DIM_MERCHANT_ANALYTICS_COLUMNS,
    FACT_TRANSACTION_ANALYTICS_COLUMNS,
    build_power_bi_frames,
    build_power_bi_serving_layer,
    validate_power_bi_inputs,
)


def create_sample_gold_frames() -> dict[str, pd.DataFrame]:
    """Create a compact valid Gold star schema for testing."""

    merchant_df = pd.DataFrame(
        {
            "merchant_key": [1, 2],
            "merchant_id": [100, 200],
            "merchant_city": [
                "Toronto",
                "Ottawa",
            ],
            "merchant_state": ["ON", "ON"],
            "merchant_zip_code": [
                "M5V",
                "K1P",
            ],
            "merchant_category_code": [
                5411,
                5812,
            ],
            "source_only_column": ["A", "B"],
        }
    )

    date_df = pd.DataFrame(
        {
            "date_key": [
                20240131,
                20240201,
            ],
            "full_date": pd.to_datetime(
                [
                    "2024-01-31",
                    "2024-02-01",
                ]
            ),
            "calendar_year": [2024, 2024],
            "calendar_quarter": [1, 1],
            "calendar_month_number": [1, 2],
            "calendar_month_name": [
                "January",
                "February",
            ],
            "calendar_day_of_month": [31, 1],
            "calendar_day_of_week_number": [
                3,
                4,
            ],
            "calendar_day_name": [
                "Wednesday",
                "Thursday",
            ],
            "is_weekend": [False, False],
            "source_only_column": ["A", "B"],
        }
    )

    transaction_df = pd.DataFrame(
        {
            "transaction_key": [1, 2, 3],
            "date_key": [
                20240131,
                20240201,
                20240201,
            ],
            "merchant_key": [1, 2, 2],
            "card_id": [10, 20, 20],
            "transaction_timestamp": (
                pd.to_datetime(
                    [
                        "2024-01-31 09:15:00",
                        "2024-02-01 10:30:00",
                        "2024-02-01 12:45:00",
                    ]
                )
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
            "transaction_error": [
                "NO_ERROR",
                "Technical Glitch",
                None,
            ],
            "is_fraud": [False, False, True],
            "source_only_column": ["A", "B", "C"],
        }
    )

    return {
        "merchant": merchant_df,
        "date": date_df,
        "transaction": transaction_df,
    }


def write_sample_gold_frames(
    base_path: Path,
) -> dict[str, Path]:
    """Persist sample Gold inputs for an end-to-end test."""

    source_frames = create_sample_gold_frames()
    gold_path = base_path / "gold"
    gold_path.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "merchant": gold_path / "dim_merchant.parquet",
        "date": gold_path / "dim_date.parquet",
        "transaction": (
            gold_path / "fact_transaction.parquet"
        ),
    }

    for table_name, dataframe in (
        source_frames.items()
    ):
        dataframe.to_parquet(
            output_paths[table_name],
            index=False,
        )

    return output_paths


def test_validate_power_bi_inputs_rejects_missing_files(
    tmp_path: Path,
) -> None:
    """Missing Gold publications must stop BI publication."""

    with pytest.raises(
        FileNotFoundError,
        match="Gold files are missing",
    ):
        validate_power_bi_inputs(
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


def test_build_power_bi_frames_enforces_contracts() -> None:
    """Serving frames should expose only the BI contract."""

    source_frames = create_sample_gold_frames()

    serving_frames = build_power_bi_frames(
        dim_merchant_df=source_frames["merchant"],
        dim_date_df=source_frames["date"],
        fact_transaction_df=(
            source_frames["transaction"]
        ),
    )

    assert serving_frames["merchant"].columns.tolist() == (
        DIM_MERCHANT_ANALYTICS_COLUMNS
    )

    assert serving_frames["date"].columns.tolist() == (
        DIM_DATE_ANALYTICS_COLUMNS
        + [
            "calendar_year_month",
            "calendar_year_month_sort",
        ]
    )

    assert serving_frames[
        "transaction"
    ].columns.tolist() == (
        FACT_TRANSACTION_ANALYTICS_COLUMNS
        + ["has_error"]
    )

    assert serving_frames["date"][
        "calendar_year_month"
    ].tolist() == ["2024-01", "2024-02"]

    assert serving_frames["date"][
        "calendar_year_month_sort"
    ].tolist() == [202401, 202402]

    assert serving_frames["merchant"][
        "merchant_id_text"
    ].tolist() == ["100", "200"]

    assert serving_frames["merchant"][
        "merchant_display_label"
    ].tolist() == ["MRC-000001", "MRC-000002"]

    assert serving_frames["transaction"][
        "has_error"
    ].tolist() == [False, True, False]


def test_merchant_identifiers_are_power_bi_safe() -> None:
    """Large source IDs must survive the BI boundary without rounding."""

    source_frames = create_sample_gold_frames()
    source_frames["merchant"]["merchant_id"] = pd.Series(
        [
            -8566951830324093739,
            5763106017265140261,
        ],
        dtype="Int64",
    )

    serving_frames = build_power_bi_frames(
        dim_merchant_df=source_frames["merchant"],
        dim_date_df=source_frames["date"],
        fact_transaction_df=(
            source_frames["transaction"]
        ),
    )

    assert serving_frames["merchant"][
        "merchant_id_text"
    ].tolist() == [
        "-8566951830324093739",
        "5763106017265140261",
    ]

    assert serving_frames["merchant"][
        "merchant_display_label"
    ].is_unique


def test_build_power_bi_frames_rejects_missing_columns() -> None:
    """A Gold schema change must fail before publication."""

    source_frames = create_sample_gold_frames()
    invalid_fact_df = source_frames[
        "transaction"
    ].drop(columns=["transaction_method"])

    with pytest.raises(
        ValueError,
        match="transaction_method",
    ):
        build_power_bi_frames(
            dim_merchant_df=(
                source_frames["merchant"]
            ),
            dim_date_df=source_frames["date"],
            fact_transaction_df=invalid_fact_df,
        )


def test_build_power_bi_serving_layer_success(
    tmp_path: Path,
) -> None:
    """The BI layer should persist and reload an exact model."""

    input_paths = write_sample_gold_frames(
        tmp_path
    )
    output_directory = tmp_path / "analytics"

    result = build_power_bi_serving_layer(
        merchant_input_path=input_paths["merchant"],
        date_input_path=input_paths["date"],
        transaction_input_path=(
            input_paths["transaction"]
        ),
        output_directory=output_directory,
    )

    assert result["status"] == "SUCCESS"
    assert result["validation"]["is_valid"]
    assert result["persisted_validation"][
        "is_valid"
    ]

    assert result["validation"][
        "transaction_rows"
    ] == 3

    assert result["validation"][
        "fraud_transaction_count"
    ] == 1

    assert result["validation"][
        "error_transaction_count"
    ] == 1

    assert result["validation"][
        "transaction_amount_total"
    ] == pytest.approx(81.25)

    for output_path in result[
        "output_paths"
    ].values():
        assert Path(output_path).exists()

    persisted_fact_df = pd.read_parquet(
        result["output_paths"]["transaction"]
    )

    assert persisted_fact_df[
        "has_error"
    ].tolist() == [False, True, False]
