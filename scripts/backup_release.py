#!/usr/bin/env python3
"""
Backup script for COT-MVP releases.
Creates a zip archive with code and optionally data files.
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path

def create_backup(version: str = "v0.2", include_data: bool = False):
    """
    Create a backup zip archive.
    
    Args:
        version: Version tag (e.g., "v0.2")
        include_data: If True, include metrics_weekly.parquet and canonical parquet
    """
    # Get project root
    root = Path(__file__).parent.parent.resolve()
    
    # Create backups directory
    backups_dir = root / "backups"
    backups_dir.mkdir(exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    zip_name = f"cot-mvp_{version}_{timestamp}.zip"
    zip_path = backups_dir / zip_name
    
    # Files/folders to include
    include_patterns = [
        "src/",
        "configs/",
        "README.md",
        "RELEASES.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        ".gitignore",
    ]
    
    # Optional data files
    if include_data:
        data_files = [
            "data/compute/metrics_weekly.parquet",
            "data/canonical/cot_weekly_canonical_full.parquet",
        ]
        for data_file in data_files:
            if (root / data_file).exists():
                include_patterns.append(data_file)
    
    # Exclude patterns
    exclude_patterns = [
        ".venv/",
        "__pycache__/",
        ".git/",
        "data/raw/",
        "data/tmp/",
        "*.pyc",
        ".pytest_cache/",
        ".mypy_cache/",
    ]
    
    def should_exclude(path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        for pattern in exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    # Create zip archive
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pattern in include_patterns:
            source = root / pattern
            if not source.exists():
                continue
            
            if source.is_file():
                # Add single file
                if not should_exclude(source):
                    zipf.write(source, source.relative_to(root))
            elif source.is_dir():
                # Add directory recursively
                for file_path in source.rglob("*"):
                    if file_path.is_file() and not should_exclude(file_path):
                        arcname = file_path.relative_to(root)
                        zipf.write(file_path, arcname)
    
    # Print result
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Backup created: {zip_path}")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"  Version: {version}")
    print(f"  Timestamp: {timestamp}")
    
    return zip_path

if __name__ == "__main__":
    import sys
    version = sys.argv[1] if len(sys.argv) > 1 else "v0.2"
    include_data = "--with-data" in sys.argv
    create_backup(version=version, include_data=include_data)

