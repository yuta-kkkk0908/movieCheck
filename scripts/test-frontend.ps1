$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Set-Location 'frontend'
npm test -- --watchAll=false
