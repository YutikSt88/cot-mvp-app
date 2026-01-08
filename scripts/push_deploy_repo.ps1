# PowerShell script to build and push deploy package to GitHub repo
# Usage: powershell -ExecutionPolicy Bypass -File scripts/push_deploy_repo.ps1 -DeployRepoPath "path/to/deploy_repo"

param(
    [Parameter(Mandatory=$true)]
    [string]$DeployRepoPath
)

$ErrorActionPreference = "Stop"

$separator = "=" * 60
Write-Host $separator -ForegroundColor Cyan
Write-Host "Deploy Package Push Script" -ForegroundColor Cyan
Write-Host $separator -ForegroundColor Cyan
Write-Host ""

# Step 1: Always rebuild and smoke-test
Write-Host "Step 1: Building deploy package..." -ForegroundColor Cyan
python scripts/build_deploy_package.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Step 2: Running smoke test..." -ForegroundColor Cyan
python scripts/smoke_test_deploy.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Smoke test failed" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Build and smoke test passed" -ForegroundColor Green
Write-Host ""

# Step 2: Ensure deploy repo exists and is a git repo
$root = Split-Path -Parent $PSScriptRoot
$deploySource = Join-Path $root "deploy\streamlit_app"
$deployRepo = Resolve-Path $DeployRepoPath -ErrorAction SilentlyContinue

if (-not $deployRepo) {
    # Path doesn't exist, create it
    Write-Host "Step 3: Creating deploy repository directory..." -ForegroundColor Cyan
    $deployRepo = New-Item -ItemType Directory -Path $DeployRepoPath -Force
    $deployRepo = $deployRepo.FullName
    Write-Host "[OK] Created directory: $deployRepo" -ForegroundColor Green
} else {
    $deployRepo = $deployRepo.Path
}

if (-not (Test-Path $deploySource)) {
    Write-Host "Error: deploy/streamlit_app not found. Run build_deploy_package.py first." -ForegroundColor Red
    exit 1
}

# Step 3: Initialize git if needed
Push-Location $deployRepo

if (-not (Test-Path ".git")) {
    Write-Host "Step 4: Initializing git repository..." -ForegroundColor Cyan
    git init
    git branch -M main
    Write-Host "[OK] Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "[OK] Git repository already exists" -ForegroundColor Green
}

# Step 4: Ensure remote origin is set correctly
$remoteUrl = "https://github.com/YutikSt88/cot-mvp-app.git"

Write-Host "Step 5: Configuring remote origin..." -ForegroundColor Cyan

# Check if origin exists using git remote -v (safe for Windows)
$remoteOutput = git remote -v 2>&1
$hasOrigin = $remoteOutput -match "origin"

if ($hasOrigin) {
    # Check if URL matches
    $originUrl = ""
    foreach ($line in $remoteOutput) {
        if ($line -match "origin\s+(fetch|push)\s+(.+)") {
            $originUrl = $matches[2]
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

# Step 5: Set git identity (repo-local) if missing
Write-Host "Step 6: Configuring git identity (local)..." -ForegroundColor Cyan
git config user.name "YutikSt88"
git config user.email "yutikst88@users.noreply.github.com"
Write-Host "[OK] Git identity configured" -ForegroundColor Green

# Step 6: Ensure branch is main
$currentBranch = git branch --show-current -ErrorAction SilentlyContinue
if (-not $currentBranch) {
    Write-Host "Creating main branch..." -ForegroundColor Cyan
    git checkout -b main
} elseif ($currentBranch -ne "main") {
    Write-Host "Switching to main branch..." -ForegroundColor Cyan
    git checkout -b main -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        git checkout main
    }
}
Write-Host "[OK] On main branch" -ForegroundColor Green

# Step 7: Copy deploy package (remove everything except .git, then copy new files)
Write-Host "Step 7: Copying deploy package..." -ForegroundColor Cyan

# Remove everything except .git directory
Get-ChildItem -Path $deployRepo -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Copy all files from deploy package
Copy-Item -Path "$deploySource\*" -Destination $deployRepo -Recurse -Force

Write-Host "[OK] Deploy package copied" -ForegroundColor Green

# Step 8: Check for changes
Write-Host "Step 8: Checking for changes..." -ForegroundColor Cyan
$status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "[OK] No changes to push" -ForegroundColor Green
    Pop-Location
    exit 0
}

# Step 9: Commit and push
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$commitMessage = "Deploy package update $timestamp"

Write-Host "Staging changes..." -ForegroundColor Cyan
git add -A

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

# Step 10: Print final verification
Write-Host ""
$separator = "=" * 60
Write-Host $separator -ForegroundColor Green
Write-Host "[OK] Deploy package pushed successfully!" -ForegroundColor Green
Write-Host $separator -ForegroundColor Green
Write-Host ""

Write-Host "Verification:" -ForegroundColor Cyan
Write-Host "  Last commit:" -ForegroundColor Gray
git log -1 --oneline
Write-Host ""
Write-Host "  Remote:" -ForegroundColor Gray
git remote -v
Write-Host ""
Write-Host "  Verify GitHub has app.py in root:" -ForegroundColor Yellow
Write-Host "    https://github.com/YutikSt88/cot-mvp-app/blob/main/app.py" -ForegroundColor Gray
Write-Host ""

Pop-Location

Write-Host "Streamlit Cloud should auto-redeploy." -ForegroundColor Cyan
