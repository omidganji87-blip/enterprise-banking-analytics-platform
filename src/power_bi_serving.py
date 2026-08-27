from pathlib import Path

import pandas as pd


FACT_TRANSACTION_ANALYTICS_COLUMNS = [
    "transaction_key",
    "date_key",
    "merchant_key",
    "card_id",
    "transaction_timestamp",
    "transaction_amount",
    "transaction_method",
    "transaction_error",
    "is_fraud",
]

DIM_DATE_ANALYTICS_COLUMNS = [
    "date_key",
    "full_date",
    "calendar_year",
    "calendar_quarter",
    "calendar_month_number",
    "calendar_month_name",
    "calendar_day_of_month",
    "calendar_day_of_week_number",
    "calendar_day_name",
    "is_weekend",
]

DIM_MERCHANT_ANALYTICS_COLUMNS = [
    "merchant_key",
    "merchant_id",
    "merchant_city",
    "merchant_state",
    "merchant_zip_code",
    "merchant_category_code",
]

POWER_BI_OUTPUT_FILENAMES = {
    "date": "dim_date_analytics.parquet",
    "merchant": "dim_merchant_analytics.parquet",
    "transaction": "fact_transaction_analytics.parquet",
}


def validate_power_bi_inputs(
    merchant_input_path: Path,
    date_input_path: Path,
    transaction_input_path: Path,
) -> None:
    """Validate that all required Gold Parquet files exist."""

    required_files = [
        Path(merchant_input_path),
        Path(date_input_path),
        Path(transaction_input_path),
    ]

    missing_files = [
        file_path
        for file_path in required_files
        if not file_path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "The Power BI serving layer cannot be created "
            "because these Gold files are missing:\n"
            + "\n".join(
                str(file_path)
                for file_path in missing_files
            )
        )


def _require_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
    table_name: str,
) -> None:
    """Reject an input table that violates its serving contract."""

    missing_columns = [
        column_name
        for column_name in required_columns
        if column_name not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{table_name} is missing required Power BI "
            f"columns: {missing_columns}"
        )


def build_power_bi_frames(
    dim_merchant_df: pd.DataFrame,
    dim_date_df: pd.DataFrame,
    fact_transaction_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Create the three curated DataFrames consumed by Power BI."""

    _require_columns(
        dataframe=dim_merchant_df,
        required_columns=(
            DIM_MERCHANT_ANALYTICS_COLUMNS
        ),
        table_name="dim_merchant",
    )

    _require_columns(
        dataframe=dim_date_df,
        required_columns=DIM_DATE_ANALYTICS_COLUMNS,
        table_name="dim_date",
    )

    _require_columns(
        dataframe=fact_transaction_df,
        required_columns=(
            FACT_TRANSACTION_ANALYTICS_COLUMNS
        ),
        table_name="fact_transaction",
    )

    dim_merchant_analytics_df = (
        dim_merchant_df[
            DIM_MERCHANT_ANALYTICS_COLUMNS
        ]
        .copy()
    )

    dim_date_analytics_df = (
        dim_date_df[
            DIM_DATE_ANALYTICS_COLUMNS
        ]
        .copy()
    )

    dim_date_analytics_df["full_date"] = (
        pd.to_datetime(
            dim_date_analytics_df["full_date"]
        )
    )

    dim_date_analytics_df["calendar_year_month"] = (
        dim_date_analytics_df["full_date"]
        .dt.strftime("%Y-%m")
    )

    dim_date_analytics_df[
        "calendar_year_month_sort"
    ] = (
        dim_date_analytics_df["calendar_year"]
        * 100
        + dim_date_analytics_df[
            "calendar_month_number"
        ]
    )

    fact_transaction_analytics_df = (
        fact_transaction_df[
            FACT_TRANSACTION_ANALYTICS_COLUMNS
        ]
        .copy()
    )

    fact_transaction_analytics_df["has_error"] = (
        fact_transaction_analytics_df[
            "transaction_error"
        ]
        .fillna("NO_ERROR")
        .ne("NO_ERROR")
    )

    return {
        "date": dim_date_analytics_df,
        "merchant": dim_merchant_analytics_df,
        "transaction": (
            fact_transaction_analytics_df
        ),
    }


def validate_power_bi_model(
    source_frames: dict[str, pd.DataFrame],
    serving_frames: dict[str, pd.DataFrame],
) -> dict:
    """Validate serving rows, keys, relationships, and totals."""

    source_date_df = source_frames["date"]
    source_merchant_df = source_frames["merchant"]
    source_transaction_df = source_frames[
        "transaction"
    ]

    date_df = serving_frames["date"]
    merchant_df = serving_frames["merchant"]
    transaction_df = serving_frames[
        "transaction"
    ]

    invalid_date_foreign_keys = int(
        (
            ~transaction_df["date_key"]
            .isin(date_df["date_key"])
        ).sum()
    )

    invalid_merchant_foreign_keys = int(
        (
            ~transaction_df["merchant_key"]
            .isin(merchant_df["merchant_key"])
        ).sum()
    )

    transaction_amount_total = float(
        transaction_df["transaction_amount"].sum()
    )

    source_transaction_amount_total = float(
        source_transaction_df[
            "transaction_amount"
        ].sum()
    )

    fraud_transaction_count = int(
        transaction_df["is_fraud"].sum()
    )

    source_fraud_transaction_count = int(
        source_transaction_df["is_fraud"].sum()
    )

    error_transaction_count = int(
        transaction_df["has_error"].sum()
    )

    source_error_transaction_count = int(
        source_transaction_df["transaction_error"]
        .fillna("NO_ERROR")
        .ne("NO_ERROR")
        .sum()
    )

    validation_result = {
        "date_rows": int(len(date_df)),
        "merchant_rows": int(len(merchant_df)),
        "transaction_rows": int(
            len(transaction_df)
        ),
        "source_date_rows": int(
            len(source_date_df)
        ),
        "source_merchant_rows": int(
            len(source_merchant_df)
        ),
        "source_transaction_rows": int(
            len(source_transaction_df)
        ),
        "missing_date_keys": int(
            date_df["date_key"].isna().sum()
        ),
        "duplicate_date_keys": int(
            date_df["date_key"].duplicated().sum()
        ),
        "missing_merchant_keys": int(
            merchant_df["merchant_key"]
            .isna()
            .sum()
        ),
        "duplicate_merchant_keys": int(
            merchant_df["merchant_key"]
            .duplicated()
            .sum()
        ),
        "missing_transaction_keys": int(
            transaction_df["transaction_key"]
            .isna()
            .sum()
        ),
        "duplicate_transaction_keys": int(
            transaction_df["transaction_key"]
            .duplicated()
            .sum()
        ),
        "invalid_date_foreign_keys": (
            invalid_date_foreign_keys
        ),
        "invalid_merchant_foreign_keys": (
            invalid_merchant_foreign_keys
        ),
        "transaction_amount_total": (
            transaction_amount_total
        ),
        "source_transaction_amount_total": (
            source_transaction_amount_total
        ),
        "fraud_transaction_count": (
            fraud_transaction_count
        ),
        "source_fraud_transaction_count": (
            source_fraud_transaction_count
        ),
        "error_transaction_count": (
            error_transaction_count
        ),
        "source_error_transaction_count": (
            source_error_transaction_count
        ),
    }

    validation_result["is_valid"] = all(
        [
            validation_result["date_rows"]
            == validation_result[
                "source_date_rows"
            ],
            validation_result["merchant_rows"]
            == validation_result[
                "source_merchant_rows"
            ],
            validation_result["transaction_rows"]
            == validation_result[
                "source_transaction_rows"
            ],
            validation_result["missing_date_keys"]
            == 0,
            validation_result["duplicate_date_keys"]
            == 0,
            validation_result[
                "missing_merchant_keys"
            ] == 0,
            validation_result[
                "duplicate_merchant_keys"
            ] == 0,
            validation_result[
                "missing_transaction_keys"
            ] == 0,
            validation_result[
                "duplicate_transaction_keys"
            ] == 0,
            invalid_date_foreign_keys == 0,
            invalid_merchant_foreign_keys == 0,
            abs(
                transaction_amount_total
                - source_transaction_amount_total
            ) < 0.005,
            fraud_transaction_count
            == source_fraud_transaction_count,
            error_transaction_count
            == source_error_transaction_count,
            date_df["calendar_year_month"]
            .notna()
            .all(),
            date_df["calendar_year_month_sort"]
            .notna()
            .all(),
        ]
    )

    if not validation_result["is_valid"]:
        raise ValueError(
            "Power BI serving-layer validation failed: "
            f"{validation_result}"
        )

    return validation_result


def persist_power_bi_frames(
    serving_frames: dict[str, pd.DataFrame],
    output_directory: Path,
) -> dict[str, Path]:
    """Write the curated Power BI tables as Parquet files."""

    output_directory = Path(output_directory)
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_paths = {
        table_name: (
            output_directory
            / POWER_BI_OUTPUT_FILENAMES[
                table_name
            ]
        )
        for table_name in POWER_BI_OUTPUT_FILENAMES
    }

    for table_name, dataframe in (
        serving_frames.items()
    ):
        dataframe.to_parquet(
            output_paths[table_name],
            index=False,
        )

    return output_paths


def validate_persisted_power_bi_frames(
    serving_frames: dict[str, pd.DataFrame],
    output_paths: dict[str, Path],
) -> dict:
    """Reload every file and prove that publication preserved it."""

    persisted_frames = {
        table_name: pd.read_parquet(output_path)
        for table_name, output_path in (
            output_paths.items()
        )
    }

    for table_name, expected_df in (
        serving_frames.items()
    ):
        pd.testing.assert_frame_equal(
            persisted_frames[table_name],
            expected_df,
            check_dtype=True,
            check_like=False,
        )

    invalid_date_foreign_keys = int(
        (
            ~persisted_frames["transaction"][
                "date_key"
            ]
            .isin(
                persisted_frames["date"][
                    "date_key"
                ]
            )
        ).sum()
    )

    invalid_merchant_foreign_keys = int(
        (
            ~persisted_frames["transaction"][
                "merchant_key"
            ]
            .isin(
                persisted_frames["merchant"][
                    "merchant_key"
                ]
            )
        ).sum()
    )

    result = {
        "date_rows": int(
            len(persisted_frames["date"])
        ),
        "merchant_rows": int(
            len(persisted_frames["merchant"])
        ),
        "transaction_rows": int(
            len(persisted_frames["transaction"])
        ),
        "invalid_date_foreign_keys": (
            invalid_date_foreign_keys
        ),
        "invalid_merchant_foreign_keys": (
            invalid_merchant_foreign_keys
        ),
        "is_valid": (
            invalid_date_foreign_keys == 0
            and invalid_merchant_foreign_keys == 0
        ),
    }

    if not result["is_valid"]:
        raise ValueError(
            "Persisted Power BI relationship validation "
            f"failed: {result}"
        )

    return result


def build_power_bi_serving_layer(
    merchant_input_path: Path,
    date_input_path: Path,
    transaction_input_path: Path,
    output_directory: Path,
) -> dict:
    """Build, publish, reload, and validate Power BI tables."""

    merchant_input_path = Path(
        merchant_input_path
    )
    date_input_path = Path(date_input_path)
    transaction_input_path = Path(
        transaction_input_path
    )
    output_directory = Path(output_directory)

    validate_power_bi_inputs(
        merchant_input_path=merchant_input_path,
        date_input_path=date_input_path,
        transaction_input_path=(
            transaction_input_path
        ),
    )

    source_frames = {
        "merchant": pd.read_parquet(
            merchant_input_path
        ),
        "date": pd.read_parquet(date_input_path),
        "transaction": pd.read_parquet(
            transaction_input_path
        ),
    }

    serving_frames = build_power_bi_frames(
        dim_merchant_df=source_frames["merchant"],
        dim_date_df=source_frames["date"],
        fact_transaction_df=(
            source_frames["transaction"]
        ),
    )

    validation_result = validate_power_bi_model(
        source_frames=source_frames,
        serving_frames=serving_frames,
    )

    output_paths = persist_power_bi_frames(
        serving_frames=serving_frames,
        output_directory=output_directory,
    )

    persisted_validation = (
        validate_persisted_power_bi_frames(
            serving_frames=serving_frames,
            output_paths=output_paths,
        )
    )

    return {
        "status": "SUCCESS",
        "output_directory": str(
            output_directory
        ),
        "output_paths": {
            table_name: str(output_path)
            for table_name, output_path in (
                output_paths.items()
            )
        },
        "validation": validation_result,
        "persisted_validation": (
            persisted_validation
        ),
    }
