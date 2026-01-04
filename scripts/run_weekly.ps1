# Weekly COT Pipeline Runner
# Runs pipeline steps in order with error handling and logging

param(
    [string]$Root = $null
)

# Determine repo root
if ($Root) {
    $RepoRoot = (Resolve-Path $Root).Path
} else {
    # If script is in scripts/, repo root is parent
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}

# Change to repo root
Push-Location $RepoRoot
try {
    Write-Host "================================================"
    Write-Host "Weekly COT Pipeline Runner"
    Write-Host "Repo root: $RepoRoot"
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "================================================"
    
    # Create logs directory if missing
    $LogsDir = Join-Path $RepoRoot "logs"
    if (-not (Test-Path $LogsDir)) {
        New-Item -ItemType Directory -Path $LogsDir | Out-Null
        Write-Host "Created logs directory: $LogsDir"
    }
    
    # Generate log filename with timestamp
    $Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $LogFile = Join-Path $LogsDir "weekly_run_$Timestamp.log"
    
    Write-Host "Log file: $LogFile"
    Write-Host ""
    
    # Determine Python executable
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        $PythonExe = $VenvPython
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Using virtual environment Python: $PythonExe" | Tee-Object -FilePath $LogFile -Append
    } else {
        $PythonExe = "python"
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] No .venv found, using system Python" | Tee-Object -FilePath $LogFile -Append
    }
    
    Write-Host "" | Tee-Object -FilePath $LogFile -Append
    
    # Function to run command and check exit code
    function Run-PipelineStep {
        param(
            [string]$Module,
            [string[]]$Arguments,
            [string]$Description
        )
        
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Description" | Tee-Object -FilePath $LogFile -Append
        $FullCmd = "$PythonExe -m $Module $($Arguments -join ' ')"
        Write-Host "Command: $FullCmd" | Tee-Object -FilePath $LogFile -Append
        
        # Run command and capture output
        $ErrorActionPreference = "Continue"
        & $PythonExe -m $Module @Arguments 2>&1 | Tee-Object -FilePath $LogFile -Append
        $ExitCode = $LASTEXITCODE
        
        if ($ExitCode -ne 0 -and $ExitCode -ne $null) {
            Write-Host "ERROR: $Description failed with exit code $ExitCode" | Tee-Object -FilePath $LogFile -Append
            throw "Pipeline step failed: $Description"
        }
        
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Description completed successfully" | Tee-Object -FilePath $LogFile -Append
        Write-Host "" | Tee-Object -FilePath $LogFile -Append
    }
    
    # Run pipeline steps in order
    try {
        # Step 1: Ingest
        Run-PipelineStep `
            -Module "src.ingest.run_ingest" `
            -Arguments @("--root", $RepoRoot, "--log-level", "INFO") `
            -Description "STEP 1: Ingest (download raw data)"
        
        # Step 2: Normalize
        Run-PipelineStep `
            -Module "src.normalize.run_normalize" `
            -Arguments @("--root", $RepoRoot, "--log-level", "INFO") `
            -Description "STEP 2: Normalize (parse and QA)"
        
        # Step 3: Registry
        Run-PipelineStep `
            -Module "src.registry.run_registry" `
            -Arguments @("--root", $RepoRoot, "--log-level", "INFO") `
            -Description "STEP 3: Registry (build contracts registry)"
        
        # Step 4: ML Backup (all-assets)
        Run-PipelineStep `
            -Module "src.normalize.run_ml_backup" `
            -Arguments @("--root", $RepoRoot, "--all-assets", "--log-level", "INFO") `
            -Description "STEP 4: ML Backup (all-assets dataset)"
        
        # Success
        Write-Host "================================================" | Tee-Object -FilePath $LogFile -Append
        Write-Host "DONE" | Tee-Object -FilePath $LogFile -Append
        Write-Host "Completed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $LogFile -Append
        Write-Host "Log file: $LogFile" | Tee-Object -FilePath $LogFile -Append
        Write-Host "================================================" | Tee-Object -FilePath $LogFile -Append
        
        Write-Host ""
        Write-Host "================================================"
        Write-Host "DONE"
        Write-Host "Completed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        Write-Host "Log file: $LogFile"
        Write-Host "================================================"
        
        exit 0
    }
    catch {
        Write-Host "================================================" | Tee-Object -FilePath $LogFile -Append
        Write-Host "FAILED" | Tee-Object -FilePath $LogFile -Append
        Write-Host "Error: $_" | Tee-Object -FilePath $LogFile -Append
        Write-Host "Failed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $LogFile -Append
        Write-Host "Log file: $LogFile" | Tee-Object -FilePath $LogFile -Append
        Write-Host "================================================" | Tee-Object -FilePath $LogFile -Append
        
        Write-Host ""
        Write-Host "================================================"
        Write-Host "FAILED"
        Write-Host "Error: $_"
        Write-Host "Failed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        Write-Host "Log file: $LogFile"
        Write-Host "================================================"
        
        exit 1
    }
}
finally {
    Pop-Location
}

