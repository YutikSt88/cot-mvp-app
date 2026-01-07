# Project Backup Script
# Creates a timestamped folder backup and zip archive of the repository
# Excludes: .venv/, __pycache__/, .git/, data/raw/**, optionally data/canonical/**

param(
    [string]$Root = $null
)

# Determine repo root
if ($Root) {
    $RepoRoot = (Resolve-Path $Root).Path
} else {
    # If script is in scripts/, repo root is parent
    $ScriptPath = Split-Path $MyInvocation.MyCommand.Path
    $RepoRoot = Split-Path $ScriptPath -Parent
}

Push-Location $RepoRoot

try {
    # Create backups directory if it doesn't exist
    $BackupsDir = Join-Path $RepoRoot "backups"
    if (-not (Test-Path $BackupsDir)) {
        New-Item -ItemType Directory -Path $BackupsDir | Out-Null
        Write-Host "Created backups directory: $BackupsDir" -ForegroundColor Cyan
    }
    
    # Generate timestamp
    $Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    
    # Backup folder name
    $BackupFolderName = "backup_${Timestamp}"
    $BackupFolderPath = Join-Path $BackupsDir $BackupFolderName
    
    # Archive name
    $ArchiveName = "${BackupFolderName}.zip"
    $ArchivePath = Join-Path $BackupsDir $ArchiveName
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Project Backup Script" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Root: $RepoRoot" -ForegroundColor Gray
    Write-Host "Backup Folder: $BackupFolderPath" -ForegroundColor Gray
    Write-Host "Archive: $ArchivePath" -ForegroundColor Gray
    Write-Host ""
    
    # Create backup folder
    if (Test-Path $BackupFolderPath) {
        Write-Host "WARNING: Backup folder already exists, removing..." -ForegroundColor Yellow
        Remove-Item -Path $BackupFolderPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $BackupFolderPath | Out-Null
    Write-Host "Created backup folder: $BackupFolderPath" -ForegroundColor Green
    
    # Define what to include/exclude
    $ItemsToCopy = @()
    $ItemsExcluded = @()
    $TotalSize = 0
    
    # Get all items in repo root
    $AllItems = Get-ChildItem -Path $RepoRoot -Force
    
    foreach ($item in $AllItems) {
        $shouldExclude = $false
        $excludeReason = ""
        
        # Exclude patterns
        if ($item.Name -eq ".git") {
            $shouldExclude = $true
            $excludeReason = ".git/"
        }
        elseif ($item.Name -eq ".venv") {
            $shouldExclude = $true
            $excludeReason = ".venv/"
        }
        elseif ($item.Name -eq "backups") {
            $shouldExclude = $true
            $excludeReason = "backups/"
        }
        elseif ($item.Name -eq "__pycache__") {
            $shouldExclude = $true
            $excludeReason = "__pycache__/"
        }
        elseif ($item.Name -eq "data") {
            # Special handling for data/ folder
            # We want to include:
            # - data/compute/metrics_weekly.parquet
            # - data/canonical/** (prefer include, but can be large)
            # We want to exclude:
            # - data/raw/**
            
            $DataDestPath = Join-Path $BackupFolderPath "data"
            New-Item -ItemType Directory -Path $DataDestPath | Out-Null
            
            # Copy data/compute/metrics_weekly.parquet
            $ComputePath = Join-Path $item.FullName "compute"
            if (Test-Path $ComputePath) {
                $ComputeDestPath = Join-Path $DataDestPath "compute"
                New-Item -ItemType Directory -Path $ComputeDestPath | Out-Null
                $MetricsFile = Join-Path $ComputePath "metrics_weekly.parquet"
                if (Test-Path $MetricsFile) {
                    Copy-Item -Path $MetricsFile -Destination $ComputeDestPath -Force
                    $fileSize = (Get-Item $MetricsFile).Length
                    $TotalSize += $fileSize
                    Write-Host "  Included: data/compute/metrics_weekly.parquet" -ForegroundColor Gray
                }
            }
            
            # Copy data/canonical/** (include canonical data)
            $CanonicalPath = Join-Path $item.FullName "canonical"
            if (Test-Path $CanonicalPath) {
                $CanonicalDestPath = Join-Path $DataDestPath "canonical"
                Copy-Item -Path $CanonicalPath -Destination $CanonicalDestPath -Recurse -Force
                $dirSize = (Get-ChildItem -Path $CanonicalPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
                $TotalSize += $dirSize
                Write-Host "  Included: data/canonical/** ($([math]::Round($dirSize / 1MB, 2)) MB)" -ForegroundColor Gray
            }
            
            # Copy other data subdirectories (indicators, ml, registry) but exclude raw
            $DataSubdirs = Get-ChildItem -Path $item.FullName -Directory | Where-Object { $_.Name -ne "raw" }
            foreach ($subdir in $DataSubdirs) {
                if ($subdir.Name -ne "compute" -and $subdir.Name -ne "canonical") {
                    $SubdirDestPath = Join-Path $DataDestPath $subdir.Name
                    Copy-Item -Path $subdir.FullName -Destination $SubdirDestPath -Recurse -Force
                    $dirSize = (Get-ChildItem -Path $subdir.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
                    $TotalSize += $dirSize
                    Write-Host "  Included: data/$($subdir.Name)/**" -ForegroundColor Gray
                }
            }
            
            # Exclude data/raw/**
            $ItemsExcluded += "data/raw/** (too large)"
            $shouldExclude = $false  # We already handled data/ manually
        }
        else {
            # Include this item
            $ItemsToCopy += $item
        }
        
        if ($shouldExclude) {
            $ItemsExcluded += $excludeReason
        }
    }
    
    # Copy included items
    Write-Host ""
    Write-Host "Copying files and directories..." -ForegroundColor Cyan
    foreach ($item in $ItemsToCopy) {
        $destPath = Join-Path $BackupFolderPath $item.Name
        
        # Skip __pycache__ directories during copy
        if ($item.PSIsContainer) {
            # Copy directory, excluding __pycache__ and .pyc files
            $tempDest = Join-Path $env:TEMP "backup_temp_$([System.Guid]::NewGuid().ToString())"
            Copy-Item -Path $item.FullName -Destination $tempDest -Recurse -Force
            
            # Remove __pycache__ and .pyc files from temp copy
            Get-ChildItem -Path $tempDest -Recurse -Directory | Where-Object { $_.Name -eq "__pycache__" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Get-ChildItem -Path $tempDest -Recurse -File | Where-Object { $_.Extension -eq ".pyc" } | Remove-Item -Force -ErrorAction SilentlyContinue
            
            # Copy to final destination (remove if exists first)
            if (Test-Path $destPath) {
                Remove-Item -Path $destPath -Recurse -Force
            }
            Move-Item -Path $tempDest -Destination $destPath -Force
            
            $dirSize = (Get-ChildItem -Path $item.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            $TotalSize += $dirSize
        } else {
            Copy-Item -Path $item.FullName -Destination $destPath -Force
            $fileSize = (Get-Item $item.FullName).Length
            $TotalSize += $fileSize
        }
        
        Write-Host "  Copied: $($item.Name)" -ForegroundColor Gray
    }
    
    # Calculate total size of backup folder
    $BackupFolderSize = (Get-ChildItem -Path $BackupFolderPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
    
    Write-Host ""
    Write-Host "Creating zip archive..." -ForegroundColor Cyan
    Compress-Archive -Path "$BackupFolderPath\*" -DestinationPath $ArchivePath -Force
    $ArchiveSize = (Get-Item $ArchivePath).Length
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Backup Summary" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backup Folder:" -ForegroundColor Yellow
    Write-Host "  $BackupFolderPath" -ForegroundColor White
    Write-Host "  Size: $([math]::Round($BackupFolderSize / 1MB, 2)) MB" -ForegroundColor White
    Write-Host ""
    Write-Host "Zip Archive:" -ForegroundColor Yellow
    Write-Host "  $ArchivePath" -ForegroundColor White
    Write-Host "  Size: $([math]::Round($ArchiveSize / 1MB, 2)) MB" -ForegroundColor White
    Write-Host ""
    Write-Host "Included:" -ForegroundColor Yellow
    Write-Host "  ✓ configs/" -ForegroundColor Green
    Write-Host "  ✓ src/" -ForegroundColor Green
    Write-Host "  ✓ scripts/" -ForegroundColor Green
    Write-Host "  ✓ docs/" -ForegroundColor Green
    Write-Host "  ✓ README.md, RELEASES.md, requirements.txt" -ForegroundColor Green
    Write-Host "  ✓ data/compute/metrics_weekly.parquet" -ForegroundColor Green
    Write-Host "  ✓ data/canonical/**" -ForegroundColor Green
    Write-Host "  ✓ data/indicators/**, data/ml/**, data/registry/**" -ForegroundColor Green
    Write-Host ""
    Write-Host "Excluded:" -ForegroundColor Yellow
    foreach ($excluded in $ItemsExcluded) {
        Write-Host "  ✗ $excluded" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Backup completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Backup failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
