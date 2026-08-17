from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _build_quarantine_reason(df: pd.DataFrame) -> pd.Series:
    """
    Build a readable quarantine reason for every invalid record.

    A record may violate more than one rule, so multiple reasons are
    combined into one semicolon-separated value.
    """

    reasons = pd.Series("", index=df.index, dtype="string")

    rule_masks = {
        "MISSING_USER_ID": df["user_id"].isna(),
        "MISSING_CARD_ID": df["card_id"].isna(),
        "INVALID_AMOUNT": df["transaction_amount"].isna(),
        "INVALID_TRANSACTION_TIMESTAMP": (
            df["transaction_timestamp"].isna()
        ),
        "INVALID_FRAUD_FLAG": df["is_fraud"].isna(),
    }

    for reason, mask in rule_masks.items():
        reasons = reasons.mask(
            mask & reasons.eq(""),
            reason,
        )

        reasons = reasons.mask(
            mask & reasons.ne("") & ~reasons.str.contains(
                reason,
                regex=False,
                na=False,
            ),
            reasons + ";" + reason,
        )

    return reasons


def transform_bronze_to_silver(
    bronze_input_path: Path,
    silver_output_path: Path,
    quarantine_output_path: Path,
) -> dict:
    """
    Read Bronze credit-card transactions, clean and standardize them,
    separate valid and invalid records, and write Silver and Quarantine
    Parquet files.
    """

    if not bronze_input_path.exists():
        raise FileNotFoundError(
            f"Bronze input file does not exist: "
            f"{bronze_input_path}"
        )

    bronze_df = pd.read_parquet(bronze_input_path)

    required_bronze_columns = [
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
        "_source_file_name",
        "_ingestion_timestamp_utc",
        "_pipeline_run_id",
    ]

    missing_columns = sorted(
        set(required_bronze_columns)
        - set(bronze_df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Bronze file is missing required columns: "
            f"{missing_columns}"
        )

    silver_work_df = bronze_df.copy()

    # =====================================================
    # 1. Rename source columns to standardized names
    # =====================================================

    silver_work_df = silver_work_df.rename(
        columns={
            "User": "user_id",
            "Card": "card_id",
            "Year": "transaction_year",
            "Month": "transaction_month",
            "Day": "transaction_day",
            "Time": "transaction_time",
            "Amount": "transaction_amount_raw",
            "Use Chip": "transaction_method",
            "Merchant Name": "merchant_id",
            "Merchant City": "merchant_city",
            "Merchant State": "merchant_state",
            "Zip": "merchant_zip_code_raw",
            "MCC": "merchant_category_code",
            "Errors?": "transaction_error",
            "Is Fraud?": "is_fraud_raw",
        }
    )

    # =====================================================
    # 2. Standardize identifier columns
    # =====================================================

    silver_work_df["user_id"] = pd.to_numeric(
        silver_work_df["user_id"],
        errors="coerce",
    ).astype("Int64")

    silver_work_df["card_id"] = pd.to_numeric(
        silver_work_df["card_id"],
        errors="coerce",
    ).astype("Int64")

    silver_work_df["merchant_id"] = pd.to_numeric(
        silver_work_df["merchant_id"],
        errors="coerce",
    ).astype("Int64")

    silver_work_df["merchant_category_code"] = pd.to_numeric(
        silver_work_df["merchant_category_code"],
        errors="coerce",
    ).astype("Int64")

    # =====================================================
    # 3. Clean transaction amount
    # =====================================================

    amount_cleaned = (
        silver_work_df["transaction_amount_raw"]
        .astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    silver_work_df["transaction_amount"] = pd.to_numeric(
        amount_cleaned,
        errors="coerce",
    )

    # Important:
    # Negative amounts are not automatically invalid because they may
    # represent refunds, reversals, or credits.

    # =====================================================
    # 4. Build one transaction timestamp
    # =====================================================

    transaction_datetime_text = (
        silver_work_df["transaction_year"]
        .astype("string")
        .str.zfill(4)
        + "-"
        + silver_work_df["transaction_month"]
        .astype("string")
        .str.zfill(2)
        + "-"
        + silver_work_df["transaction_day"]
        .astype("string")
        .str.zfill(2)
        + " "
        + silver_work_df["transaction_time"]
        .astype("string")
        .str.strip()
    )

    silver_work_df["transaction_timestamp"] = pd.to_datetime(
        transaction_datetime_text,
        format="%Y-%m-%d %H:%M",
        errors="coerce",
    )

    # =====================================================
    # 5. Standardize transaction method
    # =====================================================

    transaction_method_mapping = {
        "Swipe Transaction": "SWIPE",
        "Chip Transaction": "CHIP",
        "Online Transaction": "ONLINE",
    }

    silver_work_df["transaction_method"] = (
        silver_work_df["transaction_method"]
        .astype("string")
        .str.strip()
        .map(transaction_method_mapping)
        .fillna("UNKNOWN")
    )

    # =====================================================
    # 6. Standardize merchant text fields
    # =====================================================

    silver_work_df["merchant_city"] = (
        silver_work_df["merchant_city"]
        .astype("string")
        .str.strip()
    )

    silver_work_df["merchant_state"] = (
        silver_work_df["merchant_state"]
        .astype("string")
        .str.strip()
    )

    # =====================================================
    # 7. Convert ZIP/postal code to text
    # =====================================================

    silver_work_df["merchant_zip_code"] = (
        silver_work_df["merchant_zip_code_raw"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    # Missing ZIP codes are allowed because:
    # - Online transactions may not have a physical merchant ZIP.
    # - International transactions may use other location formats.

    # =====================================================
    # 8. Standardize transaction errors
    # =====================================================

    silver_work_df["transaction_error"] = (
        silver_work_df["transaction_error"]
        .astype("string")
        .str.strip()
        .fillna("NO_ERROR")
    )

    silver_work_df["transaction_error"] = (
        silver_work_df["transaction_error"]
        .replace("", "NO_ERROR")
    )

    # =====================================================
    # 9. Convert fraud flag to Boolean
    # =====================================================

    fraud_mapping = {
        "Yes": True,
        "No": False,
    }

    silver_work_df["is_fraud"] = (
        silver_work_df["is_fraud_raw"]
        .astype("string")
        .str.strip()
        .map(fraud_mapping)
        .astype("boolean")
    )

    # =====================================================
    # 10. Add Silver audit information
    # =====================================================

    silver_processed_at_utc = datetime.now(timezone.utc)

    silver_work_df[
        "_silver_processed_at_utc"
    ] = silver_processed_at_utc

    # =====================================================
    # 11. Apply business validation rules
    # =====================================================

    silver_work_df["quarantine_reason"] = (
        _build_quarantine_reason(silver_work_df)
    )

    valid_mask = silver_work_df[
        "quarantine_reason"
    ].eq("")

    valid_df = (
        silver_work_df.loc[valid_mask]
        .copy()
        .reset_index(drop=True)
    )

    quarantine_df = (
        silver_work_df.loc[~valid_mask]
        .copy()
        .reset_index(drop=True)
    )

    # =====================================================
    # 12. Select final Silver columns
    # =====================================================

    silver_columns = [
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
        "_source_file_name",
        "_ingestion_timestamp_utc",
        "_pipeline_run_id",
        "_silver_processed_at_utc",
    ]

    valid_df = valid_df[silver_columns]

    # Quarantine retains cleaned fields, original values, audit data,
    # and the reason for rejection.
    quarantine_columns = [
        "user_id",
        "card_id",
        "transaction_year",
        "transaction_month",
        "transaction_day",
        "transaction_time",
        "transaction_timestamp",
        "transaction_amount_raw",
        "transaction_amount",
        "transaction_method",
        "merchant_id",
        "merchant_city",
        "merchant_state",
        "merchant_zip_code_raw",
        "merchant_zip_code",
        "merchant_category_code",
        "transaction_error",
        "is_fraud_raw",
        "is_fraud",
        "quarantine_reason",
        "_source_file_name",
        "_ingestion_timestamp_utc",
        "_pipeline_run_id",
        "_silver_processed_at_utc",
    ]

    quarantine_df = quarantine_df[quarantine_columns]

    # =====================================================
    # 13. Create output folders and write files
    # =====================================================

    silver_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    quarantine_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    valid_df.to_parquet(
        silver_output_path,
        index=False,
    )

    quarantine_df.to_parquet(
        quarantine_output_path,
        index=False,
    )

    # =====================================================
    # 14. Return operational metrics
    # =====================================================

    total_rows = len(bronze_df)
    valid_rows = len(valid_df)
    quarantined_rows = len(quarantine_df)

    return {
        "status": "SUCCESS",
        "bronze_rows_read": total_rows,
        "silver_rows_written": valid_rows,
        "quarantine_rows_written": quarantined_rows,
        "reconciliation_passed": (
            total_rows
            == valid_rows + quarantined_rows
        ),
        "silver_output_path": str(silver_output_path),
        "quarantine_output_path": str(
            quarantine_output_path
        ),
    }