# PowerShell script to deploy package to GitHub repo YutikSt88/cot-mvp-app
# Usage: powershell -ExecutionPolicy Bypass -File scripts/deploy_to_github.ps1

$ErrorActionPreference = "Stop"

$separator = "=" * 60
Write-Host $separator -ForegroundColor Cyan
Write-Host "Deploy to GitHub" -ForegroundColor Cyan
Write-Host $separator -ForegroundColor Cyan
Write-Host ""

# Get project root
$root = Split-Path -Parent $PSScriptRoot
$deploySource = Join-Path $root "deploy\streamlit_app"
$deployRepo = Join-Path $root "deploy_repo"
$remoteUrl = "https://github.com/YutikSt88/cot-mvp-app.git"

# Step 1: Build deploy package
Write-Host "Step 1: Building deploy package..." -ForegroundColor Cyan
python scripts/build_deploy_package.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Build failed" -ForegroundColor Red
    exit 1
}

# Step 2: Smoke test
Write-Host "Step 2: Running smoke test..." -ForegroundColor Cyan
python scripts/smoke_test_deploy.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Smoke test failed" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Build and smoke test passed" -ForegroundColor Green
Write-Host ""

# Step 3: Ensure deploy repo exists
Write-Host "Step 3: Ensuring deploy repository exists..." -ForegroundColor Cyan
if (-not (Test-Path $deployRepo)) {
    New-Item -ItemType Directory -Path $deployRepo -Force | Out-Null
    Write-Host "[OK] Created directory: $deployRepo" -ForegroundColor Green
} else {
    Write-Host "[OK] Directory exists: $deployRepo" -ForegroundColor Green
}

# Step 4: Initialize git if needed
Push-Location $deployRepo

if (-not (Test-Path ".git")) {
    Write-Host "Step 4: Initializing git repository..." -ForegroundColor Cyan
    git init
    Write-Host "[OK] Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "[OK] Git repository already exists" -ForegroundColor Green
}

# Step 5: Set local git identity
Write-Host "Step 5: Configuring git identity (local)..." -ForegroundColor Cyan
git config user.name "YutikSt88"
git config user.email "yutikst88@users.noreply.github.com"
Write-Host "[OK] Git identity configured" -ForegroundColor Green

# Step 6: Ensure remote origin is correct
Write-Host "Step 6: Configuring remote origin..." -ForegroundColor Cyan

# Get current remotes using safe command
$remoteOutput = git remote -v 2>&1
$hasOrigin = $remoteOutput -match "origin"

if ($hasOrigin) {
    # Check if URL matches exactly
    $originUrl = ""
    foreach ($line in $remoteOutput) {
        if ($line -match "origin\s+(fetch|push)\s+(.+)") {
            $originUrl = $matches[2].Trim()
            break
        }
    }
    
    if ($originUrl -ne $remoteUrl) {
        Write-Host "Updating remote origin URL..." -ForegroundColor Yellow
        git remote set-url origin $remoteUrl
        Write-Host "[OK] Remote origin updated to: $remoteUrl" -ForegroundColor Green
    } else {
        Write-Host "[OK] Remote origin already correct: $remoteUrl" -ForegroundColor Green
    }
} else {
    Write-Host "Adding remote origin..." -ForegroundColor Yellow
    git remote add origin $remoteUrl
    Write-Host "[OK] Remote origin added: $remoteUrl" -ForegroundColor Green
}

# Step 7: Ensure branch is main
Write-Host "Step 7: Ensuring branch is main..." -ForegroundColor Cyan
git checkout -B main
Write-Host "[OK] On main branch" -ForegroundColor Green

# Step 8: Hard-sync contents (delete everything except .git, then copy new)
Write-Host "Step 8: Hard-syncing deploy package..." -ForegroundColor Cyan

# Delete everything except .git
Get-ChildItem -Path $deployRepo -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Copy all files from deploy package
if (-not (Test-Path $deploySource)) {
    Write-Host "Error: Deploy source not found: $deploySource" -ForegroundColor Red
    Pop-Location
    exit 1
}

Copy-Item -Path "$deploySource\*" -Destination $deployRepo -Recurse -Force
Write-Host "[OK] Deploy package copied" -ForegroundColor Green

# Step 8b: Write DEPLOY_VERSION.txt
Write-Host "Writing DEPLOY_VERSION.txt..." -ForegroundColor Cyan
$commitHash = git rev-parse HEAD -ErrorAction SilentlyContinue
if (-not $commitHash) {
    $commitHash = "unknown"
}
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$deployVersionContent = @"
DEPLOY VERSION
Commit: $commitHash
Timestamp: $timestamp
Source: cot-mvp repository
"@
$deployVersionContent | Out-File -FilePath (Join-Path $deployRepo "DEPLOY_VERSION.txt") -Encoding UTF8
Write-Host "[OK] DEPLOY_VERSION.txt created" -ForegroundColor Green

# Step 9: Commit and push
Write-Host "Step 9: Committing and pushing..." -ForegroundColor Cyan

git add -A

$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "[OK] No changes to push" -ForegroundColor Green
    Pop-Location
    exit 0
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$commitMessage = "Deploy package update $timestamp"

Write-Host "Creating commit..." -ForegroundColor Cyan
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Commit failed" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "Pushing to remote..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Push failed" -ForegroundColor Red
    Write-Host "Check your git credentials and remote URL." -ForegroundColor Yellow
    Pop-Location
    exit 1
}

Pop-Location

# Step 10: Final verification message
Write-Host ""
Write-Host $separator -ForegroundColor Green
Write-Host "[OK] Deploy package pushed successfully!" -ForegroundColor Green
Write-Host $separator -ForegroundColor Green
Write-Host ""
Write-Host "Verify on GitHub: app.py should exist in repo root" -ForegroundColor Yellow
Write-Host "  URL: https://github.com/YutikSt88/cot-mvp-app" -ForegroundColor Cyan
Write-Host "  File: https://github.com/YutikSt88/cot-mvp-app/blob/main/app.py" -ForegroundColor Gray
Write-Host ""
Write-Host "Streamlit Cloud should auto-redeploy." -ForegroundColor Cyan
