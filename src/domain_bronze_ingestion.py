"""
Bronze ingestion orchestration for the card and user domains.

This module reuses the generic Bronze-ingestion framework already
used by transaction files. Each source domain receives:

1. Its own Landing directory.
2. Its own schema contract.
3. Its own Bronze Parquet table.
4. Its own metadata control table.
5. Independent SHA-256 idempotency.
"""

from pathlib import Path
from pprint import pprint

from configs.config import (
    BRONZE_PATH,
    CARD_LANDING_PATH,
    METADATA_PATH,
    USER_LANDING_PATH,
)
from configs.source_schemas import (
    SOURCE_SCHEMA_REGISTRY,
)
from src.bronze_ingestion import (
    ingest_landing_csv_files,
)


# ============================================================
# Bronze output paths
# ============================================================

CARD_BRONZE_OUTPUT_PATH = (
    BRONZE_PATH
    / "credit_cards_raw.parquet"
)

USER_BRONZE_OUTPUT_PATH = (
    BRONZE_PATH
    / "banking_users_raw.parquet"
)


# ============================================================
# Metadata control-table paths
# ============================================================

CARD_CONTROL_TABLE_PATH = (
    METADATA_PATH
    / "credit_cards_file_processing_control.parquet"
)

USER_CONTROL_TABLE_PATH = (
    METADATA_PATH
    / "banking_users_file_processing_control.parquet"
)


# ============================================================
# Domain runtime configuration
# ============================================================

DOMAIN_RUNTIME_CONFIG = {
    "cards": {
        "landing_path": CARD_LANDING_PATH,
        "bronze_output_path": CARD_BRONZE_OUTPUT_PATH,
        "control_table_path": CARD_CONTROL_TABLE_PATH,
    },
    "users": {
        "landing_path": USER_LANDING_PATH,
        "bronze_output_path": USER_BRONZE_OUTPUT_PATH,
        "control_table_path": USER_CONTROL_TABLE_PATH,
    },
}


def ingest_registered_source_domain(
    domain_name: str,
    landing_path: Path,
    bronze_output_path: Path,
    control_table_path: Path,
) -> dict:
    """
    Ingest one registered source domain into Bronze.

    Parameters
    ----------
    domain_name
        Name of a domain registered in SOURCE_SCHEMA_REGISTRY.

    landing_path
        Directory containing incoming CSV files.

    bronze_output_path
        Consolidated Bronze Parquet output path.

    control_table_path
        Domain-specific metadata control-table path.

    Returns
    -------
    dict
        Source-domain execution metrics.
    """

    normalized_domain_name = (
        domain_name
        .strip()
        .lower()
    )

    if (
        normalized_domain_name
        not in SOURCE_SCHEMA_REGISTRY
    ):
        available_domains = sorted(
            SOURCE_SCHEMA_REGISTRY
        )

        raise ValueError(
            "Unknown source domain: "
            f"{domain_name}. "
            "Available domains: "
            f"{available_domains}"
        )

    landing_path = Path(
        landing_path
    )

    bronze_output_path = Path(
        bronze_output_path
    )

    control_table_path = Path(
        control_table_path
    )

    landing_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    bronze_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    control_table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    schema_contract = (
        SOURCE_SCHEMA_REGISTRY[
            normalized_domain_name
        ]
    )

    ingestion_result = (
        ingest_landing_csv_files(
            landing_path=landing_path,
            bronze_output_path=(
                bronze_output_path
            ),
            control_table_path=(
                control_table_path
            ),
            expected_columns=(
                schema_contract[
                    "required_columns"
                ]
            ),
            expected_dtypes=(
                schema_contract[
                    "expected_dtypes"
                ]
            ),
        )
    )

    return {
        "source_domain": (
            normalized_domain_name
        ),
        **ingestion_result,
    }


def ingest_card_and_user_sources() -> dict:
    """
    Ingest the card and user source domains.

    Each domain is processed independently. A failure in one domain
    is recorded without preventing the other domain from being
    evaluated.

    The aggregate result is successful only when both domains
    complete successfully.
    """

    domain_results = {}

    for (
        domain_name,
        runtime_config,
    ) in DOMAIN_RUNTIME_CONFIG.items():
        try:
            domain_result = (
                ingest_registered_source_domain(
                    domain_name=domain_name,
                    landing_path=(
                        runtime_config[
                            "landing_path"
                        ]
                    ),
                    bronze_output_path=(
                        runtime_config[
                            "bronze_output_path"
                        ]
                    ),
                    control_table_path=(
                        runtime_config[
                            "control_table_path"
                        ]
                    ),
                )
            )

        except Exception as error:
            domain_result = {
                "source_domain": domain_name,
                "status": "FAILED",
                "landing_path": str(
                    runtime_config[
                        "landing_path"
                    ]
                ),
                "bronze_output_path": str(
                    runtime_config[
                        "bronze_output_path"
                    ]
                ),
                "files_discovered": 0,
                "files_processed": 0,
                "files_skipped": 0,
                "files_failed": 1,
                "rows_read": 0,
                "rows_written": 0,
                "bronze_total_rows": 0,
                "file_results": [],
                "error_message": (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            }

        domain_results[
            domain_name
        ] = domain_result

    domain_statuses = [
        result["status"]
        for result in domain_results.values()
    ]

    if all(
        status == "SUCCESS"
        for status in domain_statuses
    ):
        overall_status = "SUCCESS"

    elif any(
        status in {
            "SUCCESS",
            "PARTIAL_SUCCESS",
        }
        for status in domain_statuses
    ):
        overall_status = "PARTIAL_SUCCESS"

    else:
        overall_status = "FAILED"

    domains_succeeded = sum(
        status == "SUCCESS"
        for status in domain_statuses
    )

    domains_failed = sum(
        status != "SUCCESS"
        for status in domain_statuses
    )

    return {
        "status": overall_status,
        "domains_discovered": len(
            DOMAIN_RUNTIME_CONFIG
        ),
        "domains_succeeded": (
            domains_succeeded
        ),
        "domains_failed": (
            domains_failed
        ),
        "files_discovered": sum(
            result.get(
                "files_discovered",
                0,
            )
            for result in domain_results.values()
        ),
        "files_processed": sum(
            result.get(
                "files_processed",
                0,
            )
            for result in domain_results.values()
        ),
        "files_skipped": sum(
            result.get(
                "files_skipped",
                0,
            )
            for result in domain_results.values()
        ),
        "files_failed": sum(
            result.get(
                "files_failed",
                0,
            )
            for result in domain_results.values()
        ),
        "rows_read": sum(
            result.get(
                "rows_read",
                0,
            )
            for result in domain_results.values()
        ),
        "rows_written": sum(
            result.get(
                "rows_written",
                0,
            )
            for result in domain_results.values()
        ),
        "domain_results": domain_results,
    }


def print_domain_ingestion_summary(
    ingestion_result: dict,
) -> None:
    """
    Print readable execution metrics for the two domains.
    """

    print("=" * 70)
    print("CARD AND USER BRONZE INGESTION")
    print("=" * 70)

    for domain_name, domain_result in (
        ingestion_result[
            "domain_results"
        ].items()
    ):
        print()
        print(
            domain_name.upper()
        )
        print("-" * 70)

        pprint(
            domain_result,
            sort_dicts=False,
        )

    print()
    print("=" * 70)
    print("DOMAIN INGESTION SUMMARY")
    print("=" * 70)
    print(
        "Overall status: "
        f"{ingestion_result['status']}"
    )
    print(
        "Domains discovered: "
        f"{ingestion_result['domains_discovered']}"
    )
    print(
        "Domains succeeded: "
        f"{ingestion_result['domains_succeeded']}"
    )
    print(
        "Domains failed: "
        f"{ingestion_result['domains_failed']}"
    )
    print(
        "Files discovered: "
        f"{ingestion_result['files_discovered']}"
    )
    print(
        "Files processed: "
        f"{ingestion_result['files_processed']}"
    )
    print(
        "Files skipped: "
        f"{ingestion_result['files_skipped']}"
    )
    print(
        "Files failed: "
        f"{ingestion_result['files_failed']}"
    )
    print(
        "Rows read: "
        f"{ingestion_result['rows_read']}"
    )
    print(
        "Rows written: "
        f"{ingestion_result['rows_written']}"
    )
    print("=" * 70)


def main() -> None:
    """
    Command-line entry point.
    """

    ingestion_result = (
        ingest_card_and_user_sources()
    )

    print_domain_ingestion_summary(
        ingestion_result
    )

    if (
        ingestion_result["status"]
        != "SUCCESS"
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()