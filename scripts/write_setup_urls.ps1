param(
  [string]$BaseUrl,
  [string]$TokenFile = "runtime\current-token.txt"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $root "runtime"
$tokenPath = Join-Path $root $TokenFile
$baseUrlPath = Join-Path $runtimeDir "public-base-url.txt"
$textPath = Join-Path $runtimeDir "omi-setup-urls.private.txt"
$htmlPath = Join-Path $runtimeDir "omi-setup.private.html"

if (-not (Test-Path $runtimeDir)) {
  New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

if (-not (Test-Path $tokenPath)) {
  throw "Missing token file. Run scripts\start_local_bridge.ps1 first."
}

$token = (Get-Content -Raw -LiteralPath $tokenPath).Trim()
if ($token.Length -lt 32) {
  throw "Bridge token is too short. Delete $tokenPath and rerun scripts\start_local_bridge.ps1."
}

if (-not $BaseUrl) {
  if (-not (Test-Path $baseUrlPath)) {
    throw "Missing public base URL. Run scripts\start_cloudflare_quick_tunnel.ps1 or pass -BaseUrl."
  }
  $BaseUrl = (Get-Content -Raw -LiteralPath $baseUrlPath).Trim()
}

$BaseUrl = $BaseUrl.TrimEnd("/")
Set-Content -LiteralPath $baseUrlPath -Value $BaseUrl -NoNewline -Encoding ASCII

$urls = [ordered]@{
  "App Home URL" = "$BaseUrl/omi/$token"
  "Setup completed URL" = "$BaseUrl/omi/$token/setup-completed"
  "Memory creation webhook" = "$BaseUrl/omi/$token/webhooks/memory"
  "Realtime transcript webhook" = "$BaseUrl/omi/$token/webhooks/realtime"
  "Chat Tools Manifest URL" = "$BaseUrl/omi/$token/.well-known/omi-tools.json"
}

$lines = @(
  "Omi Codex Bridge setup URLs - private because they include the bridge token",
  "Generated: $(Get-Date -Format o)",
  "",
  "Voice triggers: Hey Omi Codex ..., Ask Codex to ..., Tell Codex to ...",
  "Safety: OMI_CODEX_AUTORUN=0, so Omi requests queue first.",
  ""
)
foreach ($item in $urls.GetEnumerator()) {
  $lines += "$($item.Key): $($item.Value)"
}
Set-Content -LiteralPath $textPath -Value $lines -Encoding ASCII

$rows = foreach ($item in $urls.GetEnumerator()) {
  $label = [System.Net.WebUtility]::HtmlEncode($item.Key)
  $value = [System.Net.WebUtility]::HtmlEncode($item.Value)
  "<section><h2>$label</h2><input readonly value=""$value""><button data-copy=""$value"">Copy</button></section>"
}

$html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Omi Codex Setup URLs</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; padding: 24px; background: #f6f7f4; color: #141914; }
    main { max-width: 860px; margin: 0 auto; }
    h1 { font-size: 28px; margin: 0 0 8px; }
    p { color: #5f685f; }
    section { display: grid; grid-template-columns: minmax(150px, 220px) minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 12px; margin: 10px 0; background: white; border: 1px solid #dfe4da; border-radius: 8px; }
    h2 { font-size: 14px; margin: 0; }
    input { width: 100%; padding: 9px 10px; border: 1px solid #dfe4da; border-radius: 7px; }
    button { border: 0; border-radius: 7px; padding: 10px 12px; background: #111812; color: white; font-weight: 700; }
    code { background: #e9eee4; padding: 2px 5px; border-radius: 5px; }
    @media (max-width: 720px) { section { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Omi Codex Setup URLs</h1>
    <p>Private page. These URLs include the bridge token. Use them in Omi app setup fields. Voice requests queue first.</p>
    $($rows -join "`n    ")
    <p>Trigger phrases: <code>Hey Omi Codex ...</code>, <code>Ask Codex to ...</code>, <code>Tell Codex to ...</code></p>
  </main>
  <script>
    document.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-copy]");
      if (!button) return;
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = "Copied";
      setTimeout(() => button.textContent = "Copy", 900);
    });
  </script>
</body>
</html>
"@
Set-Content -LiteralPath $htmlPath -Value $html -Encoding UTF8

Write-Host "Wrote $textPath"
Write-Host "Wrote $htmlPath"
