# Production Readiness Checklist

This document separates implemented controls from live-environment acceptance
checks and longer-term enterprise enhancements. Update it whenever a release
changes the pipeline, semantic model, report, gateway, or schedule.

## Current release gates

| Gate | State | Acceptance evidence | Remaining action |
|---|---|---|---|
| Data contracts and transformations | Complete | Bronze, Silver, Gold, Analytics, and Power BI layers execute successfully; persisted model validation is true | Re-run after any schema change |
| Automated Python quality | Complete locally; release CI rerun pending | 58 tests pass locally, including exact signed 64-bit merchant-ID preservation and three PBIX package-contract tests; dependency check and module compilation pass | Push the release revision, run CI, and keep it green |
| Local Streamlit dashboard | Complete for local use | Headless smoke test returned HTTP 200 from both the app and `/_stcore/health` on 2026-08-29 | Repeat after dashboard or dependency changes; cloud deployment requires portable storage paths |
| Power BI serving contract | Complete | Three canonical Parquet files exist under `data/analytics`; row counts, keys, fraud, errors, and amount reconcile; all 1,106 merchant IDs have exact text and unique compact display labels | Revalidate after Gold or DAX contract changes |
| Guarded local production run | Complete | Verified pre-run backup, full test run, six pipeline stages, publication hashes, atomic status, and 14-day retention | Monitor each scheduled run |
| Failure recovery | Complete | Controlled failure returned exit code 1 and restored all three publications with unchanged SHA-256 hashes | Repeat after changing recovery logic |
| Windows scheduling | Complete with constraint | Daily 05:00 task is Ready, last result is 0, retries and wake-to-run are enabled | User must remain signed in under the current Interactive logon mode |
| Gateway availability | Complete | `PBIEgwService` is running and three Parquet mappings were configured | Keep the workstation and gateway online for refresh |
| Power BI Service schedule | Configured; live acceptance failed on 2026-08-28 and 2026-08-29 | Daily 06:00 America/Toronto refresh is configured; both observed scheduled attempts failed because the gateway host was offline; the 2026-08-27 on-demand refresh succeeded | Leave the signed-in workstation powered on and verify the next complete unattended 05:00/06:00 cycle |
| Report control totals | Complete for current sample | 19,963 transactions, 1,622,991.69 amount, 27 fraud transactions, and 574 error transactions | Reconcile after each changed publication |
| Report performance | Desktop baseline complete; service acceptance pending | All four pages were measured with Performance Analyzer; warm visual maximum was 818 ms | Repeat cold- and warm-cache tests in Power BI Service |
| Report design and accessibility | Corrected release published; final device and assistive-technology acceptance pending | Fraud Exposure renders as `$2.62K`; all four pages follow a professional keyboard sequence; duplicate/hidden visuals are excluded from focus; four phone layouts were generated; all seven active analytical visuals have package-verified custom alt text; standard-theme contrast and non-color cues were reviewed; published primary-page rendering, synchronized date context, clear-all behavior, representative cross-filtering, exact-safe merchant labels, Merchant Detail drill-through, and Back behavior passed | Validate high-contrast and screen-reader behavior, test phone layouts on target devices, and complete the tooltip matrix |
| Security and governed distribution | Planned | Workspace publication exists | Define audiences, row-level security, sensitivity label, app distribution, and least-privilege ownership before real banking data |
| Version control and CI | Release revision ready; CI rerun pending | The published PBIX opens as a valid 13-entry package, contains the safe Merchant Risk category and Merchant Label evidence header, contains seven verified alt-text descriptions and no automatic-date references, and is covered by 58 passing tests | Push the release revision and confirm CI succeeds |
| Final delivery audit | Conditional pass | Local technical gates, repository hygiene, service rendering, filter synchronization, gateway mapping, exact-safe merchant labels, drill-through behavior, and deliberate PBIX semantic hardening are documented; runtime files are ignored and no tracked secret patterns were found | Complete the unattended live cycle, physical-device and assistive-technology acceptance, full tooltip QA, and business-defined security/governance |

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
2. Confirm `OverallHealth` and `TaskConfigurationValid` are healthy/true.
3. Confirm the run ID belongs to the current 05:00 window.
4. Confirm Task Scheduler last result is `0`.
5. Open Power BI Service semantic-model refresh history.
6. Confirm the current 06:00 scheduled refresh succeeded.
7. Open the report and reconcile the current control totals.
8. Record any refresh duration or warning that should change the one-hour gap.

Do not call the local-to-cloud chain fully accepted until both the 05:00 local
run and the following 06:00 Power BI Service refresh have succeeded without
manual intervention.

The 2026-08-28 and 2026-08-29 service attempts failed because the workstation
was powered off and the gateway was unreachable. `WakeToRun` can resume sleep
but cannot boot a powered-off computer. For the next acceptance attempt, leave
the machine powered on and `OMID\omidg` signed in from before 05:00 until the
service refresh completes after 06:00.

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
