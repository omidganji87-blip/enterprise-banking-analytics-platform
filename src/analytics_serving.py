from pathlib import Path

import duckdb


ANALYTICS_VIEW_NAMES = [
    "dim_merchant",
    "dim_date",
    "fact_transaction",
    "vw_platform_kpis",
    "vw_transaction_method_summary",
    "vw_annual_transaction_summary",
]


def _prepare_sql_path(file_path: Path) -> str:
    """
    Convert a filesystem path into a safely escaped path that
    can be used inside a DuckDB SQL string.
    """

    return (
        file_path
        .resolve()
        .as_posix()
        .replace("'", "''")
    )


def validate_analytics_inputs(
    merchant_input_path: Path,
    date_input_path: Path,
    transaction_input_path: Path,
) -> None:
    """
    Validate that all required Gold Parquet files exist.

    Raises
    ------
    FileNotFoundError
        If one or more required Gold files do not exist.
    """

    required_files = [
        merchant_input_path,
        date_input_path,
        transaction_input_path,
    ]

    missing_files = [
        file_path
        for file_path in required_files
        if not file_path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "The analytics serving layer cannot be created "
            "because these Gold files are missing:\n"
            + "\n".join(
                str(file_path)
                for file_path in missing_files
            )
        )


def create_gold_views(
    connection: duckdb.DuckDBPyConnection,
    merchant_input_path: Path,
    date_input_path: Path,
    transaction_input_path: Path,
) -> None:
    """
    Register the persisted Gold Parquet tables as DuckDB views.
    """

    merchant_sql_path = _prepare_sql_path(
        merchant_input_path
    )

    date_sql_path = _prepare_sql_path(
        date_input_path
    )

    transaction_sql_path = _prepare_sql_path(
        transaction_input_path
    )

    connection.execute(
        f"""
        CREATE OR REPLACE VIEW dim_merchant AS
        SELECT *
        FROM read_parquet('{merchant_sql_path}');
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE VIEW dim_date AS
        SELECT *
        FROM read_parquet('{date_sql_path}');
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE VIEW fact_transaction AS
        SELECT *
        FROM read_parquet('{transaction_sql_path}');
        """
    )


def create_analytics_views(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """
    Create reusable analytical views for reporting and business
    intelligence consumers.
    """

    # --------------------------------------------------------
    # Platform-level KPI view
    # --------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE VIEW vw_platform_kpis AS

        SELECT
            COUNT(*) AS total_transactions,

            ROUND(
                SUM(transaction_amount),
                2
            ) AS total_transaction_amount,

            ROUND(
                AVG(transaction_amount),
                2
            ) AS average_transaction_amount,

            SUM(
                CASE
                    WHEN is_fraud THEN 1
                    ELSE 0
                END
            ) AS fraudulent_transactions,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN is_fraud THEN 1
                        ELSE 0
                    END
                )
                / NULLIF(COUNT(*), 0),
                2
            ) AS fraud_transaction_rate_percent

        FROM fact_transaction;
        """
    )

    # --------------------------------------------------------
    # Transaction-method summary view
    # --------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE VIEW
            vw_transaction_method_summary AS

        SELECT
            transaction_method,

            COUNT(*) AS transaction_count,

            ROUND(
                SUM(transaction_amount),
                2
            ) AS total_transaction_amount,

            ROUND(
                AVG(transaction_amount),
                2
            ) AS average_transaction_amount,

            SUM(
                CASE
                    WHEN is_fraud THEN 1
                    ELSE 0
                END
            ) AS fraudulent_transactions,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN is_fraud THEN 1
                        ELSE 0
                    END
                )
                / NULLIF(COUNT(*), 0),
                2
            ) AS fraud_transaction_rate_percent

        FROM fact_transaction

        GROUP BY
            transaction_method;
        """
    )

    # --------------------------------------------------------
    # Annual transaction summary view
    # --------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE VIEW
            vw_annual_transaction_summary AS

        SELECT
            d.calendar_year,

            COUNT(*) AS transaction_count,

            ROUND(
                SUM(f.transaction_amount),
                2
            ) AS total_transaction_amount,

            ROUND(
                AVG(f.transaction_amount),
                2
            ) AS average_transaction_amount,

            SUM(
                CASE
                    WHEN f.is_fraud THEN 1
                    ELSE 0
                END
            ) AS fraudulent_transactions,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN f.is_fraud THEN 1
                        ELSE 0
                    END
                )
                / NULLIF(COUNT(*), 0),
                2
            ) AS fraud_transaction_rate_percent

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        GROUP BY
            d.calendar_year;
        """
    )


def validate_analytics_model(
    connection: duckdb.DuckDBPyConnection,
) -> dict:
    """
    Validate row counts, primary keys, and foreign-key
    relationships through SQL.
    """

    row_counts = connection.execute(
        """
        SELECT
            (
                SELECT COUNT(*)
                FROM dim_merchant
            ) AS merchant_rows,

            (
                SELECT COUNT(*)
                FROM dim_date
            ) AS date_rows,

            (
                SELECT COUNT(*)
                FROM fact_transaction
            ) AS transaction_rows
        """
    ).fetchone()

    (
        merchant_rows,
        date_rows,
        transaction_rows,
    ) = row_counts

    primary_key_result = connection.execute(
        """
        SELECT
            (
                SELECT
                    COUNT(*)
                    - COUNT(DISTINCT merchant_key)
                FROM dim_merchant
            ) AS duplicate_merchant_keys,

            (
                SELECT
                    COUNT(*)
                    - COUNT(DISTINCT date_key)
                FROM dim_date
            ) AS duplicate_date_keys,

            (
                SELECT
                    COUNT(*)
                    - COUNT(DISTINCT transaction_key)
                FROM fact_transaction
            ) AS duplicate_transaction_keys,

            (
                SELECT
                    SUM(
                        CASE
                            WHEN merchant_key IS NULL
                                THEN 1
                            ELSE 0
                        END
                    )
                FROM dim_merchant
            ) AS missing_merchant_keys,

            (
                SELECT
                    SUM(
                        CASE
                            WHEN date_key IS NULL
                                THEN 1
                            ELSE 0
                        END
                    )
                FROM dim_date
            ) AS missing_date_keys,

            (
                SELECT
                    SUM(
                        CASE
                            WHEN transaction_key IS NULL
                                THEN 1
                            ELSE 0
                        END
                    )
                FROM fact_transaction
            ) AS missing_transaction_keys
        """
    ).fetchone()

    (
        duplicate_merchant_keys,
        duplicate_date_keys,
        duplicate_transaction_keys,
        missing_merchant_keys,
        missing_date_keys,
        missing_transaction_keys,
    ) = primary_key_result

    foreign_key_result = connection.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN m.merchant_key IS NULL
                        THEN 1
                    ELSE 0
                END
            ) AS invalid_merchant_foreign_keys,

            SUM(
                CASE
                    WHEN d.date_key IS NULL
                        THEN 1
                    ELSE 0
                END
            ) AS invalid_date_foreign_keys

        FROM fact_transaction AS f

        LEFT JOIN dim_merchant AS m
            ON f.merchant_key = m.merchant_key

        LEFT JOIN dim_date AS d
            ON f.date_key = d.date_key
        """
    ).fetchone()

    (
        invalid_merchant_foreign_keys,
        invalid_date_foreign_keys,
    ) = foreign_key_result

    validation_result = {
        "merchant_rows": int(merchant_rows),
        "date_rows": int(date_rows),
        "transaction_rows": int(
            transaction_rows
        ),
        "duplicate_merchant_keys": int(
            duplicate_merchant_keys or 0
        ),
        "duplicate_date_keys": int(
            duplicate_date_keys or 0
        ),
        "duplicate_transaction_keys": int(
            duplicate_transaction_keys or 0
        ),
        "missing_merchant_keys": int(
            missing_merchant_keys or 0
        ),
        "missing_date_keys": int(
            missing_date_keys or 0
        ),
        "missing_transaction_keys": int(
            missing_transaction_keys or 0
        ),
        "invalid_merchant_foreign_keys": int(
            invalid_merchant_foreign_keys or 0
        ),
        "invalid_date_foreign_keys": int(
            invalid_date_foreign_keys or 0
        ),
    }

    validation_result["is_valid"] = all(
        [
            validation_result[
                "merchant_rows"
            ] > 0,
            validation_result[
                "date_rows"
            ] > 0,
            validation_result[
                "transaction_rows"
            ] > 0,
            validation_result[
                "duplicate_merchant_keys"
            ] == 0,
            validation_result[
                "duplicate_date_keys"
            ] == 0,
            validation_result[
                "duplicate_transaction_keys"
            ] == 0,
            validation_result[
                "missing_merchant_keys"
            ] == 0,
            validation_result[
                "missing_date_keys"
            ] == 0,
            validation_result[
                "missing_transaction_keys"
            ] == 0,
            validation_result[
                "invalid_merchant_foreign_keys"
            ] == 0,
            validation_result[
                "invalid_date_foreign_keys"
            ] == 0,
        ]
    )

    if not validation_result["is_valid"]:
        raise ValueError(
            "Analytics serving-layer validation failed: "
            f"{validation_result}"
        )

    return validation_result


def read_platform_kpis(
    connection: duckdb.DuckDBPyConnection,
) -> dict:
    """
    Read the platform-level KPI view and return scalar metrics.
    """

    kpi_row = connection.execute(
        """
        SELECT
            total_transactions,
            total_transaction_amount,
            average_transaction_amount,
            fraudulent_transactions,
            fraud_transaction_rate_percent

        FROM vw_platform_kpis
        """
    ).fetchone()

    return {
        "total_transactions": int(
            kpi_row[0]
        ),
        "total_transaction_amount": float(
            kpi_row[1] or 0
        ),
        "average_transaction_amount": float(
            kpi_row[2] or 0
        ),
        "fraudulent_transactions": int(
            kpi_row[3] or 0
        ),
        "fraud_transaction_rate_percent": float(
            kpi_row[4] or 0
        ),
    }


def build_analytics_serving_layer(
    merchant_input_path: Path,
    date_input_path: Path,
    transaction_input_path: Path,
    analytics_database_path: Path,
) -> dict:
    """
    Build and validate the reusable DuckDB analytics serving
    layer over the persisted Gold Parquet model.

    Processing flow
    ---------------
    1. Validate the required Gold files.
    2. Create the analytics database directory.
    3. Connect to DuckDB.
    4. Register the three Gold tables as SQL views.
    5. Create reusable analytical summary views.
    6. Validate keys and relationships through SQL.
    7. Read platform-level KPI metrics.
    8. Close the database connection safely.
    9. Return execution metrics.
    """

    merchant_input_path = Path(
        merchant_input_path
    )

    date_input_path = Path(
        date_input_path
    )

    transaction_input_path = Path(
        transaction_input_path
    )

    analytics_database_path = Path(
        analytics_database_path
    )

    validate_analytics_inputs(
        merchant_input_path=merchant_input_path,
        date_input_path=date_input_path,
        transaction_input_path=(
            transaction_input_path
        ),
    )

    analytics_database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(
        str(analytics_database_path)
    )

    try:
        create_gold_views(
            connection=connection,
            merchant_input_path=(
                merchant_input_path
            ),
            date_input_path=date_input_path,
            transaction_input_path=(
                transaction_input_path
            ),
        )

        create_analytics_views(
            connection=connection
        )

        validation_result = (
            validate_analytics_model(
                connection=connection
            )
        )

        platform_kpis = read_platform_kpis(
            connection=connection
        )

        return {
            "status": "SUCCESS",
            "analytics_database_path": str(
                analytics_database_path
            ),
            "merchant_input_path": str(
                merchant_input_path
            ),
            "date_input_path": str(
                date_input_path
            ),
            "transaction_input_path": str(
                transaction_input_path
            ),
            "views_created": (
                ANALYTICS_VIEW_NAMES.copy()
            ),
            "validation": validation_result,
            "platform_kpis": platform_kpis,
        }

    finally:
        # The finally block guarantees that DuckDB closes even
        # when validation or SQL execution raises an exception.
        connection.close()