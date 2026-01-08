# Deploy to Streamlit Cloud

This document describes how to deploy COT-MVP to Streamlit Cloud.

## Overview

The deployment process involves:
1. Building a deploy package locally
2. Pushing it to a separate GitHub repository (`YutikSt88/cot-mvp-app`)
3. Connecting Streamlit Cloud to that repository

## Prerequisites

- Python 3.11+ installed
- Git installed
- GitHub account (YutikSt88)
- Streamlit Cloud account (free tier available)
- **GitHub repository created**: `YutikSt88/cot-mvp-app` (empty, public, no README)

## First Deploy (Bootstrap)

### Step 1: Build Deploy Package

Build the deploy package locally:

```bash
python scripts/build_deploy_package.py
```

This creates `deploy/streamlit_app/` with:
- `src/` - All source code
- `configs/` - Configuration files
- `data/compute/metrics_weekly.parquet` - Metrics data
- `.streamlit/config.toml` - Streamlit configuration
- `README.md` - Documentation
- `requirements.txt` - Dependencies

### Step 2: Smoke Test

Verify the deploy package:

```bash
python scripts/smoke_test_deploy.py
```

Expected output:
- `[OK] src/app/app.py exists`
- `[OK] data/compute/metrics_weekly.parquet exists`
- `[OK] Required columns present`
- `[OK] metrics_weekly.parquet has X rows`

### Step 3: Deploy to GitHub

Use the automated deploy script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_to_github.ps1
```

This script:
- Builds deploy package
- Runs smoke test
- Creates/updates `deploy_repo/` directory (in project root)
- Initializes git repository (if needed)
- Sets remote to `https://github.com/YutikSt88/cot-mvp-app.git`
- Hard-syncs deploy package (copies all files including `app.py`)
- Commits and pushes to GitHub

**Manual alternative** (if script fails):

```powershell
# Create deploy repo directory
mkdir deploy_repo
cd deploy_repo
git init
git branch -M main
git remote add origin https://github.com/YutikSt88/cot-mvp-app.git

# Copy deploy package
Copy-Item -Path ..\deploy\streamlit_app\* -Destination . -Recurse -Force

# Commit and push
git add -A
git commit -m "Initial deploy package"
git push -u origin main
```

### Step 4: Connect Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub account (if not already connected)
4. Fill in the form with **exact** values:
   - **Repository**: `YutikSt88/cot-mvp-app`
   - **Branch**: `main`
   - **Main file**: `app.py` (must be at repo root, not `src/app/app.py`)
   - **App URL**: `cot-mvp-app` (or your preferred name)
5. Click "Deploy!"

Streamlit Cloud will:
- Install dependencies from `requirements.txt`
- Run the app from `app.py` (root entrypoint)
- Auto-redeploy on every push to `main` branch

## Weekly Update Flow

After running the compute pipeline locally:

1. **Run compute pipeline** (if needed):
   ```bash
   python -m src.compute.run_compute --root . --log-level INFO
   ```

2. **Deploy to GitHub (one command):**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/deploy_to_github.ps1
   ```

   This script automatically:
   - Builds deploy package
   - Runs smoke test
   - Hard-syncs to `deploy_repo/`
   - Commits and pushes to GitHub

3. **Streamlit Cloud auto-redeploys** when it detects the push.

### Alternative: Manual Update

If you prefer manual steps:

```powershell
# Build and test
python scripts/build_deploy_package.py
python scripts/smoke_test_deploy.py

# Update deploy repo manually
cd deploy_repo
Copy-Item -Path ..\deploy\streamlit_app\* -Destination . -Recurse -Force
git add -A
git commit -m "Update deploy $(Get-Date -Format 'yyyy-MM-dd')"
git push
```

## Troubleshooting

### "Module not found" errors

**Problem**: `ModuleNotFoundError: No module named 'pyarrow'`

**Solution**: Ensure `requirements.txt` includes:
- `streamlit>=1.28.0`
- `pandas>=2.2`
- `pyarrow>=16.0` (required for parquet support)
- `pyyaml>=6.0`
- All other dependencies from main project

**Check**: Verify `deploy/streamlit_app/requirements.txt` has all dependencies.

### Parquet read error

**Problem**: `ArrowInvalid: Not a Parquet file` or similar

**Solution**:
1. Verify `data/compute/metrics_weekly.parquet` exists in deploy package:
   ```powershell
   Test-Path deploy\streamlit_app\data\compute\metrics_weekly.parquet
   ```
2. Rebuild deploy package if file is missing or corrupted
3. Check file size (should be ~6 MB)

### Module import path errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: 
- Ensure `app.py` (root entrypoint) is in deploy package root
- Verify `app.py` is set as main file path in Streamlit Cloud settings (not `src/app/app.py`)
- The root `app.py` automatically adds repo root to PYTHONPATH
- Ensure `src/__init__.py` exists (package marker)

### Large files / repo size

**Problem**: GitHub push fails due to file size limits

**Solution**:
- `metrics_weekly.parquet` is ~6 MB (within limits)
- If repo grows too large, consider Git LFS or data compression
- Check `.gitignore` excludes unnecessary files

### "App crashed" basics

**Problem**: Streamlit Cloud shows "App crashed"

**Solution**:
1. Check deployment logs in Streamlit Cloud dashboard
2. Verify `src/app/app.py` exists and is the correct entry point
3. Ensure `requirements.txt` is in the root of the deploy repository
4. Check that all paths in code are relative (not absolute)
5. Verify `.streamlit/config.toml` exists (optional but recommended)
6. Check for missing environment variables (if any are used)

## File Structure

The deploy package structure:

```
deploy/streamlit_app/
├── app.py                  # Root entrypoint (for Streamlit Cloud)
├── src/
│   ├── __init__.py         # Package marker
│   ├── app/
│   │   └── app.py          # Actual Streamlit app
│   ├── common/
│   ├── compute/
│   └── ...
├── configs/
│   ├── markets.yaml
│   └── contracts_meta.yaml
├── data/
│   └── compute/
│       └── metrics_weekly.parquet
├── .streamlit/
│   └── config.toml         # Streamlit configuration
├── README.md
└── requirements.txt
```

## Notes

- The deploy package does NOT include:
  - `.venv/` - Virtual environment
  - `data/raw/` - Raw data snapshots
  - `backups/` - Backup files
  - `.git/` - Git repository
  - `__pycache__/` - Python cache

- Streamlit Cloud automatically installs dependencies from `requirements.txt`
- The app runs on Streamlit's servers (no local server needed)
- Free tier has resource limits (check Streamlit Cloud docs)
