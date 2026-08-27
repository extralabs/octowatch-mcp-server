# Opens remaining directory / Marketplace pages for octowatch-mcp (no ExtrLabs MCP hosting).
# Already submitted: Glama, mcpservers.org, mcpfind.org. Skipping mcp.so (paid).

$repo = "https://github.com/extralabs/octowatch-mcp-server"
$blurb = "Read-only OctoWatch DLP Cloud MCP; runs locally; demo credentials or your console login."

Write-Host "Repo:  $repo"
Write-Host "Blurb: $blurb"
Write-Host ""
Write-Host "Already submitted: Glama, mcpservers.org, mcpfind.org"
Write-Host "Skipped: mcp.so (paid)"
Write-Host "Opening remaining / status pages..."

$urls = @(
  "https://glama.ai/mcp/servers?q=octowatch",
  "https://mcpservers.org/",
  "https://mcpfind.org/",
  "https://cursor.directory/plugins/new",
  "https://cursor.com/marketplace/publish",
  "https://www.pulsemcp.com/servers?q=octowatch",
  "https://github.com/punkpeye/awesome-mcp-servers/pull/13003"
)

foreach ($u in $urls) {
  Write-Host "Opening $u"
  Start-Process $u
}
