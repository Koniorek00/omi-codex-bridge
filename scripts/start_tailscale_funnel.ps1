param(
  [int]$LocalPort = 8766
)

$status = tailscale status --json | ConvertFrom-Json
if ($status.BackendState -ne "Running") {
  Write-Host "Tailscale is not logged in/running for this machine."
  Write-Host "Run: tailscale up"
  Write-Host "Then rerun this script."
  exit 1
}

$dnsName = $status.Self.DNSName.TrimEnd(".")
if (-not $dnsName) {
  Write-Host "Tailscale is running, but MagicDNS did not report a DNS name for this machine."
  exit 1
}

$certProbe = Join-Path $env:TEMP "omi-codex-bridge-tailscale-cert-probe.crt"
$keyProbe = Join-Path $env:TEMP "omi-codex-bridge-tailscale-cert-probe.key"
tailscale cert --cert-file $certProbe --key-file $keyProbe $dnsName *> $null
$certExitCode = $LASTEXITCODE
Remove-Item -LiteralPath $certProbe, $keyProbe -Force -ErrorAction SilentlyContinue
if ($certExitCode -ne 0) {
  Write-Host "Tailscale HTTPS certificates are not available for this tailnet yet."
  Write-Host "Funnel requires HTTPS cert support. Enable HTTPS/Funnel in the Tailscale admin console, then rerun this script."
  Write-Host "Tailnet-local fallback for testing:"
  Write-Host "  tailscale serve --bg --yes --http=$LocalPort localhost:$LocalPort"
  exit 1
}

Write-Host "Starting Tailscale Funnel for http://127.0.0.1:$LocalPort"
tailscale funnel --bg --yes $LocalPort
tailscale funnel status
