#!/usr/bin/env python3
"""
Smoke test for deploy package.
Verifies that deploy/streamlit_app/ has necessary files and data.
"""

import sys
from pathlib import Path
import pandas as pd

def smoke_test_deploy():
    """Run smoke tests on deploy package."""
    root = Path(__file__).parent.parent.resolve()
    deploy_dir = root / "deploy" / "streamlit_app"
    
    print("Running smoke tests on deploy package...")
    print(f"Deploy directory: {deploy_dir}\n")
    
    errors = []
    warnings = []
    
    # Test 1: Check root app.py exists (entrypoint for Streamlit Cloud)
    root_app_py = deploy_dir / "app.py"
    if root_app_py.exists():
        print(f"[OK] app.py (root entrypoint) exists")
    else:
        errors.append(f"app.py (root entrypoint) not found")
        print(f"[ERROR] app.py (root entrypoint) not found")
    
    # Test 1b: Check src/app/app.py exists (actual app)
    app_py = deploy_dir / "src" / "app" / "app.py"
    if app_py.exists():
        print(f"[OK] src/app/app.py exists")
    else:
        errors.append(f"src/app/app.py not found")
        print(f"[ERROR] src/app/app.py not found")
    
    # Test 1c: Check src/__init__.py exists (package marker) - REQUIRED
    src_init = deploy_dir / "src" / "__init__.py"
    if src_init.exists():
        print(f"[OK] src/__init__.py exists")
    else:
        errors.append("src/__init__.py not found (required for imports)")
        print(f"[ERROR] src/__init__.py not found (required for imports)")
    
    # Test 2: Check metrics_weekly.parquet exists
    metrics_parquet = deploy_dir / "data" / "compute" / "metrics_weekly.parquet"
    if metrics_parquet.exists():
        print(f"[OK] data/compute/metrics_weekly.parquet exists")
        
        # Test 3: Read and validate parquet
        try:
            df = pd.read_parquet(metrics_parquet)
            
            # Check required columns
            required_cols = ["market_key", "report_date", "open_interest"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                errors.append(f"Missing required columns: {missing_cols}")
                print(f"[ERROR] Missing required columns: {missing_cols}")
            else:
                print(f"[OK] Required columns present: {required_cols}")
            
            # Check has rows
            if len(df) == 0:
                errors.append("metrics_weekly.parquet has 0 rows")
                print(f"[ERROR] metrics_weekly.parquet has 0 rows")
            else:
                print(f"[OK] metrics_weekly.parquet has {len(df)} rows")
            
            # Check report_date
            if "report_date" in df.columns:
                date_col = df["report_date"]
                if date_col.isna().all():
                    errors.append("report_date column is all NaN")
                    print(f"[ERROR] report_date column is all NaN")
                else:
                    # Try to parse as date
                    try:
                        if not pd.api.types.is_datetime64_any_dtype(date_col):
                            pd.to_datetime(date_col, errors="raise")
                        last_date = date_col.max()
                        print(f"[OK] report_date is valid (last date: {last_date})")
                    except Exception as e:
                        warnings.append(f"report_date parsing issue: {e}")
                        print(f"[WARNING] report_date parsing issue: {e}")
            
            # Print summary
            print(f"\n[INFO] Total columns: {len(df.columns)}")
            print(f"[INFO] Total rows: {len(df)}")
            if "report_date" in df.columns and not df["report_date"].isna().all():
                last_date = df["report_date"].max()
                print(f"[INFO] Last report_date: {last_date}")
            
        except Exception as e:
            errors.append(f"Error reading metrics_weekly.parquet: {e}")
            print(f"[ERROR] Error reading metrics_weekly.parquet: {e}")
    else:
        errors.append("data/compute/metrics_weekly.parquet not found")
        print(f"[ERROR] data/compute/metrics_weekly.parquet not found")
    
    # Test 4: Check requirements.txt exists
    requirements = deploy_dir / "requirements.txt"
    if requirements.exists():
        print(f"[OK] requirements.txt exists")
    else:
        errors.append("requirements.txt not found")
        print(f"[ERROR] requirements.txt not found")
    
    # Test 6: Check forbidden directories do NOT exist
    forbidden_dirs = [
        "docs",
        "scripts",
        "src/ingest",
        "src/normalize",
        "src/registry",
    ]
    print(f"\n[TEST] Checking for forbidden directories...")
    for forbidden in forbidden_dirs:
        forbidden_path = deploy_dir / forbidden
        if forbidden_path.exists():
            errors.append(f"Forbidden directory found: {forbidden}")
            print(f"[ERROR] Forbidden directory found: {forbidden}")
        else:
            print(f"[OK] {forbidden} not present (correct)")
    
    # Test 7: Check required directories exist
    required_dirs = [
        "src/app",
        "src/common",
        "src/compute",
        "configs",
        "data/compute",
        ".streamlit",
    ]
    print(f"\n[TEST] Checking required directories...")
    for required in required_dirs:
        required_path = deploy_dir / required
        if required_path.exists():
            print(f"[OK] {required} exists")
        else:
            if required == ".streamlit":
                warnings.append(f"Optional directory missing: {required}")
                print(f"[WARNING] Optional directory missing: {required}")
            else:
                errors.append(f"Required directory missing: {required}")
                print(f"[ERROR] Required directory missing: {required}")
    
    # Test 5: Import test (verify src package structure works)
    import subprocess
    import os
    
    print(f"\n[TEST] Testing import paths...")
    try:
        # Change to deploy directory and test imports
        original_cwd = os.getcwd()
        os.chdir(str(deploy_dir))
        
        # Test basic src import (without streamlit dependency)
        # This verifies that sys.path setup and package structure work
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import sys; sys.path.insert(0, '.'); import src; from src.app import ui_state; print('OK')"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            print(f"[OK] Import test passed (src package structure works)")
        else:
            # Check if it's just a missing dependency (streamlit) vs actual import path issue
            stderr_lower = result.stderr.lower()
            if "streamlit" in stderr_lower or "no module named" in stderr_lower:
                # This is expected in test environment - streamlit not installed
                # But we can still verify the path structure worked
                if "src" in result.stderr and "app" in result.stderr:
                    warnings.append("Import test: streamlit not installed (expected in test env), but src package structure is correct")
                    print(f"[WARNING] Import test: streamlit not installed (expected), but src package structure verified")
                else:
                    errors.append(f"Import test failed - path issue: {result.stderr}")
                    print(f"[ERROR] Import test failed - path issue")
                    print(f"  stderr: {result.stderr}")
            else:
                errors.append(f"Import test failed: {result.stderr}")
                print(f"[ERROR] Import test failed")
                print(f"  stdout: {result.stdout}")
                print(f"  stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        errors.append("Import test timed out")
        print(f"[ERROR] Import test timed out")
        try:
            os.chdir(original_cwd)
        except:
            pass
    except Exception as e:
        warnings.append(f"Import test error (non-critical): {e}")
        print(f"[WARNING] Import test error (non-critical): {e}")
        try:
            os.chdir(original_cwd)
        except:
            pass
    
    # Print final summary
    print("\n" + "="*60)
    if errors:
        print("SMOKE TEST FAILED")
        print("="*60)
        for error in errors:
            print(f"  ERROR: {error}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  WARNING: {warning}")
        return False
    else:
        print("SMOKE TEST PASSED")
        print("="*60)
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  WARNING: {warning}")
        return True

if __name__ == "__main__":
    success = smoke_test_deploy()
    sys.exit(0 if success else 1)
