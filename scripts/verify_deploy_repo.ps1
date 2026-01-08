# PowerShell script to verify deploy repository
# Usage: powershell -ExecutionPolicy Bypass -File scripts/verify_deploy_repo.ps1 [-DeployRepoPath "deploy_repo"]

param(
    [Parameter(Mandatory=$false)]
    [string]$DeployRepoPath = "deploy_repo"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$deployRepo = Join-Path $root $DeployRepoPath

$separator = "=" * 60
Write-Host "Verifying Deploy Repository" -ForegroundColor Cyan
Write-Host $separator
Write-Host "Deploy repo path: $deployRepo"
Write-Host ""

$errors = 0
$warnings = 0

# Check if deploy repo exists
if (-not (Test-Path $deployRepo)) {
    Write-Host "[ERROR] Deploy repository not found: $deployRepo" -ForegroundColor Red
    exit 1
}

Push-Location $deployRepo

# Check app.py exists
Write-Host "Checking app.py..." -ForegroundColor Cyan
if (Test-Path "app.py") {
    Write-Host "[OK] app.py exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] app.py not found in root" -ForegroundColor Red
    $errors++
}

# Check git remote
Write-Host "Checking git remote..." -ForegroundColor Cyan
if (Test-Path ".git") {
    $remoteOutput = git remote -v 2>&1
    $expectedUrl = "https://github.com/YutikSt88/cot-mvp-app.git"
    
    if ($remoteOutput -match "origin") {
        $hasCorrectUrl = $false
        foreach ($line in $remoteOutput) {
            if ($line -match "origin\s+(fetch|push)\s+(.+)") {
                $url = $matches[2]
                if ($url -eq $expectedUrl) {
                    $hasCorrectUrl = $true
                    Write-Host "[OK] Remote origin is correct: $expectedUrl" -ForegroundColor Green
                    break
                }
            }
        }
        
        if (-not $hasCorrectUrl) {
            Write-Host "[WARNING] Remote origin URL may be incorrect" -ForegroundColor Yellow
            Write-Host "  Current remotes:" -ForegroundColor Gray
            git remote -v
            $warnings++
        }
    } else {
        Write-Host "[ERROR] No remote 'origin' configured" -ForegroundColor Red
        $errors++
    }
} else {
    Write-Host "[ERROR] Not a git repository (.git not found)" -ForegroundColor Red
    $errors++
}

# Check current commit
Write-Host "Checking current commit..." -ForegroundColor Cyan
if (Test-Path ".git") {
    $commitHash = git rev-parse HEAD -ErrorAction SilentlyContinue
    if ($commitHash) {
        Write-Host "[OK] Current commit: $commitHash" -ForegroundColor Green
        Write-Host "  Last commit message:" -ForegroundColor Gray
        git log -1 --oneline
    } else {
        Write-Host "[WARNING] No commits yet" -ForegroundColor Yellow
        $warnings++
    }
}

# Check branch
Write-Host "Checking branch..." -ForegroundColor Cyan
if (Test-Path ".git") {
    $currentBranch = git branch --show-current -ErrorAction SilentlyContinue
    if ($currentBranch -eq "main") {
        Write-Host "[OK] On main branch" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Not on main branch (current: $currentBranch)" -ForegroundColor Yellow
        $warnings++
    }
}

Pop-Location

# Print summary
Write-Host ""
$separator = "=" * 60
Write-Host $separator
if ($errors -eq 0) {
    Write-Host "[OK] Verification passed" -ForegroundColor Green
    if ($warnings -gt 0) {
        Write-Host "  Warnings: $warnings" -ForegroundColor Yellow
    }
    exit 0
} else {
    Write-Host "[ERROR] Verification failed" -ForegroundColor Red
    Write-Host "  Errors: $errors" -ForegroundColor Red
    if ($warnings -gt 0) {
        Write-Host "  Warnings: $warnings" -ForegroundColor Yellow
    }
    exit 1
}
