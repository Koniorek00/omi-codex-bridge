param(
  [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& "$PSScriptRoot\start_local_bridge.ps1" -Port $Port -Background
Start-Sleep -Seconds 2
& "$PSScriptRoot\start_cloudflare_quick_tunnel.ps1" -Port $Port
& "$PSScriptRoot\write_setup_urls.ps1"
& "$PSScriptRoot\doctor.ps1" -Port $Port

Write-Host "Ready. Private Omi setup file: $root\runtime\omi-setup-urls.private.txt"
Write-Host "Phone mode: quiet status notifications are enabled; screen-control is opt-in only."
