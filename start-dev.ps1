$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$venvActivate = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    . $venvActivate
}

python -m app run
exit $LASTEXITCODE
