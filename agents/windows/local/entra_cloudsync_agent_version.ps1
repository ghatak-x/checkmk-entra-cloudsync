# Microsoft Entra Cloud Sync agent version local check for Checkmk.
#
# Deploy this file on each Windows server that runs the Microsoft Entra
# Cloud Sync provisioning agent:
#   C:\ProgramData\checkmk\agent\local\entra_cloudsync_agent_version.ps1
#
# No additional PowerShell modules are required.

$ErrorActionPreference = 'Stop'
$ServiceName = 'AADConnectProvisioningAgent'
$CheckName = 'Entra Cloud Sync Agent Version'

function Write-LocalCheck([int]$State, [string]$Message) {
    Write-Output ("{0} `"{1}`" - {2}" -f $State, $CheckName, $Message)
}

try {
    $service = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'" -ErrorAction Stop
    if (-not $service) {
        Write-LocalCheck 2 "Microsoft Entra Cloud Sync provisioning agent service '$ServiceName' not found"
        exit 0
    }

    $pathName = [string]$service.PathName
    $exePath = $null

    if ($pathName -match '^\s*"([^"]+)"') {
        $exePath = $Matches[1]
    }
    elseif ($pathName -match '^\s*([^\s]+\.exe)') {
        $exePath = $Matches[1]
    }

    if (-not $exePath -or -not (Test-Path -LiteralPath $exePath)) {
        Write-LocalCheck 3 "Agent service exists, but executable path could not be resolved: $pathName"
        exit 0
    }

    $fileVersion = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($exePath)
    $version = $fileVersion.ProductVersion
    if ([string]::IsNullOrWhiteSpace($version)) {
        $version = $fileVersion.FileVersion
    }
    if ([string]::IsNullOrWhiteSpace($version)) {
        $version = 'unknown'
    }

    Write-LocalCheck 0 "Version: $version, executable: $exePath"
}
catch {
    Write-LocalCheck 3 ("Unable to determine Cloud Sync agent version: " + $_.Exception.Message)
}

# Checkmk local checks should exit 0 after emitting their own state.
exit 0
