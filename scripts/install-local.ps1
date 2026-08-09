param(
    [string]$PackagesDirectory = 'D:\accounts\st4\Data\Packages'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectRoot 'package\Harbour'
$Target = Join-Path $PackagesDirectory 'Harbour'
if (-not (Test-Path -LiteralPath $Source)) {
    throw "Generated package not found: $Source"
}
if (Test-Path -LiteralPath $Target) {
    throw "Target already exists; move it aside explicitly before installation: $Target"
}
Copy-Item -LiteralPath $Source -Destination $Target -Recurse
Write-Host "Installed $Source -> $Target"

