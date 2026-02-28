param(
  [ValidateSet('all', 'backend', 'frontend')]
  [string] $Target = 'all',
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $ArgsForTarget
)

$ErrorActionPreference = 'Stop'

switch ($Target) {
  'all' {
    if ($ArgsForTarget.Count -gt 0) {
      throw "all 指定時は追加引数を受け付けません。backend または frontend を指定してください。"
    }
    & (Join-Path $PSScriptRoot 'test-backend.ps1')
    & (Join-Path $PSScriptRoot 'test-frontend.ps1')
  }
  'backend' {
    & (Join-Path $PSScriptRoot 'test-backend.ps1') @ArgsForTarget
  }
  'frontend' {
    & (Join-Path $PSScriptRoot 'test-frontend.ps1') @ArgsForTarget
  }
}
