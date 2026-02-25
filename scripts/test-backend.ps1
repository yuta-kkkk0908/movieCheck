$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Set-Location 'backend'
python -m pytest -q
