# PowerShell script to create git commit and tag for release
# Usage: powershell -ExecutionPolicy Bypass -File scripts/tag_release.ps1

$ErrorActionPreference = "Stop"

Write-Host "Checking git status..." -ForegroundColor Cyan

# Check if there are changes
$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "Nothing to commit. Exiting." -ForegroundColor Yellow
    exit 0
}

Write-Host "Staging all changes..." -ForegroundColor Cyan
git add -A

Write-Host "Creating commit..." -ForegroundColor Cyan
$commitMessage = "v0.2: week navigator + OI tab polish + backups"
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Commit failed" -ForegroundColor Red
    exit 1
}

Write-Host "Creating tag v0.2..." -ForegroundColor Cyan
git tag -a v0.2 -m "v0.2 release: week navigator + OI tab polish + backups"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Tag creation failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Commit and tag created successfully" -ForegroundColor Green
Write-Host "  Commit: $commitMessage" -ForegroundColor Gray
Write-Host "  Tag: v0.2" -ForegroundColor Gray
Write-Host ""
Write-Host "Note: This script does NOT push to remote." -ForegroundColor Yellow
Write-Host "To push: git push origin main && git push origin v0.2" -ForegroundColor Yellow


