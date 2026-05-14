param(
  [string]$Package = "com.friend.ios"
)

$ErrorActionPreference = "Stop"
$devices = adb devices -l
$line = $devices | Where-Object { $_ -match "device product:" } | Select-Object -First 1
if (-not $line) {
  throw "No authorized Android device. If adb shows unauthorized, accept the USB debugging prompt on the phone."
}

adb shell monkey -p $Package -c android.intent.category.LAUNCHER 1
