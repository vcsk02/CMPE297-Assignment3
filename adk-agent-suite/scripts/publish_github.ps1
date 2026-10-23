param([string]$RepoName = "adk-agent-suite", [switch]$Public)
$ErrorActionPreference = "Stop"
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "Install GitHub CLI, then run gh auth login." }
gh auth status
if ($LASTEXITCODE -ne 0) { throw "GitHub authentication required." }
git rev-parse --git-dir 2>$null
if ($LASTEXITCODE -ne 0) { git init -b main }
git add .
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m "Build five end-to-end ADK agents and walkthrough artifacts" }
git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    git push -u origin HEAD
} else {
    $Visibility = if ($Public) { "--public" } else { "--private" }
    gh repo create $RepoName $Visibility --source . --remote origin --push
}
if ($LASTEXITCODE -ne 0) { throw "GitHub publishing failed." }
gh repo view --json url --jq .url
