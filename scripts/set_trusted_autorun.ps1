param(
  [string]$Uid = "",
  [string]$RemoveUid = "",
  [switch]$Enable,
  [switch]$Disable,
  [switch]$List
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $root "runtime"
$trustedPath = Join-Path $runtimeDir "trusted-uids.txt"
$autorunPath = Join-Path $runtimeDir "autorun.enabled"

if (-not (Test-Path -LiteralPath $runtimeDir)) {
  New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
}

if ($Enable -and $Disable) {
  throw "Use either -Enable or -Disable, not both."
}

function Normalize-Uid([string]$Value, [string]$Name) {
  $clean = $Value.Trim()
  if (-not $clean) {
    return ""
  }
  if ($clean -match "[\r\n,;]") {
    throw "$Name must be one UID only. Commas, semicolons, and newlines are not allowed."
  }
  return $clean
}

function Read-TrustedUids {
  if (-not (Test-Path -LiteralPath $trustedPath)) {
    return [string[]]@()
  }
  $seen = @{}
  $values = New-Object System.Collections.Generic.List[string]
  foreach ($rawLine in Get-Content -LiteralPath $trustedPath) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      continue
    }
    foreach ($part in ($line -split "[,;]")) {
      $item = $part.Trim()
      if ($item -and -not $seen.ContainsKey($item)) {
        $seen[$item] = $true
        $values.Add($item)
      }
    }
  }
  return [string[]]$values.ToArray()
}

function Write-TrustedUids([string[]]$Values) {
  $clean = [string[]]@($Values | Where-Object { $_ } | Select-Object -Unique)
  if ($clean.Count -eq 0) {
    Remove-Item -LiteralPath $trustedPath -Force -ErrorAction SilentlyContinue
    return
  }
  Set-Content -LiteralPath $trustedPath -Value $clean -Encoding ASCII
}

if ($Uid) {
  $Uid = Normalize-Uid $Uid "Uid"
  $known = Read-TrustedUids
  if ($known -notcontains $Uid) {
    Write-TrustedUids ([string[]]@($known + $Uid))
  }
}

if ($RemoveUid) {
  $RemoveUid = Normalize-Uid $RemoveUid "RemoveUid"
  $known = Read-TrustedUids
  Write-TrustedUids ([string[]]@($known | Where-Object { $_ -ne $RemoveUid }))
}

if ($Disable) {
  Remove-Item -LiteralPath $autorunPath -Force -ErrorAction SilentlyContinue
}

if ($Enable) {
  $knownAfterUid = Read-TrustedUids
  if ($knownAfterUid.Count -eq 0) {
    throw "Refusing to enable autorun without at least one trusted Omi UID."
  }
  Set-Content -LiteralPath $autorunPath -Value "enabled" -NoNewline -Encoding ASCII
}

$trusted = Read-TrustedUids
$trustedOutput = [string[]]@()
if ($List) {
  $trustedOutput = [string[]]@($trusted)
}

[ordered]@{
  autorun = Test-Path -LiteralPath $autorunPath
  trusted_uid_count = $trusted.Count
  trusted_uids = $trustedOutput
  trusted_uids_file = $trustedPath
  autorun_file = $autorunPath
} | ConvertTo-Json -Compress
