param(
    [string]$HermesSkillsPath = "$env:USERPROFILE\.hermes\skills",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceSkill = Join-Path $repoRoot "extensions\skills\server-admin"
$targetSkill = Join-Path $HermesSkillsPath "server-admin"

New-Item -ItemType Directory -Path $HermesSkillsPath -Force | Out-Null

if ((Test-Path $targetSkill) -and -not $Force) {
    Write-Error "Target skill already exists at $targetSkill. Use -Force to overwrite."
}

Copy-Item -Path $sourceSkill -Destination $targetSkill -Recurse -Force
Write-Host "Skill synced to $targetSkill"

