param(
  [int]$Port = 8766,
  [string]$TokenFile = "runtime\current-token.txt"
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$tokenPath = Join-Path $root $TokenFile

function Show-Check($Name, $Ok, $Detail) {
  $state = if ($Ok) { "OK" } else { "BLOCKED" }
  Write-Host "[$state] $Name - $Detail"
}

$commands = "python", "codex", "tailscale", "adb"
foreach ($command in $commands) {
  $cmd = Get-Command $command -ErrorAction SilentlyContinue
  Show-Check $command ([bool]$cmd) ($(if ($cmd) { $cmd.Source } else { "not found on PATH" }))
}

$health = $null
try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5
  Show-Check "bridge health" ($health.status -eq "healthy") ($health | ConvertTo-Json -Compress)
} catch {
  Show-Check "bridge health" $false "not answering on http://127.0.0.1:$Port/health"
}

if (Test-Path $tokenPath) {
  $tokenLength = ((Get-Content -Raw -LiteralPath $tokenPath).Trim()).Length
  Show-Check "bridge token" ($tokenLength -ge 32) "stored at $tokenPath, length $tokenLength"
} else {
  Show-Check "bridge token" $false "missing; run scripts\start_local_bridge.ps1"
}

try {
  $adbDevices = adb devices -l
  $deviceLine = $adbDevices | Where-Object { $_ -match "device product:|unauthorized|offline" } | Select-Object -First 1
  if ($deviceLine -match "unauthorized") {
    Show-Check "android device" $false "connected but unauthorized; accept the USB debugging prompt on the phone"
  } elseif ($deviceLine -match "\bdevice\b") {
    Show-Check "android device" $true $deviceLine
  } else {
    Show-Check "android device" $false "no authorized Android device found"
  }
} catch {
  Show-Check "android device" $false $_.Exception.Message
}

try {
  $funnel = tailscale funnel status
  $public = ($funnel -join "`n") -match "https://"
  Show-Check "tailscale funnel" $public ($(if ($public) { "public HTTPS route is present" } else { "no public HTTPS route shown; run scripts\start_tailscale_funnel.ps1" }))
} catch {
  Show-Check "tailscale funnel" $false $_.Exception.Message
}

$quickTunnelFile = Join-Path $root "runtime\public-base-url.txt"
if (Test-Path $quickTunnelFile) {
  $quickTunnelUrl = (Get-Content -Raw -LiteralPath $quickTunnelFile).Trim()
  try {
    $quickHealth = Invoke-RestMethod -Uri "$quickTunnelUrl/health" -TimeoutSec 10
    Show-Check "cloudflare quick tunnel" ($quickHealth.status -eq "healthy") "public HTTPS health is reachable"
  } catch {
    Show-Check "cloudflare quick tunnel" $false "URL exists but health check failed: $quickTunnelUrl"
  }
} else {
  Show-Check "cloudflare quick tunnel" $false "not started; run scripts\start_cloudflare_quick_tunnel.ps1"
}

$setupText = Join-Path $root "runtime\omi-setup-urls.private.txt"
$setupHtml = Join-Path $root "runtime\omi-setup.private.html"
Show-Check "private setup sheet" ((Test-Path $setupText) -and (Test-Path $setupHtml)) "text and HTML setup files under runtime"
