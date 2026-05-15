param(
  [int]$Port = 8766,
  [int]$EveryMinutes = 15,
  [switch]$NoTunnel
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $root "runtime"
$logDir = Join-Path $runtimeDir "logs"
$logPath = Join-Path $logDir "stack-watchdog.log"

if (-not (Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log($Message) {
  $line = "$(Get-Date -Format o) $Message"
  Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

Write-Log "watchdog started; port=$Port every=$EveryMinutes noTunnel=$NoTunnel"

while ($true) {
  try {
    $args = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start_stack.ps1"), "-Port", "$Port")
    if ($NoTunnel) {
      $args += "-NoTunnel"
    }
    & powershell @args *> (Join-Path $logDir "stack-watchdog-last-run.log")
    Write-Log "stack check completed"
  } catch {
    Write-Log "stack check failed: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds ([Math]::Max(60, $EveryMinutes * 60))
}
