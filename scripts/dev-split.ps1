$ErrorActionPreference = 'Stop'
$root = if ($env:PROJECT_ROOT) { $env:PROJECT_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot '..')) }

Start-Process powershell -WorkingDirectory $root -ArgumentList '-NoExit','-Command','npm run backend'
Start-Process powershell -WorkingDirectory $root -ArgumentList '-NoExit','-Command','npm run frontend'

Write-Host 'Started backend and frontend in separate PowerShell windows.'
