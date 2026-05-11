"""
Attendance sheet exporter for generating Excel documents.

Generates one attendance sheet per room, following the template:
- Header: Room No, Floor, Date, Total Students
- Table: S.No | Roll No | Class | Sem | Subject | Signature
"""
from pathlib import Path
from datetime import date
from typing import Dict, List, Tuple

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class AttendanceExporter:
    """Exports attendance sheets as an Excel document, one sheet per room."""

    def export(self, plan, output_path: str, progress_callback=None) -> bool:
        """
        Export attendance sheets to an Excel document.

        Args:
            plan: The SeatingPlan containing room_plans
            output_path: Path for the output .xlsx file
            progress_callback: Optional callable taking an integer percentage

        Returns:
            True if export successful, False otherwise
        """
        try:
            wb = Workbook()
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]

            first_sheet = True
            total_rooms = len(plan.room_plans)
            
            # Keep track of sheet names to avoid duplicates
            sheet_names = set()

            for i, room_plan in enumerate(plan.room_plans):
                # Get all students in this room ordered by seat
                students_info = self._get_students_by_seat(room_plan)

                if not students_info:
                    continue
                    
                room_name = room_plan.room.name[:31]
                # Ensure unique sheet name
                original_name = room_name
                counter = 1
                while room_name in sheet_names:
                    suffix = f"_{counter}"
                    room_name = original_name[:31 - len(suffix)] + suffix
                    counter += 1
                sheet_names.add(room_name)

                ws = wb.create_sheet(title=room_name)

                self._create_attendance_sheet(
                    ws, room_plan, students_info
                )
                
                if progress_callback:
                    progress_callback(int((i + 1) / total_rooms * 100))

            # Save document
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            wb.save(output)

            return True

        except Exception as e:
            print(f"Attendance export error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_students_by_seat(self, room_plan) -> List[dict]:
        """
        Get all students in a room ordered seat-wise (first to last).

        Returns:
            List of student info dicts
            Each dict has: roll_number, student_class, semester, exam_id, subject
        """
        students_info = []

        # Iterate column-wise (top to bottom, then next column)
        # to match the seating fill direction
        num_rows = len(room_plan.grid)
        num_cols = len(room_plan.grid[0]) if num_rows > 0 else 0

        for col in range(num_cols):
            for row in range(num_rows):
                seat = room_plan.grid[row][col]
                if seat and not seat.is_empty and seat.student:
                    student = seat.student
                    students_info.append({
                        'roll_number': student.roll_number,
                        'student_class': student.student_class,
                        'semester': student.semester,
                        'exam_id': seat.exam_id,
                        'subject': student.subject,
                    })

        return students_info

    def _create_attendance_sheet(self, ws, room_plan, students_info: List[dict]):
        """Create one attendance sheet (one page) in the worksheet."""
        room = room_plan.room

        # Determine the subject name from student data
        subject_display = ""
        for info in students_info:
            if info.get('subject'):
                subject_display = info['subject']
                break
        if not subject_display:
            subject_name = students_info[0]['exam_id'] if students_info else ""
            subject_display = subject_name.replace('_', ' ').title() if subject_name else ""

        total_students = len(students_info)
        # Date is left empty to be filled manually
        today = ""

        # Styling
        bold_font = Font(name='Calibri', size=11, bold=True)
        normal_font = Font(name='Calibri', size=11)
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

        # --- Header Table (Room info) ---
        # Row 1: Room No | Floor
        ws.cell(row=1, column=1, value="Room No.").font = bold_font
        ws.cell(row=1, column=2, value=room.name).font = normal_font
        ws.cell(row=1, column=3, value="Floor").font = bold_font
        ws.cell(row=1, column=4, value="1st").font = normal_font
        
        # Row 2: Date | Total Students
        ws.cell(row=2, column=1, value="Date").font = bold_font
        ws.cell(row=2, column=2, value="").font = normal_font
        ws.cell(row=2, column=3, value="Total Students").font = bold_font
        ws.cell(row=2, column=4, value=total_students).font = normal_font
        
        # Apply borders to header
        for r in range(1, 3):
            for c in range(1, 5):
                cell = ws.cell(row=r, column=c)
                cell.border = thin_border
                cell.alignment = left_align

        # --- Student Table ---
        start_row = 4
        headers = ["S.No", "Roll No", "Class", "Sem", "Subject", "Answer Sheet No.", "Signature"]
        
        # Header row
        for i, header in enumerate(headers):
            cell = ws.cell(row=start_row, column=i+1, value=header)
            cell.font = bold_font
            cell.alignment = center_align
            cell.border = thin_border

        # Student rows
        for idx, info in enumerate(students_info):
            current_row = start_row + 1 + idx
            
            # S.No
            c1 = ws.cell(row=current_row, column=1, value=idx + 1)
            # Roll No
            c2 = ws.cell(row=current_row, column=2, value=info['roll_number'])
            # Class
            c3 = ws.cell(row=current_row, column=3, value=info['student_class'])
            # Sem
            c4 = ws.cell(row=current_row, column=4, value=info['semester'])
            # Subject
            student_subject = info.get('subject') or subject_display
            c5 = ws.cell(row=current_row, column=5, value=student_subject)
            # Answer Sheet No.
            c6 = ws.cell(row=current_row, column=6, value="")
            # Signature
            c7 = ws.cell(row=current_row, column=7, value="")
            
            for c in [c1, c2, c3, c4, c5, c6, c7]:
                c.font = normal_font
                c.alignment = center_align
                c.border = thin_border

        # Set column widths
        ws.column_dimensions['A'].width = 6   # S.No
        ws.column_dimensions['B'].width = 15  # Roll No
        ws.column_dimensions['C'].width = 15  # Class
        ws.column_dimensions['D'].width = 8   # Sem
        ws.column_dimensions['E'].width = 25  # Subject
        ws.column_dimensions['F'].width = 18  # Answer Sheet No.
        ws.column_dimensions['G'].width = 15  # Signature
        
        # Page setup for printing
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
