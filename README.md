# Checkmk Microsoft Entra Cloud Sync

Checkmk extension for monitoring **Microsoft Entra Cloud Sync** with Microsoft Graph.

The core integration is an agentless Checkmk special agent. Two optional Windows local checks can add Cloud Sync agent version and connectivity visibility on the Windows server that runs the Microsoft Entra provisioning agent.

## What you get

The special agent discovers one set of services per `AD2AADProvisioning` Cloud Sync job:

| Service | Monitors |
|---|---|
| `Entra Cloud Sync Job <config>` | Schedule/job state, restart `NotRun` handling, successive failures, quarantine |
| `Entra Cloud Sync Execution <config>` | Last execution state, age, duration and configurable freshness |
| `Entra Cloud Sync Objects <config>` | Synchronized object counts reported by Microsoft |
| `Entra Cloud Sync Provisioning <config>` | Unresolved object failures/warnings, recovery correlation and historical activity |
| `Entra Cloud Sync Dropped Objects <config>` | Delete, staged-delete, disable and skipped provisioning events |
| `Entra Cloud Sync Property Changes <config>` | Successful property synchronization activity and changed attribute names/counts |

Optional Windows local checks provide:

- `Entra Cloud Sync Agent Version`
- connectivity to Microsoft sign-in, Microsoft Graph, AD LDAP and the Global Catalog

Normal Windows service and process monitoring is intentionally not duplicated by this package. Use the standard Checkmk Windows agent and rules for `AADConnectProvisioningAgent` and `AzureADConnectAgentUpdater`.

## Requirements

### Checkmk site

- Checkmk **2.5.0 or newer**
- outbound HTTPS/443 to `login.microsoftonline.com` and `graph.microsoft.com`
- no additional Python packages

### Microsoft Entra

Create an app registration and grant these Microsoft Graph **Application** permissions with administrator consent:

- `Synchronization.Read.All`
- `AuditLog.Read.All`
- `Directory.Read.All`

You need the tenant ID, application/client ID, client secret, and the object ID of the service principal representing the Cloud Sync configuration. Store the client secret in the **Checkmk Password Store**.

### Optional Windows local checks

- Checkmk Windows agent installed on the Cloud Sync provisioning-agent server
- Windows PowerShell 5.1 or newer
- no `AzureAD`, `MSOnline`, `Microsoft.Graph`, `ActiveDirectory` or other third-party PowerShell module is required

See [docs/setup.md](docs/setup.md) for the complete setup and deployment procedure.

## Installation

Build from the repository:

```bash
python tools/build_mkp.py
```

The package is written to `dist/entra_cloudsync-0.0.1.mkp`.

Install it in **Setup → Maintenance → Extension packages**, or as the Checkmk site user:

```bash
mkp add /tmp/entra_cloudsync-0.0.1.mkp
mkp enable entra_cloudsync 0.0.1
cmk -R
```

Create a logical host for the API integration with no normal Checkmk agent and configure:

**Setup → Agents → Other integrations → Microsoft Entra Cloud Sync**

Then discover services on that logical host.

## Optional Windows-side monitoring

After installing the MKP, the local-check source files are available on the Checkmk site under:

```text
~/local/share/check_mk/agents/windows/local/
```

Copy them to the **Windows server running the Microsoft Entra Cloud Sync provisioning agent**:

```text
C:\ProgramData\checkmk\agent\local\
```

Files:

```text
entra_cloudsync_agent_version.ps1
entra_cloudsync_connectivity.ps1
```

The connectivity check can optionally use:

```text
C:\ProgramData\checkmk\agent\config\entra_cloudsync_local.json
```

A template is installed on the Checkmk site under:

```text
~/local/share/check_mk/agents/windows/config/entra_cloudsync_local.json.example
```

The optional local checks belong on the **Cloud Sync agent server**, not on the logical API host.

### Standard Windows services/processes

The Checkmk Windows agent already exposes Windows services and processes. Configure standard Checkmk service/process rules if you want explicit monitoring of:

```text
AADConnectProvisioningAgent
AzureADConnectAgentUpdater
```

The MKP does not create those rules automatically because service/process policy is site-specific.

### Domain controller DCDiag checks

DCDiag checks used during development are **not part of this MKP**. They monitor general Active Directory/domain-controller health rather than Entra Cloud Sync itself. If you maintain DCDiag local checks separately, deploy them on the domain controller under:

```text
C:\ProgramData\checkmk\agent\local\
```

## Repository layout

```text
cmk_addons/plugins/entra_cloudsync/   Checkmk special agent, checks, rules and manuals
agents/windows/                       Optional Windows local checks and example config
docs/                                 Architecture, setup and test guidance
tests/                                Automated source/package tests
tools/build_mkp.py                    MKP builder
manifest.json                         Release metadata
```

The repository intentionally does not mirror `~/local/lib/python3/...`. The MKP installs the `cmk_addons/plugins/entra_cloudsync` tree into the correct Checkmk site location.

## Development

```bash
python -m pip install -r requirements-dev.txt
ruff check .
pytest
python tools/build_mkp.py
```

On a Checkmk 2.5 test site, additionally validate with:

```bash
cmk-validate-plugins
cmk -M entra_cloudsync_job
cmk -M entra_cloudsync_execution
cmk -M entra_cloudsync_objects
cmk -M entra_cloudsync_provisioning
cmk -M entra_cloudsync_dropped
cmk -M entra_cloudsync_properties
```

## Documentation

- [Architecture](docs/architecture.md)
- [Setup and prerequisites](docs/setup.md)
- [Testing](docs/testing.md)

## License

GPL-2.0-only. See [LICENSE](LICENSE).
