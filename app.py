"""
Root entrypoint for Streamlit Cloud deployment.

This file ensures the repository root is on PYTHONPATH so that
imports like `from src.app.ui_state import ...` work correctly.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Ensure repo root is on PYTHONPATH so `import src...` works on Streamlit Cloud
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Run the actual Streamlit app
runpy.run_path(str(REPO_ROOT / "src" / "app" / "app.py"), run_name="__main__")
