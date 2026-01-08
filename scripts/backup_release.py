#!/usr/bin/env python3
"""
Backup script for COT-MVP releases.
Creates a zip archive with code, configs, docs, and scripts.
Follows canonical naming: cot-mvp_v<SEMVER>_<YYYYMMDD_HHMM>.zip
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path

def create_backup(version: str = "v1.1.6"):
    """
    Create a backup zip archive following canonical naming standard.
    
    Args:
        version: Version tag in SEMVER format (e.g., "v1.1.6")
    
    Returns:
        Path to created zip file
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
        "docs/",
        "scripts/",
        "README.md",
        "RELEASES.md",
        "requirements.txt",
        ".gitignore",
        "app.py",  # Root entrypoint
    ]
    
    # Exclude patterns
    exclude_patterns = [
        ".venv/",
        "__pycache__/",
        ".git/",
        "data/raw/",
        "data/canonical/",
        "data/tmp/",
        "deploy_repo/",
        "deploy/",
        "backups/",
        "*.pyc",
        ".pytest_cache/",
        ".mypy_cache/",
    ]
    
    def should_exclude(path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path).replace('\\', '/')  # Normalize path separators
        # Check for __pycache__ directories
        if '__pycache__' in path.parts:
            return True
        # Check other exclude patterns
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
    
    # Create/update LATEST.txt
    latest_file = backups_dir / "LATEST.txt"
    with open(latest_file, 'w', encoding='utf-8') as f:
        f.write(f"LATEST RELEASE:\n")
        f.write(f"{version}\n")
        f.write(f"FILE:\n")
        f.write(f"{zip_name}\n")
    
    # Print result
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Backup created: {zip_path.name}")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"  Version: {version}")
    print(f"  Timestamp: {timestamp}")
    print(f"  LATEST.txt updated")
    
    return zip_path

if __name__ == "__main__":
    import sys
    version = sys.argv[1] if len(sys.argv) > 1 else "v1.1.6"
    create_backup(version=version)
