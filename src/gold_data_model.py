from pathlib import Path

import pandas as pd


REQUIRED_SILVER_COLUMNS = [
    "user_id",
    "card_id",
    "transaction_timestamp",
    "transaction_amount",
    "transaction_method",
    "merchant_id",
    "merchant_city",
    "merchant_state",
    "merchant_zip_code",
    "merchant_category_code",
    "transaction_error",
    "is_fraud",
]


def validate_silver_source(silver_df: pd.DataFrame) -> None:
    """
    Validate that the Silver DataFrame contains all columns required
    to build the Gold dimensional model.

    Raises
    ------
    ValueError
        If one or more required columns are missing.
    """

    missing_columns = sorted(
        set(REQUIRED_SILVER_COLUMNS) - set(silver_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Gold model cannot be created because required Silver "
            f"columns are missing: {missing_columns}"
        )


def create_merchant_dimension(
    silver_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create the merchant dimension.

    Grain
    -----
    One row per unique merchant business record.

    The surrogate key `merchant_key` is generated independently
    from the source-system `merchant_id`.
    """

    merchant_columns = [
        "merchant_id",
        "merchant_city",
        "merchant_state",
        "merchant_zip_code",
        "merchant_category_code",
    ]

    dim_merchant_df = (
        silver_df[merchant_columns]
        .drop_duplicates()
        .sort_values(
            by=merchant_columns,
            na_position="last",
        )
        .reset_index(drop=True)
    )

    dim_merchant_df.insert(
        loc=0,
        column="merchant_key",
        value=range(1, len(dim_merchant_df) + 1),
    )

    return dim_merchant_df


def create_date_dimension(
    silver_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a complete date dimension covering the minimum and maximum
    transaction dates found in the Silver data.

    Grain
    -----
    One row per calendar date.
    """

    transaction_dates = pd.to_datetime(
        silver_df["transaction_timestamp"],
        errors="coerce",
    ).dt.normalize()

    if transaction_dates.isna().any():
        invalid_count = int(transaction_dates.isna().sum())

        raise ValueError(
            "Date dimension cannot be created because "
            f"{invalid_count} transaction timestamps are invalid."
        )

    minimum_date = transaction_dates.min()
    maximum_date = transaction_dates.max()

    if pd.isna(minimum_date) or pd.isna(maximum_date):
        raise ValueError(
            "Date dimension cannot be created from an empty "
            "transaction date range."
        )

    full_date_range = pd.date_range(
        start=minimum_date,
        end=maximum_date,
        freq="D",
    )

    dim_date_df = pd.DataFrame(
        {
            "full_date": full_date_range,
        }
    )

    dim_date_df["date_key"] = (
        dim_date_df["full_date"]
        .dt.strftime("%Y%m%d")
        .astype("int64")
    )

    dim_date_df["calendar_year"] = (
        dim_date_df["full_date"].dt.year
    )

    dim_date_df["calendar_quarter"] = (
        dim_date_df["full_date"].dt.quarter
    )

    dim_date_df["calendar_month_number"] = (
        dim_date_df["full_date"].dt.month
    )

    dim_date_df["calendar_month_name"] = (
        dim_date_df["full_date"].dt.month_name()
    )

    dim_date_df["calendar_day_of_month"] = (
        dim_date_df["full_date"].dt.day
    )

    dim_date_df["calendar_day_of_week_number"] = (
        dim_date_df["full_date"].dt.dayofweek + 1
    )

    dim_date_df["calendar_day_name"] = (
        dim_date_df["full_date"].dt.day_name()
    )

    dim_date_df["is_weekend"] = (
        dim_date_df["full_date"].dt.dayofweek >= 5
    )

    dim_date_df = dim_date_df[
        [
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
    ]

    return dim_date_df


def create_transaction_fact(
    silver_df: pd.DataFrame,
    dim_merchant_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create the transaction fact table.

    Grain
    -----
    One row per credit-card transaction.

    The fact table receives:
    - transaction_key as its surrogate primary key
    - date_key as a foreign key to dim_date
    - merchant_key as a foreign key to dim_merchant
    """

    fact_df = silver_df.copy()

    fact_df["transaction_timestamp"] = pd.to_datetime(
        fact_df["transaction_timestamp"],
        errors="coerce",
    )

    if fact_df["transaction_timestamp"].isna().any():
        invalid_count = int(
            fact_df["transaction_timestamp"].isna().sum()
        )

        raise ValueError(
            "Transaction fact cannot be created because "
            f"{invalid_count} timestamps are invalid."
        )

    fact_df["date_key"] = (
        fact_df["transaction_timestamp"]
        .dt.strftime("%Y%m%d")
        .astype("int64")
    )

    merchant_natural_key_columns = [
        "merchant_id",
        "merchant_city",
        "merchant_state",
        "merchant_zip_code",
        "merchant_category_code",
    ]

    merchant_lookup_df = dim_merchant_df[
        ["merchant_key"] + merchant_natural_key_columns
    ]

    fact_df = fact_df.merge(
        merchant_lookup_df,
        how="left",
        on=merchant_natural_key_columns,
        validate="many_to_one",
    )

    if fact_df["merchant_key"].isna().any():
        missing_count = int(
            fact_df["merchant_key"].isna().sum()
        )

        raise ValueError(
            "Transaction fact contains "
            f"{missing_count} rows without a merchant foreign key."
        )

    fact_df["merchant_key"] = (
        fact_df["merchant_key"].astype("int64")
    )

    fact_df.insert(
        loc=0,
        column="transaction_key",
        value=range(1, len(fact_df) + 1),
    )

    fact_columns = [
        "transaction_key",
        "date_key",
        "merchant_key",
        "user_id",
        "card_id",
        "transaction_timestamp",
        "transaction_amount",
        "transaction_method",
        "merchant_category_code",
        "transaction_error",
        "is_fraud",
        "_source_file_name",
        "_ingestion_timestamp_utc",
        "_pipeline_run_id",
    ]

    available_fact_columns = [
        column
        for column in fact_columns
        if column in fact_df.columns
    ]

    fact_df = fact_df[available_fact_columns]

    return fact_df


def validate_gold_model(
    dim_merchant_df: pd.DataFrame,
    dim_date_df: pd.DataFrame,
    fact_transaction_df: pd.DataFrame,
    expected_fact_rows: int,
) -> dict:
    """
    Validate primary keys, foreign keys, row counts, and dimensional
    relationships before Gold tables are written.
    """

    duplicate_merchant_keys = int(
        dim_merchant_df["merchant_key"].duplicated().sum()
    )

    duplicate_date_keys = int(
        dim_date_df["date_key"].duplicated().sum()
    )

    duplicate_transaction_keys = int(
        fact_transaction_df[
            "transaction_key"
        ].duplicated().sum()
    )

    missing_merchant_keys = int(
        dim_merchant_df["merchant_key"].isna().sum()
    )

    missing_date_keys = int(
        dim_date_df["date_key"].isna().sum()
    )

    missing_transaction_keys = int(
        fact_transaction_df[
            "transaction_key"
        ].isna().sum()
    )

    invalid_merchant_foreign_keys = int(
        (
            ~fact_transaction_df["merchant_key"].isin(
            dim_merchant_df["merchant_key"]
        )
    ).sum()
    )
    invalid_date_foreign_keys = int(
        (
            ~fact_transaction_df["date_key"].isin(
            dim_date_df["date_key"]
        )
    ).sum()
    )
    

    actual_fact_rows = len(fact_transaction_df)

    validation_result = {
        "expected_fact_rows": expected_fact_rows,
        "actual_fact_rows": actual_fact_rows,
        "duplicate_merchant_keys": duplicate_merchant_keys,
        "duplicate_date_keys": duplicate_date_keys,
        "duplicate_transaction_keys": duplicate_transaction_keys,
        "missing_merchant_keys": missing_merchant_keys,
        "missing_date_keys": missing_date_keys,
        "missing_transaction_keys": missing_transaction_keys,
        "invalid_merchant_foreign_keys": (
            invalid_merchant_foreign_keys
        ),
        "invalid_date_foreign_keys": (
            invalid_date_foreign_keys
        ),
    }

    validation_result["is_valid"] = all(
        [
            actual_fact_rows == expected_fact_rows,
            duplicate_merchant_keys == 0,
            duplicate_date_keys == 0,
            duplicate_transaction_keys == 0,
            missing_merchant_keys == 0,
            missing_date_keys == 0,
            missing_transaction_keys == 0,
            invalid_merchant_foreign_keys == 0,
            invalid_date_foreign_keys == 0,
        ]
    )

    if not validation_result["is_valid"]:
        raise ValueError(
            "Gold model validation failed: "
            f"{validation_result}"
        )

    return validation_result


def build_gold_data_model(
    silver_input_path: Path,
    merchant_output_path: Path,
    date_output_path: Path,
    transaction_output_path: Path,
) -> dict:
    """
    Build and persist the complete Gold dimensional model.

    Processing flow
    ---------------
    1. Read the Silver transaction table.
    2. Validate the Silver schema.
    3. Create the merchant dimension.
    4. Create the date dimension.
    5. Create the transaction fact table.
    6. Validate primary and foreign keys.
    7. Write all Gold tables as Parquet.
    8. Reload and reconcile the persisted tables.
    9. Return execution metrics.
    """

    if not silver_input_path.exists():
        raise FileNotFoundError(
            f"Silver input file was not found: "
            f"{silver_input_path}"
        )

    silver_df = pd.read_parquet(silver_input_path)

    validate_silver_source(silver_df)

    dim_merchant_df = create_merchant_dimension(
        silver_df=silver_df
    )

    dim_date_df = create_date_dimension(
        silver_df=silver_df
    )

    fact_transaction_df = create_transaction_fact(
        silver_df=silver_df,
        dim_merchant_df=dim_merchant_df,
    )

    in_memory_validation = validate_gold_model(
        dim_merchant_df=dim_merchant_df,
        dim_date_df=dim_date_df,
        fact_transaction_df=fact_transaction_df,
        expected_fact_rows=len(silver_df),
    )

    merchant_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    date_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    transaction_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dim_merchant_df.to_parquet(
        merchant_output_path,
        index=False,
    )

    dim_date_df.to_parquet(
        date_output_path,
        index=False,
    )

    fact_transaction_df.to_parquet(
        transaction_output_path,
        index=False,
    )

    persisted_dim_merchant_df = pd.read_parquet(
        merchant_output_path
    )

    persisted_dim_date_df = pd.read_parquet(
        date_output_path
    )

    persisted_fact_transaction_df = pd.read_parquet(
        transaction_output_path
    )

    persisted_validation = validate_gold_model(
        dim_merchant_df=persisted_dim_merchant_df,
        dim_date_df=persisted_dim_date_df,
        fact_transaction_df=persisted_fact_transaction_df,
        expected_fact_rows=len(silver_df),
    )

    return {
        "status": "SUCCESS",
        "silver_input_path": str(silver_input_path),
        "merchant_output_path": str(merchant_output_path),
        "date_output_path": str(date_output_path),
        "transaction_output_path": str(
            transaction_output_path
        ),
        "silver_rows_read": len(silver_df),
        "merchant_rows_written": len(
            persisted_dim_merchant_df
        ),
        "date_rows_written": len(
            persisted_dim_date_df
        ),
        "transaction_rows_written": len(
            persisted_fact_transaction_df
        ),
        "merchant_columns": len(
            persisted_dim_merchant_df.columns
        ),
        "date_columns": len(
            persisted_dim_date_df.columns
        ),
        "transaction_columns": len(
            persisted_fact_transaction_df.columns
        ),
        "in_memory_validation": in_memory_validation,
        "persisted_validation": persisted_validation,
    }