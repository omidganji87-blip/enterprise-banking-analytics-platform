# Power BI Report QA

This checklist records structural and visual observations from Power BI Desktop
and the published Power BI Service report. It complements data-model
validation; it does not replace final accessibility, device, or security
acceptance.

## Page inventory reviewed on 2026-08-29

### 1. Executive Overview

- Primary navigation for Executive Overview, Risk & Exceptions, and Merchant
  Risk.
- Synchronized date-range context and a selected-date-range indicator.
- Clear-all-slicers control.
- Transaction Count, Total Transaction Amount, Average Transaction Amount,
  Fraud Rate, and Amount YoY Growth cards.
- Transaction Volume & Value Trend combination chart.
- Transaction Method Mix donut chart.

### 2. Risk & Exceptions

- Date context and primary navigation remain consistent.
- Fraud Rate, Error Rate, Fraud Transaction Count, Error Transaction Count, and
  Fraud Exposure cards.
- Fraud & Error Event Trend combination chart.
- Error Type Breakdown bar chart.

### 3. Merchant Risk

- Date context and primary navigation remain consistent.
- Transaction Count, Total Transaction Amount, Average Transaction Amount,
  Fraud Rate, and Fraud Transaction Count cards.
- Fraud by Merchant Category (MCC) bar chart.
- Top 10 Fraudulent Merchants bar chart.

### 4. Merchant Detail

- Drill-through page is omitted from the primary page navigator.
- Back control is present.
- Merchant context is shown in the page header.
- Transaction Count, Total Transaction Amount, Average Transaction Amount,
  Fraud Rate, and Fraud Transaction Count cards.
- Transaction Evidence Ledger provides transaction-level detail.
- The local report now uses `merchant_display_label` as the drill-through key
  and as the first column of the evidence ledger. The ledger header is renamed
  **Merchant Label**, while `merchant_id_text` remains available to the selected-
  merchant profile when the exact source identifier is needed.
- A local end-to-end drill-through from `MRC-000028` returned three matching
  evidence rows, preserved the compact label, displayed the exact source ID in
  the merchant profile, and returned to Merchant Risk through the Back control.

## Confirmed design strengths

- The information hierarchy moves from enterprise summary to risk, merchant
  concentration, and transaction evidence.
- Common date context, card layout, navigation, headers, and restrained banking
  palette provide visual consistency.
- Risk colors are reserved for fraud and exception information.
- The drill-through page supplies evidence without overcrowding primary pages.
- Visual titles are exposed through the Power BI accessibility tree. Cards,
  slicers, and navigation controls retain meaningful native accessible names,
  while the seven analytical charts and evidence table have custom descriptions.

## Performance Analyzer baseline captured on 2026-08-29

The four report pages were measured in Power BI Desktop with Performance
Analyzer by recording a full visual refresh against the current local semantic
model. The first Executive Overview refresh was also retained as a cold-start
observation; the page's slow visuals ranged from 3.19 to 4.26 seconds, but the
expanded slicer result showed only 89 ms of DAX query time and 4.15 seconds of
`Other` time. This indicates initialization and visual scheduling dominated the
first pass rather than an expensive DAX query.

Warm-refresh results provide the comparable local baseline:

| Page | Visual or control | Duration (ms) |
|---|---|---:|
| Executive Overview | Page navigator | 215 |
| Executive Overview | Clear-all button | 214 |
| Executive Overview | Date slicer | 390 |
| Executive Overview | Legacy card group | 445 |
| Executive Overview | Header text | 89 |
| Executive Overview | Transaction Volume & Value Trend | 518 |
| Executive Overview | Transaction Method Mix | 515 |
| Executive Overview | New card group | 524 |
| Risk & Exceptions | Page navigator | 137 |
| Risk & Exceptions | Clear-all button | 137 |
| Risk & Exceptions | Date slicer | 358 |
| Risk & Exceptions | Header text | 59 |
| Risk & Exceptions | Fraud & Error Event Trend | 426 |
| Risk & Exceptions | Error Type Breakdown | 425 |
| Risk & Exceptions | New card group | 432 |
| Merchant Risk | Page navigator | 235 |
| Merchant Risk | Clear-all button | 236 |
| Merchant Risk | Date slicer | 598 |
| Merchant Risk | Header text | 110 |
| Merchant Risk | Fraud by Merchant Category (MCC) | 774 |
| Merchant Risk | Top 10 Fraudulent Merchants | 772 |
| Merchant Risk | New card group | 818 |
| Merchant Detail | Back button | 98 |
| Merchant Detail | Date slicer | 280 |
| Merchant Detail | Header text | 55 |
| Merchant Detail | Selected Merchant Profile card | 237 |
| Merchant Detail | KPI card group | 284 |
| Merchant Detail | Transaction Evidence Ledger | 319 |

All warm Desktop visuals completed in less than one second. Merchant Risk is
the heaviest page at this data volume, with an 818 ms maximum. The published
service, gateway round trip, concurrent-user load, and truly cold browser-cache
behavior remain separate acceptance tests.

## Published-service QA on 2026-08-29

The signed-in Power BI Service report was reviewed at its published URL. All
three primary pages rendered, and the hidden Merchant Detail drill-through page
was correctly omitted from the Pages pane.

- The Merchant Risk start date was changed to `1/1/2020`; its controls updated
  to 182 transactions, $13.52K total amount, and $74.30 average amount.
- Switching to Risk & Exceptions preserved the `1/1/2020` date context and
  returned 2.20% error rate and four error transactions.
- **Clear all slicers** restored the complete `9/1/2002` through `2/28/2020`
  range and the 19,963-transaction control total.
- Observed warm page-transition wall times were 3.69 seconds for Executive
  Overview, 3.73 seconds for Risk & Exceptions, and 5.72 seconds for Merchant
  Risk. These figures include browser automation overhead and are directional,
  not network-isolated performance timings.
- The service banner still reported data updated on 2026-08-27. Scheduled
  refreshes on 2026-08-28 and 2026-08-29 failed because the gateway host was
  offline. The latest published report therefore predates the current local
  PBIX and serving-contract fixes.

The published Merchant Risk labels also demonstrated why numeric 64-bit source
IDs are unsuitable for browser display: values were rounded. The serving layer
now publishes exact `merchant_id_text` plus compact `merchant_display_label`
fields, and the local semantic model has been hardened and refreshed. Visual
field replacement is complete in the local PBIX; republication remains a
release action.

## KPI reconciliation against serving data on 2026-08-29

The current report cards were reconciled directly to
`data/analytics/fact_transaction_analytics.parquet`. The exact controls below
round to the values displayed in the Desktop report, including 20K transactions,
$1.62M total amount, $81.30 average amount, 0.14% fraud rate, 2.88% error rate,
and 6.13% amount growth.

| Control | Exact serving-data value |
|---|---:|
| Transaction Count | 19,963 |
| Total Transaction Amount | $1,622,991.69 |
| Average Transaction Amount | $81.299989 |
| Fraud Transaction Count | 27 |
| Fraud Rate | 0.13525021% |
| Fraud Exposure | $2,617.28 |
| Average Fraud Transaction Amount | $96.936296 |
| Error Transaction Count | 574 |
| Error Rate | 2.87531934% |
| Error-Free Rate | 97.12468066% |
| Prior Year Transaction Amount | $1,529,197.77 |
| Amount YoY Growth | 6.13353759% |

## Keyboard tab-order remediation on 2026-08-29

The Power BI Selection pane was used to align keyboard navigation with the
report's visual information hierarchy. Duplicate or hidden objects were removed
from keyboard focus.

| Page | Final sequence |
|---|---|
| Executive Overview | Page navigator; clear-all button; date slicer; KPI card group; Transaction Method Mix; Transaction Volume & Value Trend; header text; legacy duplicate card group excluded from focus |
| Risk & Exceptions | Page navigator; clear-all button; date slicer; KPI card group; Error Type Breakdown; Fraud & Error Event Trend; header text |
| Merchant Risk | Page navigator; clear-all button; date slicer; KPI card group; Top 10 Fraudulent Merchants; Fraud by Merchant Category; header text |
| Merchant Detail | Back button; date slicer; selected-merchant profile; KPI card group; Transaction Evidence Ledger; header text; hidden Fraud Concentration by Merchant State visual excluded from focus |

## Visual alt-text remediation on 2026-08-29

Custom screen-reader descriptions were added to every active analytical chart
and to the transaction evidence table. The descriptions explain the visual's
purpose, filter context, interpretation, and drill-through behavior where
applicable:

- Transaction Volume & Value Trend.
- Transaction Method Mix.
- Fraud & Error Event Trend.
- Error Type Breakdown.
- Top 10 Fraudulent Merchants.
- Fraud by Merchant Category.
- Transaction Evidence Ledger.

The saved PBIX package contains exactly seven `altText` properties, and all
seven expected descriptions were found in `Report/Layout`. Cards, slicers,
navigation, and the Back control continue to use Power BI's native accessible
names and values. The hidden Merchant Detail state-concentration visual remains
excluded from focus and does not need a user-facing description. A final
assistive-technology acceptance session is still required on the published
release.

Three automated package tests now protect the report artifact in CI. They verify
the required PBIX entries, exact-safe merchant display contract, absence of
automatic-date references, and presence of all seven expected descriptions.

## Local contrast and non-color cue review on 2026-08-29

The packaged base theme was inspected directly. Standard foreground text is
`#252423` on `#FFFFFF`, a 15.49:1 contrast ratio. The principal blue, orange,
red, teal, and green data colors range from 3.02:1 to 5.65:1 against white,
meeting the 3:1 graphical-object threshold. The lower-ratio accents are used for
chart marks and large KPI values, not body copy.

Risk meaning is not encoded by color alone: KPI labels name each metric, bar
charts retain category and value labels, and the fraud/error time series uses a
marked line against columns as well as a legend. Published high-contrast-mode
and target-device inspection remains an acceptance check.

## Local cross-filter interaction QA on 2026-08-29

Selecting the `SWIPE` segment in Transaction Method Mix filtered the Executive
Overview KPIs from 20K transactions, $1.62M amount, $81.30 average, 0.14% fraud
rate, and 6.13% growth to 16K, $1.30M, $81.76, 0.07%, and 3.69%. The transaction
trend also responded, and selecting the segment again restored the control
totals. This confirms the representative chart-to-chart and chart-to-card
interaction path in the corrected local PBIX.

## Mobile layout remediation on 2026-08-29

Power BI's phone-layout generator was run for all four report pages. Each phone
canvas now follows the page navigation, clear control, date slicer, KPI cards,
and analytical-detail hierarchy. Merchant Detail keeps the hidden state-
concentration chart out of the placed phone content. The generated layouts were
visually inspected in Power BI Desktop; final device-size and Power BI mobile-
app validation remains a release acceptance check.

## Open findings

| Priority | Finding | Required action |
|---|---|---|
| Medium | Custom alt text and standard-theme contrast are implemented locally, but end-to-end assistive-technology acceptance is pending | Publish the corrected PBIX and test all four pages with the target screen reader, browser, and Windows high-contrast combination |
| Medium | Generated phone layouts have not been tested on target physical devices | Validate all four pages in the Power BI mobile app and refine spacing if needed |
| Low | Merchant category and merchant bar charts are sparse for the current sample | Confirm labels, tooltips, and zero/small-count behavior using representative risk data |
| High | Published service is stale after two gateway-offline refresh failures | Keep the signed-in gateway workstation powered on and verify the next unattended 05:00/06:00 cycle |
| Medium | Published visuals still reflect the prior numeric merchant IDs and round them | Publish the corrected local PBIX, then verify compact labels and exact-ID detail in the service |
| Medium | Full Merchant Risk drill-through and tooltip behavior has not been tested in the service | Complete the interaction test after publishing the current PBIX |
| Low | Local cold-start time was dominated by Performance Analyzer `Other` time | Repeat a cold-cache service test after the scheduled refresh and compare it with the warm Desktop baseline |

## Final report acceptance checklist

- [x] Resolve Fraud Exposure truncation (`$2.62K`, thousands, two decimals).
- [x] Verify accessible names for cards, slicers, and navigation; add and
  package-verify custom descriptions for all seven active analytical visuals.
- [x] Audit the current keyboard tab order on all four pages.
- [x] Reorder keyboard focus to navigation, slicers, KPIs, charts, then
  supporting detail.
- [ ] Confirm the final focus sequence in an end-to-end keyboard and screen-
  reader session.
- [x] Remove the hidden Merchant Detail state-concentration visual from tab
  order, or make the visual visible and position it deliberately.
- [x] Validate standard-theme contrast ratios and non-color risk cues at the
  report-definition level.
- [ ] Validate the published report with the target Windows/browser high-
  contrast configuration.
- [x] Test clear-all-slicers behavior in the published primary-page flow.
- [x] Test synchronized date slicers across the published primary-page flow.
- [x] Test Merchant Risk to Merchant Detail drill-through and Back behavior in
  the corrected local PBIX; repeat it in the service after publication.
- [x] Test a representative Executive Overview cross-filter interaction and
  confirm control-total restoration.
- [ ] Test all tooltips and cross-filter interactions in the published release.
- [x] Audit whether a phone layout currently exists.
- [x] Build phone layouts for all four user-facing pages.
- [ ] Validate the generated phone layouts on target physical devices.
- [x] Capture a four-page warm Desktop Performance Analyzer baseline.
- [ ] Repeat performance testing in Power BI Service, including a cold-cache
  first load and a warm reload.
- [x] Repeat primary-page rendering and filter synchronization checks in Power
  BI Service at the current desktop browser resolution.
- [x] Reconcile report totals to the current pipeline controls.
