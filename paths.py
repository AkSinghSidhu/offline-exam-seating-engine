"""
Path utilities for the Exam Seating Planner.

Resolves data folder paths relative to the application's base directory.
Works both when running as a Python script and as a frozen PyInstaller exe.
"""
import sys
import os


def get_base_dir() -> str:
    """
    Get the application's base directory.
    
    - When running as a PyInstaller exe: the directory containing the exe
    - When running as a script: the project root directory
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running as script - use the directory containing this file
        return os.path.dirname(os.path.abspath(__file__))


def get_data_dir(subfolder: str = "") -> str:
    """Get a path inside the data/ directory, creating it if needed."""
    path = os.path.join(get_base_dir(), "data")
    if subfolder:
        path = os.path.join(path, subfolder)
    os.makedirs(path, exist_ok=True)
    return path


def get_rooms_dir() -> str:
    """Get the data/rooms/ directory path (auto-creates)."""
    return get_data_dir("rooms")


def get_students_dir() -> str:
    """Get the data/students/ directory path (auto-creates)."""
    return get_data_dir("students")


def get_output_dir() -> str:
    """Get the output/ directory path (auto-creates)."""
    path = os.path.join(get_base_dir(), "output")
    os.makedirs(path, exist_ok=True)
    return path


def ensure_data_folders():
    """Create all data folders on startup."""
    get_rooms_dir()
    get_students_dir()
    get_output_dir()
