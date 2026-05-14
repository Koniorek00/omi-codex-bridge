param(
  [int]$Limit = 10
)

$ErrorActionPreference = "Continue"

function Show-Section($Name) {
  Write-Host ""
  Write-Host "== $Name =="
}

Show-Section "Omi docs index"
try {
  $docs = Invoke-WebRequest -Uri "https://docs.omi.me/llms.txt" -UseBasicParsing -TimeoutSec 20
  $docs.Content -split "`n" |
    Select-String -Pattern "Chat Tools|Integration Apps|Notifications|Developer API|MCP|CLI" |
    Select-Object -First 12 |
    ForEach-Object { Write-Host $_.Line.Trim() }
} catch {
  Write-Host "Failed to fetch docs index: $($_.Exception.Message)"
}

Show-Section "GitHub issues"
try {
  gh issue list --repo BasedHardware/omi --state open --limit $Limit --search "webhook OR notification OR MCP OR chat tools OR Developer API"
} catch {
  Write-Host "GitHub issue search failed: $($_.Exception.Message)"
}

Show-Section "GitHub PRs"
try {
  gh pr list --repo BasedHardware/omi --state all --limit $Limit --search "webhook OR notification OR MCP OR chat tools OR Developer API"
} catch {
  Write-Host "GitHub PR search failed: $($_.Exception.Message)"
}

Show-Section "GitHub releases"
try {
  gh release list --repo BasedHardware/omi --limit $Limit
} catch {
  Write-Host "GitHub release list failed: $($_.Exception.Message)"
}
