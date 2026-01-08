# PowerShell script to bootstrap deploy repository and push to GitHub
# Usage: powershell -ExecutionPolicy Bypass -File scripts/bootstrap_deploy_repo.ps1 [-DeployRepoPath "deploy_repo"]

param(
    [Parameter(Mandatory=$false)]
    [string]$DeployRepoPath = "deploy_repo"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$deploySource = Join-Path $root "deploy\streamlit_app"
$deployRepo = Join-Path $root $DeployRepoPath

Write-Host "Bootstrap Deploy Repository" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host "Deploy source: $deploySource" -ForegroundColor Gray
Write-Host "Deploy repo: $deployRepo" -ForegroundColor Gray
Write-Host ""

# Check if deploy source exists
if (-not (Test-Path $deploySource)) {
    Write-Host "Error: Deploy package not found: $deploySource" -ForegroundColor Red
    Write-Host "Run: python scripts/build_deploy_package.py first" -ForegroundColor Yellow
    exit 1
}

# Check if deploy repo exists
if (Test-Path $deployRepo) {
    Write-Host "Deploy repository exists: $deployRepo" -ForegroundColor Yellow
    
    # Check git status if .git exists
    if (Test-Path (Join-Path $deployRepo ".git")) {
        Push-Location $deployRepo
        Write-Host "Git repository detected. Current status:" -ForegroundColor Cyan
        git status --short
        Pop-Location
    } else {
        Write-Host "No .git found. Will initialize." -ForegroundColor Yellow
    }
} else {
    Write-Host "Creating deploy repository directory: $deployRepo" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $deployRepo -Force | Out-Null
}

# Initialize git if needed
Push-Location $deployRepo

if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Cyan
    git init
    Write-Host "[OK] Git initialized" -ForegroundColor Green
} else {
    Write-Host "[OK] Git repository already initialized" -ForegroundColor Green
}

# Configure git identity (local only)
Write-Host "Configuring git identity (local)..." -ForegroundColor Cyan
git config user.name "YutikSt88"
git config user.email "yutikst88@users.noreply.github.com"
Write-Host "[OK] Git identity configured" -ForegroundColor Green

# Set remote
$remoteUrl = "https://github.com/YutikSt88/cot-mvp-app.git"

# Check if origin exists (use simple command to avoid parsing issues)
$hasOrigin = $false
try {
    $null = git remote show origin 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $hasOrigin = $true
    }
} catch {
    $hasOrigin = $false
}

if ($hasOrigin) {
    Write-Host "Updating remote origin..." -ForegroundColor Cyan
    git remote set-url origin $remoteUrl
    Write-Host "[OK] Remote updated to: $remoteUrl" -ForegroundColor Green
} else {
    Write-Host "Adding remote origin..." -ForegroundColor Cyan
    git remote add origin $remoteUrl
    Write-Host "[OK] Remote added: $remoteUrl" -ForegroundColor Green
}

# Ensure branch is main
$currentBranch = git branch --show-current -ErrorAction SilentlyContinue
if (-not $currentBranch) {
    # No commits yet, create main branch
    Write-Host "Creating main branch..." -ForegroundColor Cyan
    git checkout -b main
    Write-Host "[OK] Main branch created" -ForegroundColor Green
} elseif ($currentBranch -ne "main") {
    # Switch to main or create if doesn't exist
    Write-Host "Switching to main branch..." -ForegroundColor Cyan
    git checkout -b main -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        git checkout main
    }
    Write-Host "[OK] On main branch" -ForegroundColor Green
} else {
    Write-Host "[OK] Already on main branch" -ForegroundColor Green
}

Pop-Location

# Copy deploy package
Write-Host "Copying deploy package..." -ForegroundColor Cyan
Copy-Item -Path "$deploySource\*" -Destination $deployRepo -Recurse -Force
Write-Host "[OK] Deploy package copied" -ForegroundColor Green

# Commit and push
Push-Location $deployRepo

$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
    Pop-Location
    exit 0
}

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

Pop-Location

Write-Host ""
Write-Host "=" * 60
Write-Host "[OK] Deploy repository bootstrapped successfully!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "Repository URL: $remoteUrl" -ForegroundColor Cyan
Write-Host "Branch: main" -ForegroundColor Cyan
Write-Host "Main file: app.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://share.streamlit.io" -ForegroundColor Gray
Write-Host "2. Click 'New app'" -ForegroundColor Gray
Write-Host "3. Select repository: YutikSt88/cot-mvp-app" -ForegroundColor Gray
Write-Host "4. Branch: main" -ForegroundColor Gray
Write-Host "5. Main file path: app.py" -ForegroundColor Gray
Write-Host "6. Click 'Deploy!'" -ForegroundColor Gray
