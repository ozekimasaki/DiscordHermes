param(
    [string]$HermesHome = "$env:USERPROFILE\.hermes",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $repoRoot "scripts\install_extension.py"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python is required to run install_extension.py."
}

$arguments = @($installer, "--hermes-home", $HermesHome)
if ($Force) {
    $arguments += "--force"
}

& python @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
