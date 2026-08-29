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

## Open findings

| Priority | Finding | Required action |
|---|---|---|
| Medium | Fraud Exposure displayed with an ellipsis at the inspected Desktop canvas size | Increase value area, reduce display text size, or use compact display units; verify again at the target service resolution |
| Medium | Custom alt text and keyboard tab order were not fully verified for every visual | Use the Selection and Tab order panes, then test with keyboard-only navigation and a screen reader |
| Medium | Mobile layout was not visually validated | Complete and test the phone layout or explicitly document desktop-only scope |
| Low | Merchant category and merchant bar charts are sparse for the current sample | Confirm labels, tooltips, and zero/small-count behavior using representative risk data |
| Low | Published-service rendering was unavailable during this audit | Repeat the four-page visual check in Power BI Service after the next successful refresh |

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
- [ ] Repeat the audit in Power BI Service at the target display resolution.
- [ ] Reconcile report totals to the current pipeline controls.

