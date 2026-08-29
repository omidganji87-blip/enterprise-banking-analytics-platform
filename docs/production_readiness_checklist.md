# Production Readiness Checklist

This document separates implemented controls from live-environment acceptance
checks and longer-term enterprise enhancements. Update it whenever a release
changes the pipeline, semantic model, report, gateway, or schedule.

## Current release gates

| Gate | State | Acceptance evidence | Remaining action |
|---|---|---|---|
| Data contracts and transformations | Complete | Bronze, Silver, Gold, Analytics, and Power BI layers execute successfully; persisted model validation is true | Re-run after any schema change |
| Automated Python quality | Complete | 54 tests pass; dependency check and module compilation pass | Keep CI green on every change |
| Power BI serving contract | Complete | Three canonical Parquet files exist under `data/analytics`; row counts, keys, fraud, errors, and amount reconcile | Revalidate after Gold or DAX contract changes |
| Guarded local production run | Complete | Verified pre-run backup, full test run, six pipeline stages, publication hashes, atomic status, and 14-day retention | Monitor each scheduled run |
| Failure recovery | Complete | Controlled failure returned exit code 1 and restored all three publications with unchanged SHA-256 hashes | Repeat after changing recovery logic |
| Windows scheduling | Complete with constraint | Daily 05:00 task is Ready, last result is 0, retries and wake-to-run are enabled | User must remain signed in under the current Interactive logon mode |
| Gateway availability | Complete | `PBIEgwService` is running and three Parquet mappings were configured | Keep the workstation and gateway online for refresh |
| Power BI Service schedule | Configured; live acceptance pending | Daily 06:00 America/Toronto refresh is configured | Verify refresh history after the first complete unattended 05:00/06:00 cycle |
| Report control totals | Complete for current sample | 19,963 transactions, 1,622,991.69 amount, 27 fraud transactions, and 574 error transactions | Reconcile after each changed publication |
| Report design and accessibility | Structurally audited; final live audit pending | Four-page Executive, Risk, Merchant, and drill-through flow was inspected in Power BI Desktop | Resolve Fraud Exposure truncation; audit keyboard order, alt text, contrast, mobile layout, interactions, tooltips, and service rendering |
| Security and governed distribution | Planned | Workspace publication exists | Define audiences, row-level security, sensitivity label, app distribution, and least-privilege ownership before real banking data |
| Final delivery audit | Pending | Local technical gates are documented | Complete live service history, report UX/accessibility, security, and clean repository review |

## Reproducible validation commands

Run from the repository root.

```powershell
python -m pip check
python -m pytest -q
python -m pipelines.run_pipeline
pwsh -NoProfile -File ".\scripts\get_pipeline_health.ps1"
```

The guarded production command is:

```powershell
pwsh -NoProfile -File ".\scripts\run_scheduled_pipeline.ps1"
```

## Current control totals

```text
Date rows:                    6,390
Merchant rows:               1,106
Transaction rows:           19,963
Total transaction amount: 1,622,991.69
Fraud transactions:             27
Error transactions:             574
Invalid date keys:                0
Invalid merchant keys:            0
```

## Unattended-cycle acceptance

After 06:00 America/Toronto:

1. Run `scripts/get_pipeline_health.ps1`.
2. Confirm `OverallHealth` is `HEALTHY`.
3. Confirm the run ID belongs to the current 05:00 window.
4. Confirm Task Scheduler last result is `0`.
5. Open Power BI Service semantic-model refresh history.
6. Confirm the current 06:00 scheduled refresh succeeded.
7. Open the report and reconcile the current control totals.
8. Record any refresh duration or warning that should change the one-hour gap.

Do not call the local-to-cloud chain fully accepted until both the 05:00 local
run and the following 06:00 Power BI Service refresh have succeeded without
manual intervention.

## Enterprise hardening still required for real banking data

- Replace interactive local scheduling with a managed service identity or
  approved service account on a continuously available host.
- Store production data in governed cloud or enterprise storage rather than a
  user workstation.
- Add centralized alert delivery and multi-run telemetry.
- Define data classification, retention, lineage, ownership, and incident
  response procedures.
- Implement and test row-level security with representative roles.
- Separate development, test, and production workspaces and deployment stages.
- Complete privacy, security, and regulatory review before using customer data.
