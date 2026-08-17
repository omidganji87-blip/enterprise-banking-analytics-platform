# ============================================================
# Enterprise Banking Analytics Dashboard
# ============================================================

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# Application configuration
# ============================================================

st.set_page_config(
    page_title="Enterprise Banking Analytics",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ANALYTICS_DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "analytics"
    / "banking_analytics.duckdb"
)


# ============================================================
# Styling
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        [data-testid="stMetric"] {
            background-color: rgba(120, 120, 120, 0.08);
            border: 1px solid rgba(120, 120, 120, 0.18);
            border-radius: 0.75rem;
            padding: 1rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(120, 120, 120, 0.18);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Database validation
# ============================================================

if not ANALYTICS_DATABASE_PATH.exists():
    st.error(
        "The analytics database does not exist."
    )

    st.write(
        "Run the complete pipeline before starting "
        "the dashboard:"
    )

    st.code(
        "python -m pipelines.run_pipeline",
        language="powershell",
    )

    st.stop()


# ============================================================
# Cached SQL query function
# ============================================================

@st.cache_data(ttl=60)
def run_query(
    sql: str,
    parameters: tuple = (),
) -> pd.DataFrame:
    """
    Execute a read-only DuckDB query and return a DataFrame.

    Each connection is closed immediately after the query,
    preventing database locks and lingering WAL files.
    """

    connection = duckdb.connect(
        str(ANALYTICS_DATABASE_PATH),
        read_only=True,
    )

    try:
        return connection.execute(
            sql,
            parameters,
        ).fetchdf()

    finally:
        connection.close()


# ============================================================
# Filter helpers
# ============================================================

def build_filter_clause(
    selected_years: tuple[int, ...],
    selected_methods: tuple[str, ...],
) -> tuple[str, tuple]:
    """
    Build a parameterized SQL WHERE clause.
    """

    conditions = []
    parameters = []

    if selected_years:
        year_placeholders = ", ".join(
            ["?"] * len(selected_years)
        )

        conditions.append(
            "d.calendar_year IN "
            f"({year_placeholders})"
        )

        parameters.extend(selected_years)

    if selected_methods:
        method_placeholders = ", ".join(
            ["?"] * len(selected_methods)
        )

        conditions.append(
            "f.transaction_method IN "
            f"({method_placeholders})"
        )

        parameters.extend(selected_methods)

    if not conditions:
        return "", tuple()

    return (
        "WHERE " + " AND ".join(conditions),
        tuple(parameters),
    )


# ============================================================
# Application title
# ============================================================

st.title("🏦 Enterprise Banking Analytics")

st.caption(
    "Interactive analytics over the validated Gold dimensional "
    "model and DuckDB serving layer."
)


# ============================================================
# Load filter values
# ============================================================

available_years_df = run_query(
    """
    SELECT DISTINCT
        calendar_year

    FROM dim_date

    ORDER BY
        calendar_year
    """
)

available_methods_df = run_query(
    """
    SELECT DISTINCT
        transaction_method

    FROM fact_transaction

    WHERE transaction_method IS NOT NULL

    ORDER BY
        transaction_method
    """
)


year_options = [
    int(year)
    for year in available_years_df[
        "calendar_year"
    ].tolist()
]

method_options = (
    available_methods_df[
        "transaction_method"
    ]
    .astype(str)
    .tolist()
)


# ============================================================
# Sidebar filters
# ============================================================

st.sidebar.header("Dashboard Filters")

selected_years = st.sidebar.multiselect(
    "Calendar year",
    options=year_options,
    default=year_options,
)

selected_methods = st.sidebar.multiselect(
    "Transaction method",
    options=method_options,
    default=method_options,
)


if st.sidebar.button(
    "Refresh analytics",
    width="stretch",
):
    st.cache_data.clear()
    st.rerun()


st.sidebar.divider()

st.sidebar.caption(
    "Analytics database"
)

st.sidebar.code(
    str(ANALYTICS_DATABASE_PATH),
    language=None,
)


where_clause, query_parameters = (
    build_filter_clause(
        selected_years=tuple(
            selected_years
        ),
        selected_methods=tuple(
            selected_methods
        ),
    )
)


# ============================================================
# Filtered KPI query
# ============================================================

kpi_df = run_query(
    f"""
    SELECT
        COUNT(*) AS total_transactions,

        COALESCE(
            ROUND(
                SUM(f.transaction_amount),
                2
            ),
            0
        ) AS total_transaction_amount,

        COALESCE(
            ROUND(
                AVG(f.transaction_amount),
                2
            ),
            0
        ) AS average_transaction_amount,

        COALESCE(
            SUM(
                CASE
                    WHEN f.is_fraud THEN 1
                    ELSE 0
                END
            ),
            0
        ) AS fraudulent_transactions,

        COALESCE(
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
            ),
            0
        ) AS fraud_transaction_rate_percent

    FROM fact_transaction AS f

    INNER JOIN dim_date AS d
        ON f.date_key = d.date_key

    {where_clause}
    """,
    query_parameters,
)


kpis = kpi_df.iloc[0]


# ============================================================
# KPI cards
# ============================================================

kpi_column_1, kpi_column_2, kpi_column_3, \
    kpi_column_4, kpi_column_5 = st.columns(5)


kpi_column_1.metric(
    "Transactions",
    f"{int(kpis['total_transactions']):,}",
)

kpi_column_2.metric(
    "Transaction amount",
    (
        "$"
        f"{float(kpis['total_transaction_amount']):,.2f}"
    ),
)

kpi_column_3.metric(
    "Average amount",
    (
        "$"
        f"{float(kpis['average_transaction_amount']):,.2f}"
    ),
)

kpi_column_4.metric(
    "Fraudulent transactions",
    f"{int(kpis['fraudulent_transactions']):,}",
)

kpi_column_5.metric(
    "Fraud rate",
    (
        f"{float(kpis['fraud_transaction_rate_percent']):.2f}%"
    ),
)


st.divider()


# ============================================================
# Dashboard tabs
# ============================================================

overview_tab, fraud_tab, merchant_tab, data_tab = (
    st.tabs(
        [
            "Overview",
            "Fraud Analysis",
            "Merchant Analysis",
            "Transaction Data",
        ]
    )
)


# ============================================================
# Overview tab
# ============================================================

with overview_tab:
    annual_summary_df = run_query(
        f"""
        SELECT
            d.calendar_year,

            COUNT(*) AS transaction_count,

            ROUND(
                SUM(f.transaction_amount),
                2
            ) AS total_transaction_amount,

            SUM(
                CASE
                    WHEN f.is_fraud THEN 1
                    ELSE 0
                END
            ) AS fraudulent_transactions

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        {where_clause}

        GROUP BY
            d.calendar_year

        ORDER BY
            d.calendar_year
        """,
        query_parameters,
    )

    method_summary_df = run_query(
        f"""
        SELECT
            f.transaction_method,

            COUNT(*) AS transaction_count,

            ROUND(
                SUM(f.transaction_amount),
                2
            ) AS total_transaction_amount,

            ROUND(
                AVG(f.transaction_amount),
                2
            ) AS average_transaction_amount

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        {where_clause}

        GROUP BY
            f.transaction_method

        ORDER BY
            transaction_count DESC
        """,
        query_parameters,
    )

    overview_column_1, overview_column_2 = (
        st.columns(2)
    )

    with overview_column_1:
        st.subheader(
            "Annual transaction activity"
        )

        annual_figure = px.line(
            annual_summary_df,
            x="calendar_year",
            y="total_transaction_amount",
            markers=True,
            labels={
                "calendar_year": "Calendar year",
                "total_transaction_amount": (
                    "Transaction amount"
                ),
            },
        )

        annual_figure.update_traces(
            line_color="#1f77b4",
            line_width=3,
        )

        annual_figure.update_layout(
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        st.plotly_chart(
            annual_figure,
            width="stretch",
            key="annual_transaction_chart",
        )

    with overview_column_2:
        st.subheader(
            "Transactions by method"
        )

        method_figure = px.bar(
            method_summary_df,
            x="transaction_method",
            y="transaction_count",
            color="transaction_method",
            labels={
                "transaction_method": (
                    "Transaction method"
                ),
                "transaction_count": (
                    "Transactions"
                ),
            },
        )

        method_figure.update_layout(
            showlegend=False,
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        st.plotly_chart(
            method_figure,
            width="stretch",
            key="transaction_method_chart",
        )

    st.subheader(
        "Annual summary"
    )

    st.dataframe(
        annual_summary_df,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# Fraud-analysis tab
# ============================================================

with fraud_tab:
    fraud_by_method_df = run_query(
        f"""
        SELECT
            f.transaction_method,

            COUNT(*) AS transaction_count,

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
            ) AS fraud_rate_percent

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        {where_clause}

        GROUP BY
            f.transaction_method

        ORDER BY
            fraud_rate_percent DESC
        """,
        query_parameters,
    )

    annual_fraud_df = run_query(
        f"""
        SELECT
            d.calendar_year,

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
            ) AS fraud_rate_percent

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        {where_clause}

        GROUP BY
            d.calendar_year

        ORDER BY
            d.calendar_year
        """,
        query_parameters,
    )

    fraud_column_1, fraud_column_2 = (
        st.columns(2)
    )

    with fraud_column_1:
        st.subheader(
            "Fraud rate by transaction method"
        )

        fraud_method_figure = px.bar(
            fraud_by_method_df,
            x="transaction_method",
            y="fraud_rate_percent",
            color="transaction_method",
            text="fraud_rate_percent",
            labels={
                "transaction_method": (
                    "Transaction method"
                ),
                "fraud_rate_percent": (
                    "Fraud rate (%)"
                ),
            },
        )

        fraud_method_figure.update_layout(
            showlegend=False,
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        st.plotly_chart(
            fraud_method_figure,
            width="stretch",
            key="fraud_method_chart",
        )

    with fraud_column_2:
        st.subheader(
            "Annual fraudulent transactions"
        )

        annual_fraud_figure = px.line(
            annual_fraud_df,
            x="calendar_year",
            y="fraudulent_transactions",
            markers=True,
            labels={
                "calendar_year": "Calendar year",
                "fraudulent_transactions": (
                    "Fraudulent transactions"
                ),
            },
        )

        annual_fraud_figure.update_traces(
            line_color="#d62728",
            line_width=3,
        )

        annual_fraud_figure.update_layout(
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        st.plotly_chart(
            annual_fraud_figure,
            width="stretch",
            key="annual_fraud_chart",
        )

    st.subheader(
        "Fraud summary by transaction method"
    )

    st.dataframe(
        fraud_by_method_df,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# Merchant-analysis tab
# ============================================================

with merchant_tab:
    merchant_state_df = run_query(
        f"""
        SELECT
            COALESCE(
                NULLIF(
                    TRIM(
                        CAST(
                            m.merchant_state
                            AS VARCHAR
                        )
                    ),
                    ''
                ),
                'UNKNOWN'
            ) AS merchant_state,

            COUNT(*) AS transaction_count,

            ROUND(
                SUM(f.transaction_amount),
                2
            ) AS total_transaction_amount,

            SUM(
                CASE
                    WHEN f.is_fraud THEN 1
                    ELSE 0
                END
            ) AS fraudulent_transactions

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        INNER JOIN dim_merchant AS m
            ON f.merchant_key = m.merchant_key

        {where_clause}

        GROUP BY
            merchant_state

        ORDER BY
            total_transaction_amount DESC

        LIMIT 15
        """,
        query_parameters,
    )

    merchant_category_df = run_query(
        f"""
        SELECT
            f.merchant_category_code,

            COUNT(*) AS transaction_count,

            ROUND(
                SUM(f.transaction_amount),
                2
            ) AS total_transaction_amount,

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
            ) AS fraud_rate_percent

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        {where_clause}

        GROUP BY
            f.merchant_category_code

        ORDER BY
            transaction_count DESC

        LIMIT 15
        """,
        query_parameters,
    )

    merchant_column_1, merchant_column_2 = (
        st.columns(2)
    )

    with merchant_column_1:
        st.subheader(
            "Top merchant states by amount"
        )

        state_figure = px.bar(
            merchant_state_df.sort_values(
                "total_transaction_amount"
            ),
            x="total_transaction_amount",
            y="merchant_state",
            orientation="h",
            labels={
                "merchant_state": "Merchant state",
                "total_transaction_amount": (
                    "Transaction amount"
                ),
            },
        )

        state_figure.update_traces(
            marker_color="#2ca02c"
        )

        state_figure.update_layout(
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        st.plotly_chart(
            state_figure,
            width="stretch",
            key="merchant_state_chart",
        )

    with merchant_column_2:
        st.subheader(
            "Top merchant categories"
        )

        category_figure = px.bar(
            merchant_category_df,
            x=(
                merchant_category_df[
                    "merchant_category_code"
                ].astype(str)
            ),
            y="transaction_count",
            labels={
                "x": "Merchant category code",
                "transaction_count": (
                    "Transactions"
                ),
            },
        )

        category_figure.update_traces(
            marker_color="#9467bd"
        )

        category_figure.update_layout(
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
        )

        st.plotly_chart(
            category_figure,
            width="stretch",
            key="merchant_category_chart",
        )

    st.subheader(
        "Merchant-category risk summary"
    )

    st.dataframe(
        merchant_category_df,
        width="stretch",
        hide_index=True,
    )


# ============================================================
# Transaction-data tab
# ============================================================

with data_tab:
    transaction_sample_df = run_query(
        f"""
        SELECT
            f.transaction_key,
            f.transaction_timestamp,
            f.transaction_amount,
            f.transaction_method,
            f.is_fraud,
            f.transaction_error,
            f.merchant_category_code,
            m.merchant_city,
            m.merchant_state,
            d.calendar_year

        FROM fact_transaction AS f

        INNER JOIN dim_date AS d
            ON f.date_key = d.date_key

        INNER JOIN dim_merchant AS m
            ON f.merchant_key = m.merchant_key

        {where_clause}

        ORDER BY
            f.transaction_timestamp DESC

        LIMIT 500
        """,
        query_parameters,
    )

    st.subheader(
        "Filtered transaction sample"
    )

    st.caption(
        "The table displays a maximum of 500 transactions."
    )

    st.dataframe(
        transaction_sample_df,
        width="stretch",
        hide_index=True,
    )

    transaction_csv = (
        transaction_sample_df.to_csv(
            index=False
        ).encode("utf-8")
    )

    st.download_button(
        label="Download filtered sample as CSV",
        data=transaction_csv,
        file_name=(
            "banking_transaction_sample.csv"
        ),
        mime="text/csv",
    )


# ============================================================
# Footer
# ============================================================

st.divider()

st.caption(
    "Enterprise Banking Analytics Platform · "
    "Validated Gold model · DuckDB serving layer"
)