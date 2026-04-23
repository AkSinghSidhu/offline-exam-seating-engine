"""Exam Seating Planner - Main Entry Point"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import ensure_data_folders
from gui.app import main

if __name__ == "__main__":
    # Create data folders on startup
    ensure_data_folders()
    main()
