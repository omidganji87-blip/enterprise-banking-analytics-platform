# Power BI Serving Layer and Dashboard Runbook

This guide explains how the Enterprise Banking Intelligence Command Center is
built, refreshed, validated, and maintained. It is written so that the same
approach can be repeated in a new analytics project.

## 1. The role of the Power BI serving layer

Power BI should not depend directly on raw Landing, Bronze, or Silver data.
Those layers exist for ingestion, traceability, cleaning, and quarantine. The
report consumes a small, explicit publication contract created from the Gold
star schema:

```text
Gold model
    |
    v
Power BI serving transformation
    |
    +-- dim_date_analytics.parquet
    +-- dim_merchant_analytics.parquet
    +-- fact_transaction_analytics.parquet
    |
    v
Power BI semantic model and report
```

This separation prevents an upstream engineering change from silently adding,
removing, or changing report fields. It also keeps report refreshes focused on
business-ready data.

## 2. Why the report imports Parquet

Parquet is a column-oriented, typed, compressed file format. It is a good local
serving format for this project because:

- Power BI reads only the columns required by the model.
- Numeric, Boolean, date, and text types are preserved more reliably than CSV.
- Compression makes the files smaller and refreshes faster.
- No CSV delimiter, quoting, or locale parsing is required.
- The same files are easy to test with pandas before Power BI sees them.

Parquet is the publication format, not the semantic model. Power BI still adds
relationships, display formats, sort behavior, measures, interactions, and
report design after importing the files.

The merchant publication deliberately provides three forms of identity:

- `merchant_id` is the signed 64-bit source value retained for lineage.
- `merchant_id_text` is the exact source value represented as text for display,
  drill-through, tooltips, and exports.
- `merchant_display_label` is a compact deterministic label such as
  `MRC-000001` for readable report axes.

This prevents the rounding that can occur when a browser-based visual renders a
64-bit integer through JavaScript. Hide the numeric source field in report view;
do not delete it from the serving contract.

## 3. Canonical project files

The pipeline writes the three report tables here:

```text
data/analytics/dim_date_analytics.parquet
data/analytics/dim_merchant_analytics.parquet
data/analytics/fact_transaction_analytics.parquet
```

The report file is:

```text
dashboard/Enterprise_Banking_Intelligence_Command_Center.pbix
```

The files belong inside the project. A temporary path such as
`D:\d.parquet` is unsuitable because it is not self-explanatory, portable, or
reproducible.

## 4. How the serving files are created

The reusable implementation is in `src/power_bi_serving.py`. The exploratory
and educational version is in `notebooks/06_power_bi_serving_layer.ipynb`.

The transformation performs these operations in order:

1. Verify that all three Gold Parquet inputs exist.
2. Verify that each Gold table contains its required reporting columns.
3. Select only the approved BI fields.
4. Create `calendar_year_month` as a readable `YYYY-MM` label.
5. Create `calendar_year_month_sort` as `year * 100 + month`.
6. Create `has_error` from `transaction_error`.
7. Validate row counts, primary keys, foreign keys, amounts, fraud counts, and
   error counts against Gold.
8. Write all three curated frames as Parquet.
9. Read all three files back from disk.
10. Compare the persisted frames with the in-memory frames and recheck both
    relationships.

The read-back check matters. A successful in-memory calculation does not prove
that the published files are complete and readable.

### Derived fields

`calendar_year_month` gives visuals a human-readable monthly label:

```text
2020-01
2020-02
2020-03
```

`calendar_year_month_sort` gives Power BI an unambiguous numeric order:

```text
202001
202002
202003
```

`has_error` turns the operational text into a reliable Boolean business flag:

```text
transaction_error = NO_ERROR  -> has_error = False
transaction_error = Bad PIN   -> has_error = True
```

## 5. How to import the files in Power BI Desktop

Repeat these steps for each of the three Parquet files:

1. Open Power BI Desktop.
2. Select **Home > Get data > More**.
3. Search for **Parquet**.
4. Select the **Parquet** connector and choose **Connect**.
5. Enter the full path to one of the files under `data/analytics`.
6. Select **Transform Data**, not immediate Load, so the query can be inspected.
7. Give the query the same name as the file without the extension.
8. Confirm that the data types are correct.
9. Select **Close & Apply** after all three queries are ready.

### Where the import query is typed

The import expression belongs in Power Query, not in a DAX measure and not in a
calculated table.

Open it through:

```text
Home > Transform data > select query > Home > Advanced Editor
```

A direct Parquet query has this general M-language form:

```powerquery
let
    Source = Parquet.Document(
        File.Contents(
            "D:\\Road Maps\\project\\Data Modeling\\Enterprise-Banking-Analytics-Platform\\data\\analytics\\fact_transaction_analytics.parquet"
        )
    )
in
    Source
```

Power Query M acquires and shapes data. DAX calculates model results after the
data has been loaded. Keeping those responsibilities separate is fundamental:

```text
Power Query M -> connect, import, clean, and shape
DAX           -> filter-aware business calculations
```

## 6. Semantic model

The model is a star schema with two one-to-many relationships:

```text
dim_date_analytics[date_key]       1 ---- * fact_transaction_analytics[date_key]

dim_merchant_analytics[merchant_key] 1 -- * fact_transaction_analytics[merchant_key]
```

Use single-direction filtering from each dimension to the fact. This gives
predictable filter propagation and avoids ambiguous filter paths.

### Date-table configuration

1. Select `dim_date_analytics`.
2. Choose **Table tools > Mark as date table**.
3. Select `full_date` as the date column.
4. Set `full_date` to the **Date** data type, not Date/time, because each row
   represents a complete calendar day and contains no time-of-day event.
5. Sort `calendar_month_name` by `calendar_month_number`.
6. Sort `calendar_day_name` by `calendar_day_of_week_number`.
7. Sort `calendar_year_month` by `calendar_year_month_sort`.

Date/time stores both a date and a clock time. Date stores only the calendar
date. The date dimension uses Date; the fact's event timestamp uses Date/time.

### Model hygiene

Technical fields should remain available to relationships but hidden from
report authors:

- `date_key`
- `merchant_key`
- `transaction_key`
- `calendar_month_number`
- `calendar_day_of_week_number`
- `calendar_year_month_sort`

Set identifier and ordinal fields to **Don't summarize**. A sum of merchant
keys or month numbers has no business meaning.

## 7. Measures table and DAX

Measures belong in a dedicated `_Measures` home table. The table is an
organizational container; report calculations still operate on the fact and
dimension tables.

### Core operational measures

```dax
Transaction Count =
COUNTROWS ( fact_transaction_analytics )
```

```dax
Total Transaction Amount =
SUM ( fact_transaction_analytics[transaction_amount] )
```

```dax
Average Transaction Amount =
AVERAGE ( fact_transaction_analytics[transaction_amount] )
```

```dax
Fraud Transaction Count =
CALCULATE (
    [Transaction Count],
    fact_transaction_analytics[is_fraud] = TRUE ()
)
```

```dax
Fraud Rate =
DIVIDE ( [Fraud Transaction Count], [Transaction Count] )
```

```dax
Error Transaction Count =
CALCULATE (
    [Transaction Count],
    fact_transaction_analytics[has_error] = TRUE ()
)
```

```dax
Error Rate =
DIVIDE ( [Error Transaction Count], [Transaction Count] )
```

### Executive and comparison measures

```dax
Fraud Exposure =
CALCULATE (
    [Total Transaction Amount],
    fact_transaction_analytics[is_fraud] = TRUE ()
)
```

```dax
Average Fraud Transaction Amount =
DIVIDE ( [Fraud Exposure], [Fraud Transaction Count] )
```

```dax
Error-Free Rate =
1 - [Error Rate]
```

```dax
Prior Year Transaction Amount =
CALCULATE (
    [Total Transaction Amount],
    DATEADD ( dim_date_analytics[full_date], -1, YEAR )
)
```

```dax
Amount YoY Growth =
DIVIDE (
    [Total Transaction Amount] - [Prior Year Transaction Amount],
    [Prior Year Transaction Amount]
)
```

```dax
Selected Date Range =
VAR MinDate = MIN ( dim_date_analytics[full_date] )
VAR MaxDate = MAX ( dim_date_analytics[full_date] )
RETURN
    FORMAT ( MinDate, "MMM d, yyyy" )
        & " - "
        & FORMAT ( MaxDate, "MMM d, yyyy" )
```

### Guided interaction and conditional-format measures

```dax
Selected Merchant Profile =
VAR MerchantLabel =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_display_label] )
VAR MerchantSourceID =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_id_text] )
VAR MerchantCity = SELECTEDVALUE ( dim_merchant_analytics[merchant_city] )
VAR MerchantState = SELECTEDVALUE ( dim_merchant_analytics[merchant_state] )
VAR MerchantZip = SELECTEDVALUE ( dim_merchant_analytics[merchant_zip_code] )
VAR MerchantCategory =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_category_code] )
RETURN
    IF (
        ISBLANK ( MerchantLabel ),
        "Drill through from Merchant Risk to select one merchant",
        MerchantLabel
            & "  |  Source ID " & MerchantSourceID
            & "  |  " & COALESCE ( MerchantCity, "ONLINE" )
            & IF (
                NOT ISBLANK ( MerchantState ),
                ", " & MerchantState,
                ""
            )
            & IF (
                NOT ISBLANK ( MerchantZip ),
                " " & MerchantZip,
                ""
            )
            & "  |  Category " & MerchantCategory
    )
```

This measure gives the Merchant Detail page a useful empty-state instruction
and a compact identity banner after drill-through.

```dax
Fraud Cell Color =
IF (
    SELECTEDVALUE ( fact_transaction_analytics[is_fraud] ) = TRUE (),
    "#FDECEC",
    "#FFFFFF"
)
```

```dax
Error Cell Color =
IF (
    SELECTEDVALUE ( fact_transaction_analytics[has_error] ) = TRUE (),
    "#FFF4E5",
    "#FFFFFF"
)
```

Apply the color measures through **Cell elements > Background color > Field
value** on the Transaction Evidence Ledger. They add a nonintrusive row cue;
keep explicit fraud and error columns visible so color is never the only signal.

The current `_Measures` table contains these 16 business measures:

```text
Amount YoY Growth
Average Fraud Transaction Amount
Average Transaction Amount
Error Cell Color
Error Rate
Error Transaction Count
Error-Free Rate
Fraud Cell Color
Fraud Exposure
Fraud Rate
Fraud Transaction Count
Prior Year Transaction Amount
Selected Date Range
Selected Merchant Profile
Total Transaction Amount
Transaction Count
```

Format counts as whole numbers, monetary measures as currency, and rates or
growth measures as percentages. A measure's name, formula, format, home table,
and description together form its semantic contract.

## 8. Report information architecture

The Command Center separates questions by audience rather than placing every
visual on one page.

### Executive Overview

Purpose: answer the senior manager's first questions quickly.

- Transaction Count
- Total Transaction Amount
- Average Transaction Amount
- Fraud Rate
- Amount YoY Growth
- Selected Date Range context
- High-level trends and operating mix

### Risk & Exceptions

Purpose: quantify exposure and operational control failures.

- Fraud Rate
- Error Rate
- Fraud Transaction Count
- Error Transaction Count
- Fraud Exposure
- Risk and exception breakdowns

### Merchant Risk

Purpose: locate merchant concentrations and compare performance across merchant
attributes.

- Merchant category analysis
- Merchant geography analysis
- Ranked merchant-risk views
- Cross-filtering into selected segments

### Merchant Detail

Purpose: provide a focused drill-through destination without crowding the main
navigation. This page remains hidden from the normal page tabs and is reached
from a merchant context.

## 9. Professional UI and interaction standards

- Maintain a consistent title zone, filter zone, KPI row, and analysis grid.
- Use aligned visual containers and equal spacing instead of manual guesswork.
- Keep the highest-priority KPIs in the first visual scan line.
- Use red or amber only for risk, failure, or exceptions—not decoration.
- Use one restrained banking palette with strong text contrast.
- Keep slicers synchronized when the same date context should apply across
  pages.
- Provide a clear-all-slicers control on every primary page.
- Use a page navigator for predictable movement between report sections.
- Hide technical columns from report view.
- Keep visual titles short and decision-oriented.
- Use tooltips to add detail without making the main canvas dense.
- Verify tab order, contrast, and meaningful alt text before publication.

The outer frame around a group of cards is a shape placed behind the cards. The
shape and the cards can be grouped in the Selection pane. The shape provides
visual structure; it does not contain or calculate the cards.

## 10. Refresh procedure

Use this order whenever the source data changes:

1. From the project root, run:

   ```powershell
   python -m pipelines.run_pipeline
   ```

2. Confirm the pipeline ends with `PIPELINE COMPLETED SUCCESSFULLY`.
3. Confirm the Power BI model and persisted validations are `True`.
4. Open the PBIX report.
5. From a separate PowerShell 7 terminal, run:

   ```powershell
   pwsh -NoProfile -File ".\scripts\harden_power_bi_model.ps1" `
       -RemoveAutoDateTables `
       -RefreshModel
   ```

6. Confirm the command reports `NumericMerchantIdHidden : True`, no remaining
   automatic date tables, and a non-null model refresh duration.
7. Check the control totals on the Executive and Risk pages.
8. Save the PBIX file.

Power BI refresh reads the already-published serving files. It does not replace
the data pipeline.

### Automated daily refresh sequence

The production sequence separates data publication from report import:

```text
05:00 America/Toronto
Windows Task Scheduler -> scripts/run_scheduled_pipeline.ps1
                       -> tests + six pipeline stages
                       -> validated Parquet publication

06:00 America/Toronto
Power BI Service       -> on-premises data gateway
                       -> three Parquet files in data/analytics
                       -> semantic-model refresh
```

The one-hour gap gives the guarded pipeline time to finish before Power BI reads
the files. The jobs are independent; successful execution of the local task
does not directly call the Power BI REST API or trigger the service refresh.

#### Register or repair the 05:00 Windows task

Open a PowerShell 7 terminal at the project root and run:

```powershell
pwsh -NoProfile -File ".\scripts\register_scheduled_pipeline_task.ps1"
```

The registration script uses the installed PowerShell 7 executable and records
the exact Python executable in the task action. It configures one-hour maximum
runtime, overlap prevention, two 15-minute retries, wake-to-run, and
start-when-available behavior.

On this workstation, S4U registration was denied by Windows. The registered
fallback is an interactive, credential-free task under `OMID\omidg`. The user
must remain signed in to Windows. Locking or sleeping is acceptable; signing
out or shutting down prevents the task from running. `WakeToRun` resumes a
sleeping machine; it cannot boot a computer that was powered off.

#### Run the guarded pipeline manually

```powershell
pwsh -NoProfile -File ".\scripts\run_scheduled_pipeline.ps1"
```

The wrapper performs these controls in order:

1. Validate PowerShell, Python, project paths, and the current serving files.
2. Create a timestamped recovery folder and verify each copied file by SHA-256.
3. Run the complete pytest suite.
4. Run all six pipeline stages.
5. Verify that every published Parquet file exists, is non-empty, and has a
   readable SHA-256 hash.
6. Write the latest status atomically to
   `monitoring/scheduled_pipeline_status.json`.
7. Keep 14 days of timestamped logs and recovery copies.

If production execution fails, the wrapper restores and re-hashes the previous
validated publication. Exit code `0` means success, `1` means failure with
successful recovery, and `2` means both execution and recovery failed.

#### Check operational health

```powershell
pwsh -NoProfile -File ".\scripts\get_pipeline_health.ps1"
```

The report is `HEALTHY` only when all of these are true:

- The latest pipeline status is `SUCCESS`, no more than 26 hours old, and is
  newer than the most recently required 05:00 run window.
- The Windows task exists, is ready or running, its last result is `0`, and its
  last run is newer than the required run window. Its PowerShell action,
  wrapper path, Python argument, 05:00 daily trigger, interactive identity, and
  reliability settings must also match the registered production contract.
- The Power BI gateway Windows service is running.
- All three serving Parquet files exist.

For machine-readable output, add `-AsJson`. Investigate a nonzero health-check
exit code before relying on the next Power BI refresh.

#### Verify the next unattended cycle

After 06:00, verify both sides of the chain:

1. Run `scripts/get_pipeline_health.ps1` and confirm a 05:00 pipeline run ID,
   task result `0`, and `HEALTHY`.
2. In Power BI Service, open the semantic model refresh history.
3. Confirm the latest scheduled refresh started after 06:00 and succeeded.
4. Open the report and reconcile the Executive and Risk control totals.

## 11. Validation checklist

For the current sample data, these controls should reconcile:

```text
Date rows:                    6,390
Merchant rows:               1,106
Transaction rows:           19,963
Fraudulent transactions:        27
Error transactions:            574
Total transaction amount: 1,622,991.69
Invalid date relationships:       0
Invalid merchant relationships:   0
```

Before publishing a changed report, validate:

- All automated Python tests pass.
- Each relationship is active, one-to-many, and single-directional.
- The Date table is marked correctly.
- Month and weekday labels use their numeric sort columns.
- Hidden keys remain hidden.
- KPI totals reconcile to the pipeline controls.
- Date filtering affects every intended visual and page.
- Page navigation and clear-filter controls work.
- Drill-through preserves the intended merchant context.
- No visual is clipped at the target display size.
- The PBIX is saved after the final refresh.

## 12. Common errors and their meaning

### A temporary Parquet path cannot be found

Cause: the query still points to a temporary location such as `D:\d.parquet`.

Resolution: open **Transform data**, select the query, edit the Source step or
Advanced Editor, and use the canonical file under `data/analytics`.

### A month or weekday sorts alphabetically

Cause: the label is sorting by itself.

Resolution: select the label column and use **Sort by column** with the matching
numeric order column.

### A key field shows a sigma symbol

Cause: Power BI assumes a numeric column can be aggregated.

Resolution: select the field and set **Summarization** to **Don't summarize**.

### A measure ignores a slicer

Cause: the DAX may remove filter context, the relationship may be inactive, or
the visual interaction may be disabled.

Resolution: inspect the DAX first, then Model view relationships, then **Format
> Edit interactions**.

### A calculated `_Measures` table shows a warning

Cause: an invalid calculated-table name or expression was entered. A calculated
table and a measure are different objects.

Resolution: create a simple measures-home table once, keep its placeholder
column hidden, and use **New measure** for each business calculation.

### Refresh reports a cyclic reference

Cause: Power BI's automatic date hierarchy created a hidden `LocalDateTable_*`,
an automatic relationship, and a timestamp-column variation even though the
model already has a marked `dim_date_analytics` table.

Resolution: keep the PBIX open, ensure `dim_date_analytics` is marked as the
date table, and run:

```powershell
pwsh -NoProfile -File ".\scripts\harden_power_bi_model.ps1" `
    -RemoveAutoDateTables `
    -RefreshModel
```

The script removes the dependent variation and relationship before deleting the
hidden tables, then refreshes the model. It is safe to run again because it is
idempotent.

## 13. Change-management rule

When a Gold schema changes, do not repair Power BI first. Update the serving
contract and tests, run the pipeline, inspect the published Parquet files, and
only then refresh or modify the semantic model. This preserves a traceable path
from source data to executive KPI.
