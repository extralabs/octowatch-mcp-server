# Sync GitHub About (description, homepage, topics) for SEO / directory crawlers.
# Requires: gh auth login  OR  $env:GITHUB_TOKEN with repo scope.
# Usage:  ./scripts/sync-github-about.ps1

$ErrorActionPreference = "Stop"
$owner = "extralabs"
$repo = "octowatch-mcp-server"

$description = "Read-only MCP server for OctoWatch DLP Cloud (octowatchdlp.com) - risks, idle time, productivity, and employee monitoring for Cursor, Claude, and VS Code."
$homepage = "https://octowatchdlp.com/"
$topics = @(
  "mcp",
  "mcp-server",
  "model-context-protocol",
  "dlp",
  "employee-monitoring",
  "python",
  "security",
  "octowatch"
)

function Get-GitHubToken {
  if ($env:GITHUB_TOKEN) { return $env:GITHUB_TOKEN }
  if ($env:GH_TOKEN) { return $env:GH_TOKEN }
  $gh = Get-Command gh -ErrorAction SilentlyContinue
  if ($gh) {
    $t = & gh auth token 2>$null
    if ($LASTEXITCODE -eq 0 -and $t) { return $t.Trim() }
  }
  return $null
}

$token = Get-GitHubToken
if (-not $token) {
  Write-Host @"
No GitHub auth found (gh CLI or GITHUB_TOKEN / GH_TOKEN).

Set About manually:
  https://github.com/$owner/$repo
  -> About (pencil) -> Website = $homepage
  -> Description = (see docs/distribution.md)
"@
  exit 1
}

$headers = @{
  Accept                 = "application/vnd.github+json"
  Authorization          = "Bearer $token"
  "X-GitHub-Api-Version" = "2022-11-28"
}

$patchBody = @{
  description = $description
  homepage    = $homepage
} | ConvertTo-Json

Write-Host "PATCH repos/$owner/$repo (description + homepage)..."
Invoke-RestMethod `
  -Method Patch `
  -Uri "https://api.github.com/repos/$owner/$repo" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $patchBody | Out-Null

$topicsBody = @{ names = $topics } | ConvertTo-Json
$topicHeaders = @{
  Accept                 = "application/vnd.github.mercy-preview+json"
  Authorization          = "Bearer $token"
  "X-GitHub-Api-Version" = "2022-11-28"
}
Write-Host "PUT repos/$owner/$repo/topics..."
Invoke-RestMethod `
  -Method Put `
  -Uri "https://api.github.com/repos/$owner/$repo/topics" `
  -Headers $topicHeaders `
  -ContentType "application/json" `
  -Body $topicsBody | Out-Null

$check = Invoke-RestMethod `
  -Uri "https://api.github.com/repos/$owner/$repo" `
  -Headers $headers

$topicList = ($check.topics -join ", ")
Write-Host ""
Write-Host "OK - GitHub About synced:"
Write-Host "  description: $($check.description)"
Write-Host "  homepage:    $($check.homepage)"
Write-Host "  topics:      $topicList"
