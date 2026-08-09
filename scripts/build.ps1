$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    python tools/build.py
    python -m unittest discover -s tests -v
    python tools/validate.py
}
finally {
    Pop-Location
}

