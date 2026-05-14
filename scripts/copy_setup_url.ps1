param(
  [ValidateSet("home", "setup", "memory", "realtime", "manifest")]
  [string]$Name = "realtime"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$setupFile = Join-Path $root "runtime\omi-setup-urls.private.txt"

if (-not (Test-Path $setupFile)) {
  & "$PSScriptRoot\write_setup_urls.ps1"
}

$labels = @{
  home = "App Home URL"
  setup = "Setup completed URL"
  memory = "Memory creation webhook"
  realtime = "Realtime transcript webhook"
  manifest = "Chat Tools Manifest URL"
}

$label = $labels[$Name]
$line = Get-Content -LiteralPath $setupFile | Where-Object { $_ -like "$label*" } | Select-Object -First 1
if (-not $line) {
  throw "Could not find $label in $setupFile"
}

$url = ($line -replace "^[^:]+:\s*", "").Trim()
Set-Clipboard -Value $url
Write-Host "$label copied to clipboard."
