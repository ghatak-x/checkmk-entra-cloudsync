# Microsoft Entra Cloud Sync connectivity local checks for Checkmk.
#
# Deploy this file on each Windows server that runs the Microsoft Entra
# Cloud Sync provisioning agent:
#   C:\ProgramData\checkmk\agent\local\entra_cloudsync_connectivity.ps1
#
# It tests connectivity from the Cloud Sync agent server itself to:
#   - login.microsoftonline.com:443
#   - graph.microsoft.com:443
#   - a domain controller:389 (LDAP)
#   - a domain controller:3268 (Global Catalog)
#
# No additional PowerShell modules are required.
# Optional configuration file:
#   C:\ProgramData\checkmk\agent\config\entra_cloudsync_local.json
# Example:
#   { "domain_controller": "dc01.example.com", "timeout_seconds": 3 }

$ErrorActionPreference = 'Stop'
$ConfigPath = Join-Path $env:ProgramData 'checkmk\agent\config\entra_cloudsync_local.json'
$TimeoutSeconds = 3
$DomainController = $null

function Write-LocalCheck([int]$State, [string]$Name, [string]$Message) {
    Write-Output ("{0} `"{1}`" - {2}" -f $State, $Name, $Message)
}

function Test-TcpEndpoint([string]$HostName, [int]$Port, [int]$TimeoutMs) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait($TimeoutMs)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

if (Test-Path -LiteralPath $ConfigPath) {
    try {
        $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
        if ($config.domain_controller) {
            $DomainController = [string]$config.domain_controller
        }
        if ($config.timeout_seconds) {
            $TimeoutSeconds = [int]$config.timeout_seconds
        }
    }
    catch {
        Write-LocalCheck 3 'Entra Cloud Sync Connectivity Config' ("Invalid config file: " + $_.Exception.Message)
    }
}

$TimeoutSeconds = [Math]::Max(1, [Math]::Min(30, $TimeoutSeconds))
$TimeoutMs = $TimeoutSeconds * 1000

$CloudEndpoints = @(
    @{ Name = 'Entra Cloud Sync Microsoft Login'; Host = 'login.microsoftonline.com'; Port = 443 },
    @{ Name = 'Entra Cloud Sync Microsoft Graph'; Host = 'graph.microsoft.com'; Port = 443 }
)

foreach ($endpoint in $CloudEndpoints) {
    $ok = Test-TcpEndpoint $endpoint.Host $endpoint.Port $TimeoutMs
    if ($ok) {
        Write-LocalCheck 0 $endpoint.Name ("TCP connection to {0}:{1} succeeded" -f $endpoint.Host, $endpoint.Port)
    }
    else {
        Write-LocalCheck 2 $endpoint.Name ("TCP connection to {0}:{1} failed (timeout {2}s)" -f $endpoint.Host, $endpoint.Port, $TimeoutSeconds)
    }
}

if (-not $DomainController) {
    try {
        $domain = [System.DirectoryServices.ActiveDirectory.Domain]::GetComputerDomain()
        $DomainController = $domain.FindDomainController().Name
    }
    catch {
        $DomainController = $null
    }
}

if (-not $DomainController) {
    Write-LocalCheck 3 'Entra Cloud Sync LDAP Connectivity' 'No domain controller could be discovered; set domain_controller in entra_cloudsync_local.json'
    Write-LocalCheck 3 'Entra Cloud Sync Global Catalog Connectivity' 'No domain controller could be discovered; set domain_controller in entra_cloudsync_local.json'
    exit 0
}

$DirectoryEndpoints = @(
    @{ Name = 'Entra Cloud Sync LDAP Connectivity'; Host = $DomainController; Port = 389 },
    @{ Name = 'Entra Cloud Sync Global Catalog Connectivity'; Host = $DomainController; Port = 3268 }
)

foreach ($endpoint in $DirectoryEndpoints) {
    $ok = Test-TcpEndpoint $endpoint.Host $endpoint.Port $TimeoutMs
    if ($ok) {
        Write-LocalCheck 0 $endpoint.Name ("TCP connection to {0}:{1} succeeded" -f $endpoint.Host, $endpoint.Port)
    }
    else {
        Write-LocalCheck 2 $endpoint.Name ("TCP connection to {0}:{1} failed (timeout {2}s)" -f $endpoint.Host, $endpoint.Port, $TimeoutSeconds)
    }
}

exit 0
