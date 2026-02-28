$ErrorActionPreference = 'Stop'
$projectRoot = if ($env:PROJECT_ROOT) { $env:PROJECT_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot '..')) }
Set-Location (Join-Path $projectRoot 'frontend')

if (-not (Test-Path '.\node_modules\.bin\react-scripts.cmd')) {
  Write-Host '[INFO] frontend 依存が見つからないため npm install を実行します...'
  npm install
}

$env:DISABLE_ESLINT_PLUGIN = 'true'
$env:BROWSER = 'none'
npm start
