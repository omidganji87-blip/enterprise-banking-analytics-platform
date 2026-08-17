"""End-to-end orchestration for the banking analytics platform."""

from pprint import pprint

from configs.config import (
    BRONZE_PATH,
    GOLD_PATH,
    LANDING_PATH,
    METADATA_PATH,
    PROJECT_ROOT,
    QUARANTINE_PATH,
    SILVER_PATH,
)
from configs.source_schemas import (
    TRANSACTION_EXPECTED_DTYPES,
    TRANSACTION_REQUIRED_COLUMNS,
)
from src.analytics_serving import build_analytics_serving_layer
from src.bronze_ingestion import ingest_landing_csv_files
from src.gold_data_model import build_gold_data_model
from src.silver_transformation import transform_bronze_to_silver


# -----------------------------------------------------------------------------
# Pipeline paths
# -----------------------------------------------------------------------------

DATA_PATH = PROJECT_ROOT / "data"
ANALYTICS_PATH = DATA_PATH / "analytics"

BRONZE_OUTPUT_PATH = (
    BRONZE_PATH / "credit_card_transactions_sample.parquet"
)

CONTROL_TABLE_PATH = (
    METADATA_PATH / "file_processing_control.parquet"
)

SILVER_OUTPUT_PATH = (
    SILVER_PATH / "credit_card_transactions_clean.parquet"
)

QUARANTINE_OUTPUT_PATH = (
    QUARANTINE_PATH
    / "credit_card_transactions_quarantine.parquet"
)

MERCHANT_OUTPUT_PATH = (
    GOLD_PATH / "dim_merchant.parquet"
)

DATE_OUTPUT_PATH = (
    GOLD_PATH / "dim_date.parquet"
)

TRANSACTION_OUTPUT_PATH = (
    GOLD_PATH / "fact_transaction.parquet"
)

ANALYTICS_DATABASE_PATH = (
    ANALYTICS_PATH / "banking_analytics.duckdb"
)


def _print_stage(
    title: str,
    result: dict,
) -> None:
    """Print one pipeline stage and its execution metrics."""

    print()
    print(title)
    print("-" * 70)

    pprint(
        result,
        sort_dicts=False,
    )


def _require_success(
    stage_name: str,
    result: dict,
) -> None:
    """
    Stop the pipeline before publishing incomplete downstream data.
    """

    if result.get("status") != "SUCCESS":
        raise RuntimeError(
            f"{stage_name} did not complete successfully. "
            f"Status: {result.get('status', 'UNKNOWN')}"
        )


def run_enterprise_banking_pipeline() -> dict:
    """
    Run the complete enterprise banking analytics pipeline.

    Processing flow
    ---------------
    1. Discover and process every CSV in Landing.
    2. Append valid new batches into Bronze.
    3. Stop downstream publication if any Landing file fails.
    4. Transform Bronze into Silver and Quarantine.
    5. Build the Gold dimensional model.
    6. Build the DuckDB analytics serving layer.
    7. Validate persisted outputs.
    8. Return complete execution metrics.
    """

    print("=" * 70)
    print("ENTERPRISE BANKING ANALYTICS PIPELINE")
    print("=" * 70)

    # Ensure that a missing Landing directory is represented as an
    # empty Landing directory. The ingestion function then produces
    # a clear "No CSV files were found" error.
    LANDING_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------------------
    # Stage 1 — Bronze ingestion
    # -----------------------------------------------------------------

    bronze_result = ingest_landing_csv_files(
        landing_path=LANDING_PATH,
        bronze_output_path=BRONZE_OUTPUT_PATH,
        control_table_path=CONTROL_TABLE_PATH,
        expected_columns=TRANSACTION_REQUIRED_COLUMNS,
        expected_dtypes=TRANSACTION_EXPECTED_DTYPES,
    )

    _print_stage(
        title="STAGE 1 - BRONZE INGESTION",
        result=bronze_result,
    )

    # PARTIAL_SUCCESS and FAILED must block downstream publication.
    # This prevents an incomplete batch from replacing verified
    # Silver, Gold, and Analytics outputs.
    _require_success(
        stage_name="Bronze ingestion",
        result=bronze_result,
    )

    # -----------------------------------------------------------------
    # Stage 2 — Silver transformation
    # -----------------------------------------------------------------

    silver_result = transform_bronze_to_silver(
        bronze_input_path=BRONZE_OUTPUT_PATH,
        silver_output_path=SILVER_OUTPUT_PATH,
        quarantine_output_path=QUARANTINE_OUTPUT_PATH,
    )

    _print_stage(
        title="STAGE 2 - SILVER TRANSFORMATION",
        result=silver_result,
    )

    _require_success(
        stage_name="Silver transformation",
        result=silver_result,
    )

    if not silver_result.get(
        "reconciliation_passed",
        False,
    ):
        raise RuntimeError(
            "Silver transformation reconciliation failed."
        )

    # -----------------------------------------------------------------
    # Stage 3 — Gold dimensional model
    # -----------------------------------------------------------------

    gold_result = build_gold_data_model(
        silver_input_path=SILVER_OUTPUT_PATH,
        merchant_output_path=MERCHANT_OUTPUT_PATH,
        date_output_path=DATE_OUTPUT_PATH,
        transaction_output_path=TRANSACTION_OUTPUT_PATH,
    )

    _print_stage(
        title="STAGE 3 - GOLD DIMENSIONAL MODEL",
        result=gold_result,
    )

    _require_success(
        stage_name="Gold dimensional model",
        result=gold_result,
    )

    if not gold_result[
        "persisted_validation"
    ]["is_valid"]:
        raise RuntimeError(
            "Persisted Gold model validation failed."
        )

    # -----------------------------------------------------------------
    # Stage 4 — Analytics serving layer
    # -----------------------------------------------------------------

    analytics_result = build_analytics_serving_layer(
        merchant_input_path=MERCHANT_OUTPUT_PATH,
        date_input_path=DATE_OUTPUT_PATH,
        transaction_input_path=TRANSACTION_OUTPUT_PATH,
        analytics_database_path=ANALYTICS_DATABASE_PATH,
    )

    _print_stage(
        title="STAGE 4 - ANALYTICS SERVING LAYER",
        result=analytics_result,
    )

    _require_success(
        stage_name="Analytics serving layer",
        result=analytics_result,
    )

    if not analytics_result[
        "validation"
    ]["is_valid"]:
        raise RuntimeError(
            "Analytics serving-layer validation failed."
        )

    # -----------------------------------------------------------------
    # Complete pipeline result
    # -----------------------------------------------------------------

    pipeline_result = {
        "status": "SUCCESS",
        "bronze": bronze_result,
        "silver": silver_result,
        "gold": gold_result,
        "analytics": analytics_result,
    }

    print()
    print("=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(
        "Landing files discovered:",
        bronze_result["files_discovered"],
    )

    print(
        "Landing files processed:",
        bronze_result["files_processed"],
    )

    print(
        "Landing files skipped:",
        bronze_result["files_skipped"],
    )

    print(
        "Landing files failed:",
        bronze_result["files_failed"],
    )

    print(
        "Bronze total rows:",
        bronze_result["bronze_total_rows"],
    )

    print(
        "Silver rows written:",
        silver_result["silver_rows_written"],
    )

    print(
        "Quarantine rows written:",
        silver_result["quarantine_rows_written"],
    )

    print(
        "Gold merchant rows:",
        gold_result["merchant_rows_written"],
    )

    print(
        "Gold date rows:",
        gold_result["date_rows_written"],
    )

    print(
        "Gold transaction rows:",
        gold_result["transaction_rows_written"],
    )

    print(
        "Gold persisted validation:",
        gold_result[
            "persisted_validation"
        ]["is_valid"],
    )

    print(
        "Analytics views created:",
        len(
            analytics_result[
                "views_created"
            ]
        ),
    )

    print(
        "Analytics transaction rows:",
        analytics_result[
            "validation"
        ]["transaction_rows"],
    )

    print(
        "Total transaction amount:",
        analytics_result[
            "platform_kpis"
        ]["total_transaction_amount"],
    )

    print(
        "Fraudulent transactions:",
        analytics_result[
            "platform_kpis"
        ]["fraudulent_transactions"],
    )

    print(
        "Fraud transaction rate:",
        (
            analytics_result[
                "platform_kpis"
            ]["fraud_transaction_rate_percent"]
        ),
    )

    print(
        "Analytics validation:",
        analytics_result[
            "validation"
        ]["is_valid"],
    )

    print("=" * 70)

    return pipeline_result


if __name__ == "__main__":
    run_enterprise_banking_pipeline()