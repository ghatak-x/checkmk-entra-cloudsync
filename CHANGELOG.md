# Changelog

All notable changes to this project are documented here.

## 0.0.1

Initial public release.

- Microsoft Graph special agent for Microsoft Entra Cloud Sync.
- Cloud Sync job state, restart/`NotRun` handling, successive failures and quarantine monitoring.
- Execution state, duration and configurable freshness monitoring.
- Synchronized object counts.
- Object-level provisioning failures and warnings with unresolved-failure recovery correlation.
- Dropped/deprovisioned object event counts.
- Property synchronization activity with empty-value normalization.
- Checkmk service parameter rules for execution freshness and `NotRun` grace handling.
- Six Checkmk check manuals.
- Optional Windows local checks for Cloud Sync agent version and connectivity.
