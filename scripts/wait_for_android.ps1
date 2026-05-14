param(
  [int]$TimeoutSeconds = 900,
  [string]$Package = "com.friend.ios",
  [switch]$OpenOmi,
  [switch]$StartScrcpy
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$scrcpy = "F:\ag projects\Wik_AI\omi_automation\windows\scrcpy\scrcpy-win64-v3.3.4\scrcpy.exe"

Write-Host "Waiting for authorized Android device. Accept the USB debugging prompt on the phone."
while ((Get-Date) -lt $deadline) {
  $devices = adb devices -l
  $authorized = $devices | Where-Object { $_ -match "\bdevice\b" -and $_ -match "product:" } | Select-Object -First 1
  $unauthorized = $devices | Where-Object { $_ -match "unauthorized" } | Select-Object -First 1
if ($authorized) {
    Write-Host "Android authorized: $authorized"
    if ($OpenOmi) {
      adb shell monkey -p $Package -c android.intent.category.LAUNCHER 1 | Out-Null
      Write-Host "Opened Omi package $Package"
    }
    if ($StartScrcpy -and (Test-Path $scrcpy)) {
      Start-Process -FilePath $scrcpy -ArgumentList @("--stay-awake", "--turn-screen-on") | Out-Null
      Write-Host "Started scrcpy"
    }
    exit 0
  }
  if ($unauthorized) {
    Write-Host "Still unauthorized. Check the phone screen."
  } else {
    Write-Host "No Android device yet."
  }
  Start-Sleep -Seconds 5
}

throw "Timed out waiting for authorized Android device."
