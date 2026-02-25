$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'test-backend.ps1')
& (Join-Path $PSScriptRoot 'test-frontend.ps1')
