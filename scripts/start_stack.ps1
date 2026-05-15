param(
  [int]$Port = 8766,
  [switch]$NoTunnel,
  [switch]$NoAndroidSafe,
  [switch]$Doctor
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $root "runtime"
$publicUrlFile = Join-Path $runtimeDir "public-base-url.txt"
$androidPowerScript = "C:\Users\wikto\.codex\skills\android-connection\scripts\Set-AndroidPowerProfile.ps1"

function Write-Step($Message) {
  Write-Host "[OmiCodexStack] $Message"
}

function Test-LocalHealth {
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 15
    return ($health.status -eq "healthy")
  } catch {
    return $false
  }
}

function Test-PublicHealth {
  if (-not (Test-Path -LiteralPath $publicUrlFile)) {
    return $false
  }
  $publicUrl = (Get-Content -Raw -LiteralPath $publicUrlFile).Trim()
  if (-not $publicUrl) {
    return $false
  }
  try {
    $health = Invoke-RestMethod -Uri "$publicUrl/health" -TimeoutSec 20
    return ($health.status -eq "healthy")
  } catch {
    try {
      $uri = [Uri]$publicUrl
      $ip = Resolve-DnsName $uri.Host -Server 1.1.1.1 -Type A -ErrorAction Stop |
        Select-Object -First 1 -ExpandProperty IPAddress
      if (-not $ip) {
        return $false
      }
      $resolveArg = "$($uri.Host)`:443`:$ip"
      $raw = & curl.exe --resolve $resolveArg "$publicUrl/health" --max-time 25 --silent --show-error
      if ($LASTEXITCODE -ne 0 -or -not $raw) {
        return $false
      }
      $health = $raw | ConvertFrom-Json
      return ($health.status -eq "healthy")
    } catch {
      return $false
    }
  }
}

function Wait-ForLocalHealth {
  for ($i = 0; $i -lt 20; $i++) {
    if (Test-LocalHealth) {
      return $true
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

function Wait-ForPublicHealth {
  for ($i = 0; $i -lt 60; $i++) {
    if (Test-PublicHealth) {
      return $true
    }
    Start-Sleep -Seconds 2
  }
  return $false
}

function Stop-CloudflareTunnelForPort {
  $pattern = "tunnel --url http://(?:127\.0\.0\.1|localhost):$Port"
  $processes = @(Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match "cloudflared" -and $_.CommandLine -match $pattern } |
    Select-Object ProcessId)
  foreach ($item in $processes) {
    Stop-Process -Id $item.ProcessId -Force -ErrorAction SilentlyContinue
  }
}

Set-Location $root

if (-not (Test-LocalHealth)) {
  Write-Step "Local bridge is down; starting it on port $Port."
  & "$PSScriptRoot\start_local_bridge.ps1" -Port $Port -Background
  if (-not (Wait-ForLocalHealth)) {
    throw "Local bridge did not become healthy on port $Port."
  }
} else {
  Write-Step "Local bridge is healthy on port $Port."
}

if (-not $NoAndroidSafe -and (Test-Path -LiteralPath $androidPowerScript)) {
  try {
    & powershell -ExecutionPolicy Bypass -File $androidPowerScript -Mode safe | Out-Null
    Write-Step "Android quiet power profile is applied."
  } catch {
    Write-Step "Android quiet profile skipped: $($_.Exception.Message)"
  }
}

if (-not $NoTunnel) {
  if (Test-PublicHealth) {
    Write-Step "Public Cloudflare quick tunnel is healthy."
  } else {
    Write-Step "Public tunnel is down/stale; refreshing Cloudflare quick tunnel."
    Stop-CloudflareTunnelForPort
    Start-Sleep -Seconds 1
    & "$PSScriptRoot\start_cloudflare_quick_tunnel.ps1" -Port $Port | Out-Host
    if (-not (Wait-ForPublicHealth)) {
      throw "Public Cloudflare quick tunnel did not become healthy."
    }
  }
}

& "$PSScriptRoot\write_setup_urls.ps1" | Out-Null

if ($Doctor) {
  & "$PSScriptRoot\doctor.ps1" -Port $Port
}

Write-Step "Ready."
