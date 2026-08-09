param(
    [string]$ManifestPath
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $ProjectRoot 'local-only\deployments\latest.json'
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Deployment manifest not found: $ManifestPath"
}

$Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
if (-not $Manifest.rollback_available -or -not $Manifest.backup) {
    throw 'This deployment has no rollback backup.'
}
$PackagesDirectory = [System.IO.Path]::GetFullPath([string]$Manifest.packages_directory)
$Target = [System.IO.Path]::GetFullPath([string]$Manifest.target)
$Backup = [System.IO.Path]::GetFullPath([string]$Manifest.backup)
$RollbackDirectory = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot 'local-only\deployments\rollback'))
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Replaced = Join-Path $RollbackDirectory ".Harbour.replaced.$Timestamp"
$PackagesPrefix = $PackagesDirectory.TrimEnd('\') + '\'
$RollbackPrefix = $RollbackDirectory.TrimEnd('\') + '\'
if (-not $Target.StartsWith($PackagesPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing target outside Packages directory: $Target"
}
foreach ($Path in @($Backup, $Replaced)) {
    if (-not $Path.StartsWith($RollbackPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing backup path outside rollback directory: $Path"
    }
}
if (-not (Test-Path -LiteralPath $Backup -PathType Container)) {
    throw "Rollback backup not found: $Backup"
}
if (Test-Path -LiteralPath $Replaced) {
    throw "Rollback preservation path already exists: $Replaced"
}

if (Test-Path -LiteralPath $Target) {
    Move-Item -LiteralPath $Target -Destination $Replaced
}
try {
    Move-Item -LiteralPath $Backup -Destination $Target
}
catch {
    if ((Test-Path -LiteralPath $Replaced) -and -not (Test-Path -LiteralPath $Target)) {
        Move-Item -LiteralPath $Replaced -Destination $Target
    }
    throw
}

$Manifest.rollback_available = $false
$Manifest | Add-Member -NotePropertyName rolled_back_at -NotePropertyValue (Get-Date).ToString('o') -Force
$Manifest | Add-Member -NotePropertyName replaced_package -NotePropertyValue $Replaced -Force
$Manifest | ConvertTo-Json | Set-Content -LiteralPath $ManifestPath -Encoding utf8
Write-Host "RESTORED=$Target"
Write-Host "REPLACED_PACKAGE=$Replaced"
