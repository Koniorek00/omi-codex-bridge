param(
  [int]$Port = 8766,
  [string]$Token = $env:OMI_CODEX_BRIDGE_TOKEN
)

if (-not $Token) {
  $Token = "dev-token-change-me"
  Write-Warning "Using default bridge token. Set OMI_CODEX_BRIDGE_TOKEN before exposing with Funnel."
}

$env:OMI_CODEX_BRIDGE_TOKEN = $Token
python -m uvicorn omi_codex_bridge.main:app --host 127.0.0.1 --port $Port

