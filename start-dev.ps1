$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$venvActivate = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $venvActivate)) {
    Write-Error "Python virtual environment not found at $venvActivate. Create it with: py -3.11 -m venv .venv"
    exit 1
}

. $venvActivate
python (Join-Path $PSScriptRoot 'run_local.py')
exit $LASTEXITCODE
