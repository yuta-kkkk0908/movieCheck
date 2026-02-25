$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Set-Location 'backend'
python main.py
