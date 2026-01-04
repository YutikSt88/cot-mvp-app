# Project Backup Script
# Creates a zip archive of the repository excluding .git, .venv, data/, reports/, backups/

param(
    [string]$Tag = "v1.1.2",
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
        Write-Host "Created backups directory: $BackupsDir"
    }
    
    # Generate timestamp
    $Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    
    # Archive name
    $ArchiveName = "cot-mvp_${Tag}_${Timestamp}.zip"
    $ArchivePath = Join-Path $BackupsDir $ArchiveName
    
    Write-Host "Creating backup archive..."
    Write-Host "Root: $RepoRoot"
    Write-Host "Archive: $ArchivePath"
    Write-Host ""
    
    # Files and directories to exclude
    $ExcludePatterns = @(
        ".git",
        ".venv",
        "data",
        "reports",
        "backups",
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "Thumbs.db"
    )
    
    # Get all items to archive
    $ItemsToArchive = Get-ChildItem -Path $RepoRoot -Force | Where-Object {
        $item = $_
        $shouldExclude = $false
        foreach ($pattern in $ExcludePatterns) {
            if ($item.Name -eq $pattern -or $item.Name -like $pattern) {
                $shouldExclude = $true
                break
            }
        }
        -not $shouldExclude
    }
    
    if (-not $ItemsToArchive) {
        Write-Host "ERROR: No items to archive" -ForegroundColor Red
        exit 1
    }
    
    # Create temporary directory for items to archive
    $TempDir = Join-Path $env:TEMP "cot_mvp_backup_$([System.Guid]::NewGuid().ToString())"
    New-Item -ItemType Directory -Path $TempDir | Out-Null
    
    try {
        # Copy items to temp directory
        foreach ($item in $ItemsToArchive) {
            $destPath = Join-Path $TempDir $item.Name
            Copy-Item -Path $item.FullName -Destination $destPath -Recurse -Force
        }
        
        # Create zip archive
        Compress-Archive -Path "$TempDir\*" -DestinationPath $ArchivePath -Force
        
        Write-Host "Backup created successfully: $ArchivePath" -ForegroundColor Green
        Write-Host "Size: $([math]::Round((Get-Item $ArchivePath).Length / 1MB, 2)) MB"
        
    } finally {
        # Cleanup temp directory
        if (Test-Path $TempDir) {
            Remove-Item -Path $TempDir -Recurse -Force
        }
    }
    
} finally {
    Pop-Location
}

