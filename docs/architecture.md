# Architecture

## Core: Microsoft Graph special agent

The Checkmk site authenticates to Microsoft Entra with an app registration and calls Microsoft Graph directly over HTTPS. No Checkmk agent is required on the logical Cloud Sync API host.

The collector uses two Graph data areas:

- synchronization jobs under `/servicePrincipals/{servicePrincipalId}/synchronization/jobs`
- provisioning audit events under `/auditLogs/provisioning`

Only synchronization jobs with `templateId == AD2AADProvisioning` are evaluated.

The special agent writes one `entra_cloudsync` agent section. The Checkmk check plug-in turns that section into six services for each Cloud Sync configuration.

```text
Microsoft Entra / Microsoft Graph
             |
             | HTTPS/443
             v
      Checkmk special agent
             |
             v
   entra_cloudsync section
             |
             +-- Job
             +-- Execution
             +-- Objects
             +-- Provisioning
             +-- Dropped Objects
             +-- Property Changes
```

## Provisioning failure recovery

Provisioning logs are read newest first. The collector keeps the newest event for each object identity within the configured window. A failure or warning remains unresolved only while that object's newest event is still a problem. A later successful event for the same object clears the unresolved problem while historical success/failure metrics remain available.

Identity correlation prefers the source object ID, then target object ID, then UPN when available.

## Property changes

Property-sync reporting evaluates successful `update` events. `modifiedProperties` is compared after normalizing equivalent empty values such as `null`, empty string, empty list and empty dictionary. The collector retains property names and counts, not old/new property values.

## Restart and NotRun behavior

Microsoft can temporarily return `status.code = NotRun` and sentinel timestamps after provisioning is started or restarted. The check treats year-0001 timestamps as missing rather than calculating an invalid age.

For an active schedule in `NotRun`, Checkmk starts a persistent observation timer. The default grace period is two synchronization intervals: WARN during the grace period, CRIT if `NotRun` persists beyond it. The multiplier is configurable by rule.

## Optional Windows-side checks

The two Windows local checks are independent from the Graph integration. They run on the server hosting the Microsoft Entra Cloud Sync provisioning agent and provide local agent-version and connectivity information.

Standard Windows service/process monitoring remains the responsibility of the normal Checkmk Windows agent and Checkmk service/process rules.

General domain-controller health such as DCDiag is deliberately outside this MKP's core scope.
