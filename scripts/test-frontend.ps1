param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $TestArgs
)

$ErrorActionPreference = 'Stop'
$projectRoot = if ($env:PROJECT_ROOT) { $env:PROJECT_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot '..')) }
Set-Location (Join-Path $projectRoot 'frontend')

if (-not (Test-Path '.\node_modules\.bin\react-scripts.cmd')) {
  Write-Host '[INFO] frontend 依存が見つからないため npm install を実行します...'
  npm install
}

if (-not $env:CI) {
  $env:CI = '1'
}

if ($TestArgs.Count -gt 0) {
  npm test -- @TestArgs
} else {
  npm test -- --watchAll=false --passWithNoTests
}
