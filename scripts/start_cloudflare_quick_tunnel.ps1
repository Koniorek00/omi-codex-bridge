param(
  [int]$Port = 8766,
  [string]$CloudflaredPath = "F:\ag projects\apps\Codex Improvement\codexui-tools\cloudflared.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $root "runtime"
$logDir = Join-Path $runtimeDir "logs"
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

if (-not (Test-Path $CloudflaredPath)) {
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "cloudflared was not found. Install Cloudflare.cloudflared or pass -CloudflaredPath."
  }
  $CloudflaredPath = $cmd.Source
}

$stdout = Join-Path $logDir "cloudflared.out.log"
$stderr = Join-Path $logDir "cloudflared.err.log"
$urlFile = Join-Path $runtimeDir "public-base-url.txt"

Start-Process -FilePath $CloudflaredPath -ArgumentList @("tunnel", "--url", "http://127.0.0.1:$Port") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null

$publicUrl = $null
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  $logs = @()
  if (Test-Path $stdout) { $logs += Get-Content -Raw -LiteralPath $stdout }
  if (Test-Path $stderr) { $logs += Get-Content -Raw -LiteralPath $stderr }
  $match = ($logs -join "`n") | Select-String -Pattern "https://[-a-z0-9]+\.trycloudflare\.com" -AllMatches
  if ($match.Matches.Count -gt 0) {
    $publicUrl = $match.Matches[0].Value
    break
  }
}

if (-not $publicUrl) {
  throw "cloudflared started, but no trycloudflare.com URL appeared in the logs yet. Check $stderr"
}

Set-Content -LiteralPath $urlFile -Value $publicUrl -NoNewline -Encoding ASCII
& "$PSScriptRoot\write_setup_urls.ps1" -BaseUrl $publicUrl
Write-Host "Public HTTPS base URL saved in $urlFile"
Write-Host $publicUrl
