# Offline Exam Seating Engine

Offline Exam Seating Engine is a Python-based utility designed to automate the process of seating arrangement for examinations. It processes an input of students and rooms to generate an optimized and conflict-free exam seating layout, along with necessary output files like attendance sheets and classwise/roomwise documents.

## Features

- Parse student data and room metrics from Excel templates.
- Automatically arrange seating while minimizing conflicts.
- Generates detailed output files including Attendance Sheets and Room/Class distributions.
- Works offline directly on the system.

## Data Templates

Two input templates are required:
1. Student details (Date, Roll No., Class, Sem, Subject).
2. Room details (Floor, Room, Col, Row, Total).

A script `generate_template.py` is provided to reconstruct sample template datasets. You can run it to generate `template_students.xlsx` and `template_rooms.xlsx` in the `templates/` folder.

## Getting Started

1. Place the student dataset and room details into the `data/students/` and `data/rooms/` folders respectively, mimicking the templates.
2. Ensure you have the required dependencies by installing `requirements.txt`:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the application:
   ```sh
   python main.py
   ```

Output configurations and document files will be exported in the `output/` folder.

## Releases

For standalone binaries, navigate to the GitHub Releases section to download the ready-to-use Executable format.
