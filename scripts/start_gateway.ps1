param(
    [string]$HermesHome = "$env:USERPROFILE\.hermes"
)

$ErrorActionPreference = "Stop"
$env:HERMES_HOME = $HermesHome

$hermes = Get-Command hermes -ErrorAction SilentlyContinue
if (-not $hermes) {
    Write-Error "The 'hermes' command was not found. Install Hermes first, then re-run this script."
}

& hermes gateway

