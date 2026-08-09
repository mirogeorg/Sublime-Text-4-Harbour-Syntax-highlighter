param(
    [string]$PackagesDirectory = 'D:\accounts\st4\Data\Packages'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectRoot 'package\Harbour'
$ManifestDirectory = Join-Path $ProjectRoot 'local-only\deployments'
$RollbackDirectory = Join-Path $ManifestDirectory 'rollback'
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Target = Join-Path $PackagesDirectory 'Harbour'
$Stage = Join-Path $PackagesDirectory ".Harbour.deploy.$Timestamp"
$Backup = Join-Path $RollbackDirectory "harbour.rollback.$Timestamp"
$Failed = Join-Path $RollbackDirectory ".Harbour.failed.$Timestamp"
$MovedCurrent = $false

function Assert-ChildPath([string]$Candidate, [string]$Parent) {
    $ParentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    $CandidateFull = [System.IO.Path]::GetFullPath($Candidate)
    if (-not $CandidateFull.StartsWith($ParentFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside Packages directory: $CandidateFull"
    }
}

function Get-TreeDigest([string]$Directory) {
    $Rows = Get-ChildItem -LiteralPath $Directory -Recurse -File |
        Sort-Object FullName |
        ForEach-Object {
            $Relative = $_.FullName.Substring($Directory.TrimEnd('\').Length + 1).Replace('\', '/')
            $Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$Hash  $Relative"
        }
    $Joined = [String]::Join("`n", $Rows)
    $Bytes = [Text.Encoding]::UTF8.GetBytes($Joined)
    $Hasher = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($Hasher.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $Hasher.Dispose()
    }
}

if (-not (Test-Path -LiteralPath $PackagesDirectory -PathType Container)) {
    throw "Sublime Packages directory not found: $PackagesDirectory"
}
if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Generated package not found: $Source"
}
foreach ($Path in @($Target, $Stage)) {
    Assert-ChildPath $Path $PackagesDirectory
}
foreach ($Path in @($Backup, $Failed)) {
    Assert-ChildPath $Path $RollbackDirectory
}
if (Test-Path -LiteralPath $Stage) {
    throw "Staging path already exists: $Stage"
}
if (Test-Path -LiteralPath $Backup) {
    throw "Backup path already exists: $Backup"
}

$SourceDigest = Get-TreeDigest $Source
$null = New-Item -ItemType Directory -Path $RollbackDirectory -Force

try {
    Copy-Item -LiteralPath $Source -Destination $Stage -Recurse
    if (-not (Test-Path -LiteralPath (Join-Path $Stage 'Harbour.sublime-syntax') -PathType Leaf)) {
        throw 'Staged package is incomplete.'
    }
    if ((Get-TreeDigest $Stage) -ne $SourceDigest) {
        throw 'Staged package hash does not match the generated package.'
    }

    if (Test-Path -LiteralPath $Target) {
        Move-Item -LiteralPath $Target -Destination $Backup
        $MovedCurrent = $true
    }
    Move-Item -LiteralPath $Stage -Destination $Target

    if ((Get-TreeDigest $Target) -ne $SourceDigest) {
        throw 'Deployed package hash does not match the generated package.'
    }

    New-Item -ItemType Directory -Path $ManifestDirectory -Force | Out-Null
    $Manifest = [ordered]@{
        deployed_at = (Get-Date).ToString('o')
        packages_directory = [System.IO.Path]::GetFullPath($PackagesDirectory)
        source = [System.IO.Path]::GetFullPath($Source)
        target = [System.IO.Path]::GetFullPath($Target)
        backup = if ($MovedCurrent) { [System.IO.Path]::GetFullPath($Backup) } else { $null }
        source_digest = $SourceDigest
        rollback_available = $MovedCurrent
    }
    $Manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ManifestDirectory 'latest.json') -Encoding utf8
    Write-Host "DEPLOYED=$Target"
    Write-Host "BACKUP=$(if ($MovedCurrent) { $Backup } else { '<none>' })"
    Write-Host "DIGEST=$SourceDigest"
}
catch {
    $DeployError = $_
    if ($MovedCurrent -and (Test-Path -LiteralPath $Backup)) {
        if (Test-Path -LiteralPath $Target) {
            Move-Item -LiteralPath $Target -Destination $Failed
        }
        Move-Item -LiteralPath $Backup -Destination $Target
    }
    elseif (Test-Path -LiteralPath $Stage) {
        Move-Item -LiteralPath $Stage -Destination $Failed
    }
    throw $DeployError
}
