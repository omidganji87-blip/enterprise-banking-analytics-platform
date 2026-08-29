# Power BI Report QA

This checklist records structural and visual observations from the local Power
BI Desktop report. It complements data-model validation; it does not replace a
published-service, accessibility, or security review.

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
- `merchant_id` is configured in the drill-through filter well.

## Confirmed design strengths

- The information hierarchy moves from enterprise summary to risk, merchant
  concentration, and transaction evidence.
- Common date context, card layout, navigation, headers, and restrained banking
  palette provide visual consistency.
- Risk colors are reserved for fraud and exception information.
- The drill-through page supplies evidence without overcrowding primary pages.
- Visual titles are exposed through the Power BI accessibility tree.

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

## Open findings

| Priority | Finding | Required action |
|---|---|---|
| Medium | Fraud Exposure displayed with an ellipsis at the inspected Desktop canvas size | Increase value area, reduce display text size, or use compact display units; verify again at the target service resolution |
| Medium | Custom alt text and keyboard tab order were not fully verified for every visual | Use the Selection and Tab order panes, then test with keyboard-only navigation and a screen reader |
| Medium | Mobile layout was not visually validated | Complete and test the phone layout or explicitly document desktop-only scope |
| Low | Merchant category and merchant bar charts are sparse for the current sample | Confirm labels, tooltips, and zero/small-count behavior using representative risk data |
| Low | Published-service rendering was unavailable during this audit | Repeat the four-page visual check in Power BI Service after the next successful refresh |
| Low | Local cold-start time was dominated by Performance Analyzer `Other` time | Repeat a cold-cache service test after the scheduled refresh and compare it with the warm Desktop baseline |

## Final report acceptance checklist

- [ ] Resolve Fraud Exposure truncation.
- [ ] Verify every visual title and custom alt-text description.
- [ ] Verify keyboard tab order follows navigation, slicers, KPIs, charts, then
  supporting detail.
- [ ] Validate color contrast and non-color risk cues.
- [ ] Test clear-all-slicers behavior on every primary page.
- [ ] Test synchronized date slicers across all primary pages.
- [ ] Test Merchant Risk to Merchant Detail drill-through and Back behavior.
- [ ] Test all tooltips and cross-filter interactions.
- [ ] Validate phone layout or document its exclusion.
- [x] Capture a four-page warm Desktop Performance Analyzer baseline.
- [ ] Repeat performance testing in Power BI Service, including a cold-cache
  first load and a warm reload.
- [ ] Repeat the audit in Power BI Service at the target display resolution.
- [x] Reconcile report totals to the current pipeline controls.
