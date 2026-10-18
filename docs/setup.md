# Setup and prerequisites

## 1. Checkmk site

Requirements:

- Checkmk 2.5.0 or newer
- DNS resolution and correct system time
- outbound HTTPS TCP/443 to `login.microsoftonline.com` and `graph.microsoft.com`
- no external Python packages

The special agent uses the Python runtime shipped with Checkmk and Checkmk's own APIs.

## 2. Microsoft Entra application

Create a dedicated app registration for monitoring. Grant these Microsoft Graph **Application** permissions and administrator consent:

- `Synchronization.Read.All`
- `AuditLog.Read.All`
- `Directory.Read.All`

Create a client secret. Store it in the Checkmk Password Store instead of entering it as a clear-text rule value.

Collect these values:

- tenant ID
- application/client ID
- client secret
- object ID of the service principal representing the Cloud Sync configuration

The service-principal object ID is not the same as the application/client ID.

## 3. Install and configure the MKP

Install the MKP in **Setup → Maintenance → Extension packages** or from the site shell.

Create a logical host for the API integration. The host should use no normal Checkmk agent and should execute configured special agents.

Create the rule:

**Setup → Agents → Other integrations → Microsoft Entra Cloud Sync**

Configure:

- Tenant ID
- Client ID
- Client secret / Password Store entry
- Cloud Sync service-principal object ID
- Provisioning log window, default 60 minutes
- Maximum provisioning-log pages, default 10
- HTTP timeout, default 30 seconds

Activate changes and discover services on the logical API host.

## 4. Check parameters

Two service parameter rules are included.

### Execution freshness

Default levels are relative to the Microsoft-reported synchronization interval:

- WARN: 2.0 × interval
- CRIT: 3.0 × interval

For a `PT20M` interval this means WARN after 40 minutes and CRIT after 60 minutes.

### NotRun grace

An active Cloud Sync job can temporarily enter `NotRun` after start/restart. The default grace is:

- WARN while `NotRun` for less than 2.0 × interval
- CRIT once `NotRun` reaches the grace limit

The multiplier is configurable.

## 5. Optional Windows local checks

These checks are optional and do not affect the Graph special agent.

After the MKP is installed, the source files are available on the Checkmk server under:

```text
~/local/share/check_mk/agents/windows/local/
```

Deploy them on every Windows server that actually runs the Microsoft Entra Cloud Sync provisioning agent:

```text
C:\ProgramData\checkmk\agent\local\entra_cloudsync_agent_version.ps1
C:\ProgramData\checkmk\agent\local\entra_cloudsync_connectivity.ps1
```

No extra PowerShell module is required.

### Connectivity configuration

By default the connectivity check tests:

- `login.microsoftonline.com:443`
- `graph.microsoft.com:443`
- a discovered domain controller on LDAP 389
- the same domain controller on Global Catalog 3268

If domain-controller auto-discovery is not appropriate, copy the example configuration from:

```text
~/local/share/check_mk/agents/windows/config/entra_cloudsync_local.json.example
```

to:

```text
C:\ProgramData\checkmk\agent\config\entra_cloudsync_local.json
```

Example:

```json
{
  "domain_controller": "dc01.example.com",
  "timeout_seconds": 3
}
```

### Recommended caching

The development environment used a one-hour cache for the agent-version check and a five-minute cache for connectivity. On Windows this can be configured in the agent's user configuration if desired. The scripts themselves do not require caching.

## 6. Standard Windows service/process monitoring

The Checkmk Windows agent already reports services and processes. Use normal Checkmk rules for the Cloud Sync processes/services instead of duplicating them as local checks.

Relevant names are:

```text
AADConnectProvisioningAgent
AzureADConnectAgentUpdater
```

Service monitoring is generally sufficient for availability. Process discovery can be added if your monitoring policy explicitly requires process-count/resource checks, but it may duplicate the service view.

## 7. Domain controller checks

The DCDiag local checks used in the development lab are not bundled. They are generic Active Directory/domain-controller monitoring rather than Cloud Sync monitoring.

If you maintain them separately, deploy them on the domain controller under:

```text
C:\ProgramData\checkmk\agent\local\
```

## 8. No additional runtime modules

The package does not require:

- AzureAD PowerShell
- MSOnline PowerShell
- Microsoft.Graph PowerShell
- ActiveDirectory PowerShell for the bundled local checks
- pip-installed Python modules
