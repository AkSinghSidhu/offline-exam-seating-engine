# Offline Exam Seating Engine

Offline Exam Seating Engine is a Python and PySide6-based desktop application designed to automate and optimize examination seating arrangements. It processes student rosters and room configurations to produce conflict-free, adjacency-safe seating plans alongside complete administrative exports (attendance sheets, invigilator envelope summaries, and room/class distribution lists).

## Key Features

- **Conflict-Free Seating Optimization**:
  - Multi-phase Pre-Plan & Fill algorithm with adjacency-safe gap packing to prevent students of the same subject or class from sitting adjacently.
  - Reserve room allocation support to handle overflow or emergency seating requirements.
  - Batch backfilling for leftover or irregularly sized student batches.
- **Comprehensive Document & Report Exports**:
  - **Excel Seating Plans & Distribution Sheets**: Detailed room-wise and class-wise seating layouts.
  - **2-Way Attendance Sheets**: Attendance sheets with seat coordinate and position tracking.
  - **Classwise Attendance Sheets**: Per-course attendance records for departments.
  - **Invigilator / Envelope Sheets (`.docx`)**: Room-wise examination summaries and question paper accounting.
- **Privacy & Offline First**:
  - Runs completely offline without cloud dependencies.
  - Input student/room datasets and generated outputs are kept strictly local (`data/` and `output/` are excluded from version control).
- **Modern Desktop GUI**: Built with PySide6 for an intuitive, responsive user experience with real-time feedback and progress tracking.

## Repository & Data Structure

```
├── core/                   # Seating algorithm and document exporters
├── gui/                    # PySide6 user interface panels and components
├── models/                 # Data models (Student, Room, Exam)
├── templates/              # Sample starter templates for students & rooms
├── data/                   # (Local / Git-ignored) Real input Excel files
│   ├── rooms/              # Place room details here
│   └── students/           # Place student rosters here
├── output/                 # (Local / Git-ignored) Generated plans and exports
├── generate_template.py    # Generates blank starter Excel templates
├── generate_test_data.py   # Generates synthetic mock datasets for testing
├── main.py                 # Application entry point
├── paths.py                # Cross-platform path management
└── requirements.txt        # Python package dependencies
```

## Getting Started

### 1. Installation

Clone the repository and install the dependencies in a virtual environment:

```sh
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Prepare Data

Place your input Excel files into the `data/` folder:
- **Students**: Place files into `data/students/` (columns: `Date`, `Roll No.`, `Class`, `Sem`, `Subject`).
- **Rooms**: Place files into `data/rooms/` (columns: `Floor`, `Room`, `Col`, `Row`, `Total`).

> **Tip**: If you need starter templates or test datasets:
> - Run `python generate_template.py` to create clean templates in `templates/`.
> - Run `python generate_test_data.py` to generate realistic synthetic student datasets for benchmarking.

### 3. Run the Application

```sh
python main.py
```

Generated seating plans, attendance sheets, and envelope summaries will be exported to the `output/` directory.

## Releases & Standalone Binaries

Pre-compiled standalone executables for Windows (`.exe`) and Linux are available in the [GitHub Releases](https://github.com/AkSinghSidhu/offline-exam-seating-engine/releases) section.
