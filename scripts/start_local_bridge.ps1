param(
  [int]$Port = 8766,
  [switch]$Background,
  [string]$Workspace = "F:\ag projects\apps\Omi",
  [string]$AllowedWorkspaces = "F:\ag projects;C:\Users\wikto\.codex\skills;C:\Users\wikto\.agents\skills;F:\programy\Obsidian\Codex Vault\Codex",
  [string]$ObsidianVault = "F:\programy\Obsidian\Codex Vault\Codex",
  [string]$ObsidianRoot = "Codex/Omi Codex Bridge",
  [switch]$DisableObsidian,
  [switch]$DisablePhoneStatus,
  [switch]$ExpandAndroidNotifications,
  [string]$TrustedUids = "",
  [string]$TokenFile = "runtime\current-token.txt"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tokenPath = Join-Path $root $TokenFile
$runtimeDir = Join-Path $root "runtime"

if (-not (Test-Path $runtimeDir)) {
  New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

if (-not (Test-Path $tokenPath)) {
  $bytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
  $token = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
  Set-Content -LiteralPath $tokenPath -Value $token -NoNewline -Encoding ASCII
} else {
  $token = (Get-Content -Raw -LiteralPath $tokenPath).Trim()
}

if ($token.Length -lt 32) {
  throw "Bridge token is too short. Delete $tokenPath and rerun this script."
}

$env:OMI_CODEX_BRIDGE_TOKEN = $token
$env:OMI_CODEX_WORKSPACE = $Workspace
$env:OMI_CODEX_ALLOWED_WORKSPACES = $AllowedWorkspaces
$env:OMI_CODEX_AUTORUN = "0"
$env:OMI_CODEX_AUTORUN_REQUIRE_TRUSTED_UID = "1"
$env:OMI_CODEX_TRUSTED_UIDS = $TrustedUids
$env:OMI_CODEX_RUNNER = "codex"
$env:OMI_CODEX_RUNTIME_DIR = $runtimeDir
$env:OMI_OBSIDIAN_ENABLED = if ($DisableObsidian) { "0" } else { "1" }
$env:OMI_OBSIDIAN_VAULT_PATH = $ObsidianVault
$env:OMI_OBSIDIAN_ROOT = $ObsidianRoot
$env:OMI_CODEX_PHONE_STATUS_UPDATES = if ($DisablePhoneStatus) { "0" } else { "1" }
$env:OMI_ANDROID_EXPAND_NOTIFICATIONS = if ($ExpandAndroidNotifications) { "1" } else { "0" }
$env:OMI_ANDROID_SLEEP_AFTER_NOTIFY = "1"
$env:OMI_NOTIFICATION_MODE = if ($env:OMI_NOTIFICATION_MODE) { $env:OMI_NOTIFICATION_MODE } else { "auto" }

if ($Background) {
  $logDir = Join-Path $runtimeDir "logs"
  if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
  }
  $stdout = Join-Path $logDir "bridge.out.log"
  $stderr = Join-Path $logDir "bridge.err.log"
  $argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$PSCommandPath`"",
    "-Port", "$Port",
    "-Workspace", "`"$Workspace`"",
    "-AllowedWorkspaces", "`"$AllowedWorkspaces`"",
    "-ObsidianVault", "`"$ObsidianVault`"",
    "-ObsidianRoot", "`"$ObsidianRoot`"",
    "-TrustedUids", "`"$TrustedUids`"",
    "-TokenFile", "`"$TokenFile`""
  )
  if ($DisableObsidian) {
    $argList += "-DisableObsidian"
  }
  if ($DisablePhoneStatus) {
    $argList += "-DisablePhoneStatus"
  }
  if ($ExpandAndroidNotifications) {
    $argList += "-ExpandAndroidNotifications"
  }
  Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
  Write-Host "Omi Codex Bridge starting in background on http://127.0.0.1:$Port"
  Write-Host "Token saved in $tokenPath"
  exit 0
}

Set-Location $root
python -m uvicorn omi_codex_bridge.main:app --host 127.0.0.1 --port $Port
