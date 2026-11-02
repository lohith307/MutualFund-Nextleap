"""
streamlit_app.py — Root Entrypoint for Streamlit Community Cloud

Ensures the repository root is properly added to sys.path and executes
the Groww Mutual Fund FAQ Assistant UI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Launch main application
from src.ui.app import *  # noqa: F401, F403

