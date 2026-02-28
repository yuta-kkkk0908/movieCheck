$ErrorActionPreference = 'Stop'
$projectRoot = if ($env:PROJECT_ROOT) { $env:PROJECT_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot '..')) }
Set-Location (Join-Path $projectRoot 'backend')
python main.py
