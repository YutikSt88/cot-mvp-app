#!/usr/bin/env python3
"""
Build deploy package for Streamlit Cloud.
Creates deploy/streamlit_app/ with necessary files for deployment.
"""

import os
import shutil
from pathlib import Path

def build_deploy_package():
    """Build deploy package in deploy/streamlit_app/"""
    # Get project root
    root = Path(__file__).parent.parent.resolve()
    
    # Deploy directory
    deploy_dir = root / "deploy" / "streamlit_app"
    
    # Remove existing deploy directory if exists
    if deploy_dir.exists():
        print(f"Removing existing deploy directory: {deploy_dir}")
        shutil.rmtree(deploy_dir)
    
    # Create deploy directory structure
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / "src").mkdir(exist_ok=True)
    (deploy_dir / "configs").mkdir(exist_ok=True)
    (deploy_dir / "data" / "compute").mkdir(parents=True, exist_ok=True)
    
    print(f"Building deploy package in: {deploy_dir}")
    
    # Copy src/ (only app, common, and compute - NOT ingest/normalize/registry)
    src_source = root / "src"
    src_dest = deploy_dir / "src"
    if not src_source.exists():
        print(f"  [ERROR] src/ not found")
        return False
    
    # Create src directory structure
    src_dest.mkdir(exist_ok=True)
    
    # Copy src/__init__.py first
    src_init_source = root / "src" / "__init__.py"
    src_init_dest = deploy_dir / "src" / "__init__.py"
    if src_init_source.exists():
        shutil.copy2(src_init_source, src_init_dest)
        print(f"  [OK] Copied src/__init__.py")
    else:
        print(f"  [ERROR] src/__init__.py not found")
        return False
    
    # Copy only required subdirectories
    required_src_dirs = ["app", "common", "compute"]
    for subdir in required_src_dirs:
        source_dir = src_source / subdir
        dest_dir = src_dest / subdir
        if source_dir.exists():
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
            print(f"  [OK] Copied src/{subdir}/")
        else:
            print(f"  [ERROR] src/{subdir}/ not found")
            return False
    
    print(f"  [OK] Copied src/ (app, common, compute only)")
    
    # Copy configs/ (entire directory)
    configs_source = root / "configs"
    configs_dest = deploy_dir / "configs"
    if configs_source.exists():
        shutil.copytree(configs_source, configs_dest, dirs_exist_ok=True)
        print(f"  [OK] Copied configs/")
    else:
        print(f"  [ERROR] configs/ not found")
        return False
    
    # Copy metrics_weekly.parquet
    metrics_source = root / "data" / "compute" / "metrics_weekly.parquet"
    metrics_dest = deploy_dir / "data" / "compute" / "metrics_weekly.parquet"
    if metrics_source.exists():
        shutil.copy2(metrics_source, metrics_dest)
        metrics_size_mb = metrics_source.stat().st_size / (1024 * 1024)
        print(f"  [OK] Copied metrics_weekly.parquet ({metrics_size_mb:.2f} MB)")
    else:
        print(f"  [WARNING] metrics_weekly.parquet not found")
    
    # Create deploy-friendly README.md (minimal)
    readme_dest = deploy_dir / "README.md"
    readme_content = """# COT-MVP Streamlit App

Deployed from [cot-mvp](https://github.com/YutikSt88/cot-mvp) repository.

## Streamlit Cloud Deployment

- **Main file:** `app.py`
- **Repository:** YutikSt88/cot-mvp-app
- **App URL:** cot-app.streamlit.app

## Data Source

Metrics computed from CFTC Commitment of Traders (COT) reports.

See main repository for full pipeline documentation.
"""
    readme_dest.write_text(readme_content)
    print(f"  [OK] Created deploy-friendly README.md")
    
    # Copy requirements.txt
    requirements_source = root / "requirements.txt"
    requirements_dest = deploy_dir / "requirements.txt"
    if requirements_source.exists():
        shutil.copy2(requirements_source, requirements_dest)
        print(f"  [OK] Copied requirements.txt")
    else:
        print(f"  [ERROR] requirements.txt not found")
        return False
    
    # Copy app.py (root entrypoint) - REQUIRED
    app_py_source = root / "app.py"
    app_py_dest = deploy_dir / "app.py"
    if app_py_source.exists():
        shutil.copy2(app_py_source, app_py_dest)
        print(f"  [OK] Copied app.py (root entrypoint)")
    else:
        print(f"  [ERROR] app.py not found (required for Streamlit Cloud)")
        return False
    
    # Copy src/__init__.py (package marker) - REQUIRED
    src_init_source = root / "src" / "__init__.py"
    src_init_dest = deploy_dir / "src" / "__init__.py"
    if src_init_source.exists():
        # Ensure src/ directory exists in deploy
        (deploy_dir / "src").mkdir(exist_ok=True)
        shutil.copy2(src_init_source, src_init_dest)
        print(f"  [OK] Copied src/__init__.py (package marker)")
    else:
        print(f"  [ERROR] src/__init__.py not found (required for imports)")
        return False
    
    # Copy .streamlit/ (if exists)
    streamlit_source = root / ".streamlit"
    streamlit_dest = deploy_dir / ".streamlit"
    if streamlit_source.exists():
        shutil.copytree(streamlit_source, streamlit_dest, dirs_exist_ok=True)
        print(f"  [OK] Copied .streamlit/")
    else:
        print(f"  [INFO] .streamlit/ not found (optional)")
    
    # Clean up excluded files/directories
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        ".venv",
        ".git",
        "backups",
        "data/raw",
        "data/tmp",
        "*.zip",
    ]
    
    # Forbidden directories that should not exist in deploy package
    forbidden_dirs = [
        "src/ingest",
        "src/normalize",
        "src/registry",
        "docs",
        "scripts",
    ]
    
    def should_exclude(path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        for pattern in exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    # Remove excluded files/directories
    for item in deploy_dir.rglob("*"):
        if should_exclude(item):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
    
    # Remove forbidden directories if they exist
    for forbidden in forbidden_dirs:
        forbidden_path = deploy_dir / forbidden
        if forbidden_path.exists():
            print(f"  [WARNING] Removing forbidden directory: {forbidden}")
            shutil.rmtree(forbidden_path, ignore_errors=True)
    
    # Remove all __pycache__ directories
    for pycache_dir in deploy_dir.rglob("__pycache__"):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir, ignore_errors=True)
    
    # Calculate sizes
    total_size = sum(f.stat().st_size for f in deploy_dir.rglob("*") if f.is_file())
    total_size_mb = total_size / (1024 * 1024)
    
    metrics_size_mb = 0
    if metrics_dest.exists():
        metrics_size_mb = metrics_dest.stat().st_size / (1024 * 1024)
    
    # Print summary
    print("\n" + "="*60)
    print("Deploy package built successfully!")
    print("="*60)
    print(f"Deploy directory: {deploy_dir}")
    print(f"Total size: {total_size_mb:.2f} MB")
    print(f"metrics_weekly.parquet: {metrics_size_mb:.2f} MB")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = build_deploy_package()
    exit(0 if success else 1)
