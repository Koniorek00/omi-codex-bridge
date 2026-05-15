param(
  [switch]$Uninstall,
  [int]$Port = 8766,
  [int]$EveryMinutes = 15,
  [switch]$NoTunnel
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$stackScript = Join-Path $PSScriptRoot "start_stack.ps1"
$watchScript = Join-Path $PSScriptRoot "watch_stack.ps1"
$startupTask = "Omi Codex Bridge Startup"
$watchdogTask = "Omi Codex Bridge Watchdog"
$startupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "Omi Codex Bridge Watchdog.lnk"

function Remove-TaskIfPresent($Name) {
  Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
}

function Set-FriendlyTaskSettings($Name) {
  try {
    $settings = New-ScheduledTaskSettingsSet `
      -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries `
      -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
      -MultipleInstances IgnoreNew
    Set-ScheduledTask -TaskName $Name -Settings $settings | Out-Null
  } catch {
    Write-Warning "Task '$Name' was created, but settings could not be updated: $($_.Exception.Message)"
  }
}

function Stop-WatchdogProcesses {
  $currentPid = $PID
  Get-CimInstance Win32_Process |
    Where-Object {
      $_.ProcessId -ne $currentPid -and
      $_.CommandLine -and
      $_.CommandLine -match [regex]::Escape($watchScript)
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Install-StartupShortcut {
  $shortcutArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchScript`" -Port $Port -EveryMinutes $EveryMinutes"
  if ($NoTunnel) {
    $shortcutArgs += " -NoTunnel"
  }
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($startupShortcut)
  $shortcut.TargetPath = "powershell.exe"
  $shortcut.Arguments = $shortcutArgs
  $shortcut.WorkingDirectory = $root
  $shortcut.Description = "Starts and watches the Omi Codex Bridge stack"
  $shortcut.Save()
  Write-Host "[OmiCodexStack] Installed Startup shortcut fallback: $startupShortcut"
}

function Start-WatchdogNow {
  Stop-WatchdogProcesses
  $args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchScript`" -Port $Port -EveryMinutes $EveryMinutes"
  if ($NoTunnel) {
    $args += " -NoTunnel"
  }
  Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden | Out-Null
}

if ($Uninstall) {
  Remove-TaskIfPresent $startupTask
  Remove-TaskIfPresent $watchdogTask
  Stop-WatchdogProcesses
  if (Test-Path -LiteralPath $startupShortcut) {
    Remove-Item -LiteralPath $startupShortcut -Force
  }
  Write-Host "[OmiCodexStack] Removed startup/watchdog tasks."
  exit 0
}

if (-not (Test-Path -LiteralPath $stackScript)) {
  throw "Missing stack script: $stackScript"
}
if (-not (Test-Path -LiteralPath $watchScript)) {
  throw "Missing watch script: $watchScript"
}

$taskArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$stackScript`" -Port $Port"
if ($NoTunnel) {
  $taskArgs += " -NoTunnel"
}

Remove-TaskIfPresent $startupTask
Remove-TaskIfPresent $watchdogTask

try {
  $settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $taskArgs -WorkingDirectory $root
  $startupTrigger = New-ScheduledTaskTrigger -AtLogOn
  Register-ScheduledTask -TaskName $startupTask -Action $action -Trigger $startupTrigger -Settings $settings -Force | Out-Null

  $watchdogTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
  $watchdogTrigger.Repetition.Interval = "PT$EveryMinutes`M"
  $watchdogTrigger.Repetition.Duration = "P3650D"
  Register-ScheduledTask -TaskName $watchdogTask -Action $action -Trigger $watchdogTrigger -Settings $settings -Force | Out-Null
  Write-Host "[OmiCodexStack] Installed '$startupTask' and '$watchdogTask'."
} catch {
  Write-Warning "Scheduled tasks could not be installed: $($_.Exception.Message)"
  Install-StartupShortcut
  Start-WatchdogNow
}

Write-Host "[OmiCodexStack] Starting stack once now."
$runArgs = @("-ExecutionPolicy", "Bypass", "-File", $stackScript, "-Port", "$Port")
if ($NoTunnel) {
  $runArgs += "-NoTunnel"
}
& powershell @runArgs
