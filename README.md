# Enterprise Banking Analytics Platform

A production-style local data engineering and analytics platform that processes credit-card transaction data through Bronze, Silver, Gold, and analytical serving layers.

The project demonstrates data ingestion, schema validation, data-quality quarantine, dimensional modeling, SQL analytics, automated testing, pipeline orchestration, and an interactive Streamlit dashboard.

## Architecture

```text
Landing CSV
    │
    ▼
Bronze Layer
    ├── Source-schema validation
    ├── Audit metadata
    ├── File-level idempotency
    └── Parquet persistence
    │
    ▼
Silver Layer
    ├── Data cleaning
    ├── Type standardization
    ├── Business-rule validation
    ├── Valid records → Silver
    └── Invalid records → Quarantine
    │
    ▼
Gold Layer
    ├── dim_merchant
    ├── dim_date
    └── fact_transaction
    │
    ▼
Analytics Serving Layer
    ├── DuckDB database
    ├── Gold SQL views
    ├── KPI views
    └── Relationship validation
    │
    ▼
Streamlit Dashboard
    ├── Overview
    ├── Fraud analysis
    ├── Merchant analysis
    └── Transaction explorer
```

## Gold dimensional model

The central fact-table grain is:

> One row per credit-card transaction.

```text
                 dim_date
                    │
                    │ date_key
                    │
dim_merchant ── fact_transaction
 merchant_key
```

### `dim_merchant`

One row per unique merchant business record.

Important fields include:

- `merchant_key`
- `merchant_id`
- `merchant_city`
- `merchant_state`
- `merchant_zip_code`
- `merchant_category_code`

### `dim_date`

One row per calendar date across the complete transaction date range.

Important fields include:

- `date_key`
- `full_date`
- `calendar_year`
- `calendar_quarter`
- `calendar_month_number`
- `calendar_month_name`
- `calendar_day_of_month`
- `calendar_day_of_week_number`
- `calendar_day_name`
- `is_weekend`

### `fact_transaction`

One row per credit-card transaction.

Important fields include:

- `transaction_key`
- `date_key`
- `merchant_key`
- `user_id`
- `card_id`
- `transaction_timestamp`
- `transaction_amount`
- `transaction_method`
- `merchant_category_code`
- `transaction_error`
- `is_fraud`

## Main capabilities

### Bronze ingestion

- Reads the Landing CSV.
- Validates source columns and data types.
- Adds ingestion audit metadata.
- Writes the Bronze table as Parquet.
- Records successful processing in a metadata control table.
- Skips files that were already processed successfully.

### Silver transformation

- Standardizes column names.
- Converts identifiers to appropriate types.
- Parses transaction timestamps.
- Converts monetary values into numeric values.
- Standardizes transaction methods.
- Standardizes fraud indicators.
- Separates valid and invalid records.
- Writes rejected records to Quarantine.
- Reconciles Bronze rows with Silver and Quarantine rows.

### Gold dimensional model

- Creates a Merchant dimension.
- Creates a complete Date dimension.
- Creates the Transaction fact table.
- Generates surrogate keys.
- Validates primary keys.
- Validates merchant and date foreign keys.
- Persists and reloads all Gold tables.
- Revalidates the persisted model.

### Analytics serving layer

- Creates a local DuckDB database.
- Registers Gold Parquet tables as SQL views.
- Creates reusable analytical views.
- Validates the star schema through SQL.
- Calculates platform-level banking KPIs.
- Closes database connections safely.

### Dashboard

The Streamlit dashboard provides:

- Total transaction count
- Total transaction amount
- Average transaction amount
- Fraudulent transaction count
- Fraud transaction rate
- Annual transaction trends
- Transaction-method analysis
- Fraud analysis by transaction method
- Merchant-state analysis
- Merchant-category analysis
- Filtered transaction exploration
- CSV download support

## Project structure

```text
Enterprise-Banking-Analytics-Platform/
│
├── configs/
│   ├── __init__.py
│   ├── config.py
│   └── source_schemas.py
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── landing/
│   ├── bronze/
│   ├── silver/
│   ├── quarantine/
│   ├── gold/
│   ├── analytics/
│   └── metadata/
│
├── notebooks/
│   ├── 00_test_configuration.ipynb
│   ├── 01_source_data_discovery.ipynb
│   ├── 02_bronze_ingestion.ipynb
│   ├── 03_silver_transformation.ipynb
│   ├── 04_gold_data_model.ipynb
│   └── 05_gold_analytics.ipynb
│
├── pipelines/
│   └── run_pipeline.py
│
├── src/
│   ├── __init__.py
│   ├── analytics_serving.py
│   ├── bronze_ingestion.py
│   ├── gold_data_model.py
│   ├── metadata_control.py
│   ├── schema_validation.py
│   └── silver_transformation.py
│
├── tests/
│   ├── test_analytics_serving.py
│   ├── test_bronze_ingestion.py
│   ├── test_gold_data_model.py
│   ├── test_run_pipeline.py
│   ├── test_schema_validation.py
│   └── test_silver_transformation.py
│
├── .gitignore
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

## Technology stack

- Python 3.14
- pandas
- PyArrow
- DuckDB
- Streamlit
- Plotly
- pytest
- Jupyter and VS Code notebooks

## Environment setup

### 1. Create a virtual environment

From the project root:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install production dependencies

```powershell
python -m pip install -r requirements.txt
```

For development, notebooks, and automated testing:

```powershell
python -m pip install -r requirements-dev.txt
```

### 3. Verify installed dependencies

```powershell
python -m pip check
```

Expected:

```text
No broken requirements found.
```

## Source-data setup

Place the source transaction CSV at:

```text
data/landing/User0_credit_card_transactions.csv
```

The source file must satisfy the schema contract defined in:

```text
configs/source_schemas.py
```

Generated data files are excluded from Git because they may be large or sensitive.

## Run the complete pipeline

Always run commands from the project root.

```powershell
python -m pipelines.run_pipeline
```

The pipeline executes:

```text
Stage 1 — Bronze ingestion
Stage 2 — Silver transformation
Stage 3 — Gold dimensional model
Stage 4 — Analytics serving layer
```

A successful execution ends with:

```text
PIPELINE COMPLETED SUCCESSFULLY
```

When the source file was previously processed successfully, the Bronze stage returns:

```text
Bronze status: SKIPPED
```

This is expected idempotent behavior. The persisted Bronze output continues through Silver, Gold, and Analytics.

## Run the dashboard

From the project root:

```powershell
python -m streamlit run dashboard/app.py
```

Open the local URL shown in the terminal, normally:

```text
http://localhost:8501
```

Keep the terminal running while using the dashboard.

To stop the dashboard, press:

```text
Ctrl + C
```

## Run automated tests

Run the complete test suite:

```powershell
python -m pytest -v
```

Or use the concise output:

```powershell
python -m pytest -q
```

Current validated result:

```text
22 passed
```

Run an individual test module with:

```powershell
python -m pytest tests/test_gold_data_model.py -v
```

Do not run test files using the Python play button. Tests should be executed through pytest from the project root.

## Current sample-data results

For the current local sample dataset:

```text
Silver transactions:          19,963
Quarantine records:           0
Merchant dimension rows:      1,106
Date dimension rows:          6,390
Transaction fact rows:        19,963
Fraudulent transactions:      27
Fraud transaction rate:       0.14%
Total transaction amount:     1,622,991.69
Average transaction amount:   81.30
```

All persisted Gold primary-key and foreign-key validations pass.

## Analytics views

The DuckDB serving database contains these project views:

```text
dim_merchant
dim_date
fact_transaction
vw_platform_kpis
vw_transaction_method_summary
vw_annual_transaction_summary
```

The local database is created at:

```text
data/analytics/banking_analytics.duckdb
```

The database contains view definitions. The primary analytical data remains in the Gold Parquet files.

## Data-quality behavior

Invalid Silver records are written to:

```text
data/quarantine/credit_card_transactions_quarantine.parquet
```

Possible rejection reasons include:

```text
MISSING_USER_ID
MISSING_CARD_ID
INVALID_AMOUNT
INVALID_TRANSACTION_TIMESTAMP
INVALID_FRAUD_FLAG
```

The Silver transformation enforces this reconciliation:

```text
Bronze rows
=
Silver rows
+
Quarantine rows
```

## Important operational notes

- Run modules using `python -m` from the project root.
- Do not run reusable files under `src` directly.
- Do not manually delete a DuckDB `.wal` file while a database connection is active.
- Do not commit transaction data, Parquet files, DuckDB databases, secrets, or logs.
- Run the complete test suite after changing dependencies.
- Rebuild the analytics serving layer after changing Gold outputs.
- The local dashboard should not be deployed until cloud-compatible data storage and paths are configured.

## Future enhancements

Potential next phases include:

- Centralized pipeline execution logging
- Stage-duration and failure monitoring
- Command-line configuration
- Incremental Silver and Gold processing
- Slowly changing dimensions
- Customer and card dimensions
- Data-contract versioning
- CI/CD test automation
- Containerization with Docker
- Cloud object storage
- Managed orchestration
- Dashboard authentication
- Cloud dashboard deployment

## Project status

The current local platform supports:

```text
Schema validation
✓

Idempotent Bronze ingestion
✓

Silver cleaning and quarantine
✓

Gold dimensional modeling
✓

Persisted data-quality validation
✓

DuckDB analytics serving
✓

Interactive Streamlit dashboard
✓

End-to-end orchestration
✓

Automated test coverage
✓
```