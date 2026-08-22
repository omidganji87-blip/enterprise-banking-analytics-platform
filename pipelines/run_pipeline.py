from pprint import pprint

import src.domain_bronze_ingestion as domain_bronze
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


# ============================================================
# Pipeline paths
# ============================================================

DATA_PATH = PROJECT_ROOT / "data"
ANALYTICS_PATH = DATA_PATH / "analytics"

BRONZE_OUTPUT_PATH = (
    BRONZE_PATH
    / "credit_card_transactions_raw.parquet"
)

CONTROL_TABLE_PATH = (
    METADATA_PATH
    / "bronze_ingestion_control.parquet"
)

SILVER_OUTPUT_PATH = (
    SILVER_PATH
    / "credit_card_transactions_clean.parquet"
)

QUARANTINE_OUTPUT_PATH = (
    QUARANTINE_PATH
    / "credit_card_transactions_quarantine.parquet"
)

MERCHANT_OUTPUT_PATH = (
    GOLD_PATH
    / "dim_merchant.parquet"
)

DATE_OUTPUT_PATH = (
    GOLD_PATH
    / "dim_date.parquet"
)

TRANSACTION_OUTPUT_PATH = (
    GOLD_PATH
    / "fact_transaction.parquet"
)

ANALYTICS_DATABASE_PATH = (
    ANALYTICS_PATH
    / "banking_analytics.duckdb"
)


# ============================================================
# Pipeline helpers
# ============================================================

def _print_stage(
    stage_number: int,
    stage_name: str,
) -> None:
    """
    Print a consistent pipeline-stage heading.
    """

    print()
    print(
        f"STAGE {stage_number} - {stage_name}"
    )
    print("-" * 70)


def _require_success(
    stage_name: str,
    stage_result: dict,
) -> None:
    """
    Stop the pipeline when a stage reports failure.

    A failed upstream stage must never publish downstream data.
    """

    if stage_result.get("status") != "SUCCESS":
        raise RuntimeError(
            f"{stage_name} did not complete successfully: "
            f"{stage_result}"
        )


def _print_pipeline_summary(
    pipeline_result: dict,
) -> None:
    """
    Print the most important execution metrics.
    """

    bronze_result = pipeline_result["bronze"]

    domain_result = pipeline_result[
        "domain_bronze"
    ]

    silver_result = pipeline_result["silver"]
    gold_result = pipeline_result["gold"]

    analytics_result = pipeline_result[
        "analytics"
    ]

    print()
    print("=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(
        "Transaction files discovered:",
        bronze_result["files_discovered"],
    )

    print(
        "Transaction files processed:",
        bronze_result["files_processed"],
    )

    print(
        "Transaction files skipped:",
        bronze_result["files_skipped"],
    )

    print(
        "Transaction files failed:",
        bronze_result["files_failed"],
    )

    print(
        "Transaction Bronze rows:",
        bronze_result["bronze_total_rows"],
    )

    print(
        "Reference domains discovered:",
        domain_result["domains_discovered"],
    )

    print(
        "Reference domains succeeded:",
        domain_result["domains_succeeded"],
    )

    print(
        "Reference domains failed:",
        domain_result["domains_failed"],
    )

    print(
        "Reference files processed:",
        domain_result["files_processed"],
    )

    print(
        "Reference files skipped:",
        domain_result["files_skipped"],
    )

    print(
        "Reference Bronze rows written:",
        domain_result["rows_written"],
    )

    print(
        "Silver rows written:",
        silver_result["silver_rows_written"],
    )

    print(
        "Quarantine rows written:",
        silver_result[
            "quarantine_rows_written"
        ],
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
        gold_result[
            "transaction_rows_written"
        ],
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
            analytics_result["views_created"]
        ),
    )

    print(
        "Analytics transaction rows:",
        analytics_result[
            "platform_kpis"
        ]["total_transactions"],
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
        analytics_result[
            "platform_kpis"
        ]["fraud_transaction_rate_percent"],
    )

    print(
        "Analytics validation:",
        analytics_result[
            "validation"
        ]["is_valid"],
    )

    print("=" * 70)


# ============================================================
# Enterprise pipeline
# ============================================================

def run_enterprise_banking_pipeline() -> dict:
    """
    Run the complete banking analytics pipeline.

    Processing flow
    ---------------
    Transaction landing CSV files
        -> Transaction Bronze append

    Card and user landing CSV files
        -> Domain-specific Bronze append

    Transaction Bronze
        -> Silver cleaning and quarantine
        -> Gold dimensional model
        -> DuckDB analytics serving layer

    Downstream publication is allowed only when every required
    upstream Bronze domain succeeds.
    """

    print("=" * 70)
    print("ENTERPRISE BANKING ANALYTICS PIPELINE")
    print("=" * 70)

    LANDING_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Stage 1: Transaction Bronze ingestion
    # --------------------------------------------------------

    _print_stage(
        1,
        "TRANSACTION BRONZE INGESTION",
    )

    bronze_result = ingest_landing_csv_files(
        landing_path=LANDING_PATH,
        bronze_output_path=(
            BRONZE_OUTPUT_PATH
        ),
        control_table_path=(
            CONTROL_TABLE_PATH
        ),
        expected_columns=(
            TRANSACTION_REQUIRED_COLUMNS
        ),
        expected_dtypes=(
            TRANSACTION_EXPECTED_DTYPES
        ),
    )

    pprint(bronze_result)

    _require_success(
        "Transaction Bronze ingestion",
        bronze_result,
    )

    # --------------------------------------------------------
    # Stage 2: Card and user Bronze ingestion
    # --------------------------------------------------------

    _print_stage(
        2,
        "CARD AND USER BRONZE INGESTION",
    )

    domain_bronze_result = (
        domain_bronze
        .ingest_card_and_user_sources()
    )

    pprint(domain_bronze_result)

    _require_success(
        "Card and user Bronze ingestion",
        domain_bronze_result,
    )

    # --------------------------------------------------------
    # Stage 3: Silver transformation
    # --------------------------------------------------------

    _print_stage(
        3,
        "SILVER TRANSFORMATION",
    )

    silver_result = transform_bronze_to_silver(
        bronze_input_path=(
            BRONZE_OUTPUT_PATH
        ),
        silver_output_path=(
            SILVER_OUTPUT_PATH
        ),
        quarantine_output_path=(
            QUARANTINE_OUTPUT_PATH
        ),
    )

    pprint(silver_result)

    _require_success(
        "Silver transformation",
        silver_result,
    )

    if not silver_result.get(
        "reconciliation_passed"
    ):
        raise RuntimeError(
            "Silver row reconciliation failed."
        )

    # --------------------------------------------------------
    # Stage 4: Gold dimensional model
    # --------------------------------------------------------

    _print_stage(
        4,
        "GOLD DIMENSIONAL MODEL",
    )

    gold_result = build_gold_data_model(
        silver_input_path=(
            SILVER_OUTPUT_PATH
        ),
        merchant_output_path=(
            MERCHANT_OUTPUT_PATH
        ),
        date_output_path=(
            DATE_OUTPUT_PATH
        ),
        transaction_output_path=(
            TRANSACTION_OUTPUT_PATH
        ),
    )

    pprint(gold_result)

    _require_success(
        "Gold dimensional model",
        gold_result,
    )

    if not gold_result[
        "persisted_validation"
    ]["is_valid"]:
        raise RuntimeError(
            "Persisted Gold validation failed."
        )

    # --------------------------------------------------------
    # Stage 5: Analytics serving layer
    # --------------------------------------------------------

    _print_stage(
        5,
        "ANALYTICS SERVING LAYER",
    )

    analytics_result = (
        build_analytics_serving_layer(
            merchant_input_path=(
                MERCHANT_OUTPUT_PATH
            ),
            date_input_path=(
                DATE_OUTPUT_PATH
            ),
            transaction_input_path=(
                TRANSACTION_OUTPUT_PATH
            ),
            analytics_database_path=(
                ANALYTICS_DATABASE_PATH
            ),
        )
    )

    pprint(analytics_result)

    _require_success(
        "Analytics serving layer",
        analytics_result,
    )

    if not analytics_result[
        "validation"
    ]["is_valid"]:
        raise RuntimeError(
            "Analytics serving-layer validation "
            "failed."
        )

    pipeline_result = {
        "status": "SUCCESS",
        "bronze": bronze_result,
        "domain_bronze": (
            domain_bronze_result
        ),
        "silver": silver_result,
        "gold": gold_result,
        "analytics": analytics_result,
    }

    _print_pipeline_summary(
        pipeline_result
    )

    return pipeline_result


# ============================================================
# Command-line entry point
# ============================================================

if __name__ == "__main__":
    run_enterprise_banking_pipeline()