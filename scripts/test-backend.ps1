param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $PytestArgs
)

$ErrorActionPreference = 'Stop'
$projectRoot = if ($env:PROJECT_ROOT) { $env:PROJECT_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot '..')) }
Set-Location (Join-Path $projectRoot 'backend')

if ($PytestArgs.Count -gt 0) {
  python -m pytest @PytestArgs
} else {
  python -m pytest -q
}
