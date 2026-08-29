# Enterprise Banking Analytics Platform

[![Enterprise Banking Platform CI](https://github.com/omidganji87-blip/enterprise-banking-analytics-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/omidganji87-blip/enterprise-banking-analytics-platform/actions/workflows/ci.yml)

A production-style local data engineering and analytics platform that processes credit-card transaction data through Bronze, Silver, Gold, analytical, and Power BI publication layers.

The project demonstrates multi-domain ingestion, schema validation, data-quality quarantine, dimensional modeling, SQL analytics, a tested Power BI serving contract, automated orchestration, and two interactive reporting experiences.

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
Power BI Publication Layer
    ├── Curated Parquet tables
    ├── Derived reporting fields
    ├── Persisted-model validation
    └── Explicit BI schema contract
    │
    ├──► Enterprise Banking Intelligence Command Center
    │     ├── Executive Overview
    │     ├── Risk & Exceptions
    │     ├── Merchant Risk
    │     └── Merchant Detail drill-through
    │
    └──► Streamlit Dashboard
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
- `merchant_id_text`
- `merchant_display_label`
- `merchant_city`
- `merchant_state`
- `merchant_zip_code`
- `merchant_category_code`

`merchant_id` remains the signed 64-bit source identifier for lineage. The
serving layer also publishes its exact text form because report visuals render
through JavaScript and cannot safely display every 64-bit integer. Use the
compact `merchant_display_label` (`MRC-######`) in axes and drill-through UI,
and use `merchant_id_text` when the exact source identifier must be shown or
exported.

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

### Power BI serving layer

- Publishes an explicit three-table reporting contract from Gold.
- Adds `calendar_year_month` and its numeric sort field.
- Adds a Boolean `has_error` business flag.
- Reconciles source and serving row counts.
- Validates primary keys and both star-schema relationships.
- Reconciles transaction amount, fraud count, and error count to Gold.
- Writes typed and compressed Parquet files inside the project.
- Reloads every published file and proves that persistence preserved the data.
- Runs automatically as Stage 6 of the end-to-end pipeline.

### Reporting applications

The Power BI Command Center provides:

- An executive KPI and trend overview
- Risk and operational-exception analysis
- Fraud exposure and year-over-year comparisons
- Merchant category and geographic risk analysis
- Synchronized date filtering
- Page navigation and clear-filter controls
- A hidden merchant drill-through destination
- A curated measures table and star-schema semantic model

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
│   ├── app.py
│   └── Enterprise_Banking_Intelligence_Command_Center.pbix
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
│   ├── 05_gold_analytics.ipynb
│   └── 06_power_bi_serving_layer.ipynb
│
├── docs/
│   ├── power_bi_runbook.md
│   ├── production_readiness_checklist.md
│   └── report_qa.md
│
├── pipelines/
│   └── run_pipeline.py
│
├── scripts/
│   ├── get_pipeline_health.ps1
│   ├── register_scheduled_pipeline_task.ps1
│   └── run_scheduled_pipeline.ps1
│
├── src/
│   ├── __init__.py
│   ├── analytics_serving.py
│   ├── bronze_ingestion.py
│   ├── gold_data_model.py
│   ├── metadata_control.py
│   ├── power_bi_serving.py
│   ├── schema_validation.py
│   └── silver_transformation.py
│
├── tests/
│   ├── test_analytics_serving.py
│   ├── test_bronze_ingestion.py
│   ├── test_gold_data_model.py
│   ├── test_power_bi_serving.py
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
- Power BI Desktop
- Power Query M
- DAX
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
Stage 1 — Transaction Bronze ingestion
Stage 2 — Card and user Bronze ingestion
Stage 3 — Silver transformation and quarantine
Stage 4 — Gold dimensional model
Stage 5 — DuckDB analytics serving layer
Stage 6 — Power BI Parquet serving layer
```

A successful execution ends with:

```text
PIPELINE COMPLETED SUCCESSFULLY
```

When the source file was previously processed successfully, the Bronze stage returns:

```text
Bronze status: SKIPPED
```

This is expected idempotent behavior. The persisted Bronze output continues through Silver, Gold, Analytics, and Power BI publication.

## Run the guarded production workflow

The production wrapper tests the code, creates and verifies recovery copies of
the current Power BI files, runs all six pipeline stages, validates the new
publication, records machine-readable status, and removes runtime artifacts
older than 14 days.

From the project root, run:

```powershell
pwsh -NoProfile -File ".\scripts\run_scheduled_pipeline.ps1"
```

The wrapper uses these exit codes:

```text
0  Pipeline and publication completed successfully
1  Pipeline failed; previous validated publication was restored
2  Pipeline failed and recovery also failed
```

Operational outputs are intentionally excluded from Git:

```text
logs/scheduled_pipeline/
monitoring/scheduled_pipeline_status.json
data/backups/power_bi_serving/
```

Check the complete local refresh chain with:

```powershell
pwsh -NoProfile -File ".\scripts\get_pipeline_health.ps1"
```

The command verifies the latest pipeline status, Windows scheduled task,
on-premises data gateway service, and all three serving files.

### Automated local-to-Power-BI refresh sequence

The configured operating sequence is:

```text
05:00 America/Toronto  Windows Task Scheduler runs the guarded pipeline
06:00 America/Toronto  Power BI Service imports the three published Parquet files
```

Register or repair the Windows task from a PowerShell 7 terminal with:

```powershell
pwsh -NoProfile -File ".\scripts\register_scheduled_pipeline_task.ps1"
```

The current task uses interactive Windows credentials because unattended S4U
registration was denied on this workstation. `OMID\omidg` must remain signed
in; the workstation may be locked or sleeping because the task is configured to
wake it. It must remain powered on; wake-to-run cannot start a fully powered-off
computer. The gateway service and internet connection must be available for the
06:00 Power BI Service refresh. The two schedules are independent: a pipeline
run does not directly trigger a Power BI refresh.

## Open and refresh the Power BI report

Run the complete pipeline before refreshing Power BI. Then open:

```text
dashboard/Enterprise_Banking_Intelligence_Command_Center.pbix
```

In Power BI Desktop, select **Home > Refresh**. The report reads these three
project-managed files:

```text
data/analytics/dim_date_analytics.parquet
data/analytics/dim_merchant_analytics.parquet
data/analytics/fact_transaction_analytics.parquet
```

After a serving-contract or date-model change, keep the PBIX open and run the
idempotent semantic-model hardening command from a separate PowerShell 7
terminal:

```powershell
pwsh -NoProfile -File ".\scripts\harden_power_bi_model.ps1" `
    -RemoveAutoDateTables `
    -RefreshModel
```

The command preserves the source merchant ID as exact text, exposes the compact
merchant display label, hides the unsafe numeric display field, removes hidden
automatic date tables that can create cyclic refresh dependencies, and performs
a full local model refresh. Save the PBIX after it succeeds.

For a detailed, repeatable training guide covering import queries, Power Query,
relationships, sort columns, DAX, page design, refresh, validation, and
troubleshooting, see [Power BI Serving Layer and Dashboard Runbook](docs/power_bi_runbook.md).

For release gates, unattended-cycle acceptance, and enterprise hardening, see
[Production Readiness Checklist](docs/production_readiness_checklist.md).

For the current page inventory and remaining UX/accessibility checks, see
[Power BI Report QA](docs/report_qa.md).

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
55 passed
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
Error transactions:           574
Total transaction amount:     1,622,991.69
Average transaction amount:   81.30
```

All persisted Gold and Power BI primary-key, foreign-key, row-count, fraud,
error, and monetary-control validations pass.

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

## Power BI semantic model

The report imports three curated Parquet tables:

```text
dim_date_analytics[date_key]          1 ─── * fact_transaction_analytics[date_key]
dim_merchant_analytics[merchant_key]  1 ─── * fact_transaction_analytics[merchant_key]
```

Both relationships use single-direction filtering from the dimensions to the
fact. `dim_date_analytics` is marked as the Date table using `full_date`.
Business calculations are stored in a dedicated `_Measures` table.

Current validated publication controls:

```text
Power BI date rows:                 6,390
Power BI merchant rows:            1,106
Power BI transaction rows:        19,963
Invalid date foreign keys:             0
Invalid merchant foreign keys:         0
Power BI error transactions:         574
Power BI fraud transactions:          27
Power BI transaction amount: 1,622,991.69
```

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
- Update and test the Power BI serving contract before refreshing the PBIX after a Gold schema change.
- Keep Power BI query sources inside `data/analytics`; do not use temporary drive-root files.
- Keep the workstation signed in for the current interactive 05:00 scheduled task.
- Treat the 05:00 pipeline and 06:00 Power BI refresh as separate monitored jobs.
- Run `scripts/get_pipeline_health.ps1` after infrastructure or credential changes.
- The local dashboard should not be deployed until cloud-compatible data storage and paths are configured.

## Future enhancements

Potential next phases include:

- Centralized multi-host log aggregation
- Per-stage duration telemetry and alert delivery
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
- Power BI deployment pipelines and environment parameters
- Row-level security and governed workspace publication
- Automated semantic-model metadata checks

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

Validated Power BI serving contract
✓

Enterprise Power BI Command Center
✓

Interactive Streamlit dashboard
✓

End-to-end orchestration
✓

Guarded scheduled production execution and verified recovery
✓

Operational health and configuration-drift monitoring
✓

Automated test coverage
✓

Cross-platform GitHub CI for Python and operational PowerShell
✓

Four-page Power BI Desktop performance baseline
✓

Power BI KPI, keyboard-order, hidden-focus, and phone-layout remediation
✓
```

The local platform controls are implemented and validated. Published-service
rendering plus synchronized-date and clear-filter behavior were verified on
2026-08-29. The local PBIX now includes exact-safe merchant labels, a tested
Merchant Risk drill-through path, and package-verified descriptions for all
seven active analytical visuals. Three automated PBIX package tests bring the
local suite to 58 passing tests. Final production acceptance still requires a
successful fully unattended 05:00 pipeline plus 06:00 Power BI Service refresh
cycle, publication of the corrected PBIX, service tooltip/drill-through and
assistive-technology/device QA, and governed security and distribution controls
before real banking data is introduced.
