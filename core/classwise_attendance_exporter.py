"""
Class-wise attendance sheet exporter for generating Excel documents.

Generates one attendance sheet per class (class + semester) per room,
following the template:
- Header: Room No, Class, Semester, Date, Total Students
- Table: S.No | Roll No | Subject | Signature
"""
from pathlib import Path
from datetime import date
from typing import Dict, List, Tuple
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ClassWiseAttendanceExporter:
    """Exports attendance sheets as an Excel document, one sheet per class per room."""

    def export(self, plan, output_path: str, progress_callback=None, date_str: str = "") -> bool:
        """
        Export class-wise attendance sheets to an Excel document.

        Args:
            plan: The SeatingPlan containing room_plans
            output_path: Path for the output .xlsx file
            progress_callback: Optional callable taking an integer percentage

        Returns:
            True if export successful, False otherwise
        """
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Classwise Attendance"

            class_groups_by_room = self._group_students_by_room_and_class_ordered(plan)

            if not class_groups_by_room:
                return False

            total_sheets = sum(len(groups) for groups in class_groups_by_room)
            produced_sheets = 0
            current_row = 1

            for room_plan, groups in class_groups_by_room:
                room_name = room_plan.room.name
                for class_key, students_info in sorted(groups.items()):
                    
                    last_row = self._create_attendance_sheet(ws, room_plan, class_key, students_info, date_str, current_row)
                    current_row = last_row + 3

                    produced_sheets += 1
                    if progress_callback:
                        progress_callback(int(produced_sheets / total_sheets * 100))

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            wb.save(output)

            return True

        except Exception as e:
            print(f"Class-wise attendance export error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _group_students_by_room_and_class_ordered(self, plan) -> List[Tuple[object, Dict[str, List[dict]]]]:
        """
        Collect every seated student, preserving the original room order.

        Returns:
            List of tuples: (room_plan, Dict[class_sem_key, list_of_students])
        """
        results = []

        for room_plan in plan.room_plans:
            num_rows = len(room_plan.grid)
            num_cols = len(room_plan.grid[0]) if num_rows > 0 else 0
            
            groups: Dict[str, List[dict]] = defaultdict(list)

            for col in range(num_cols):
                for row in range(num_rows):
                    seat = room_plan.grid[row][col]
                    if seat and not seat.is_empty and seat.student:
                        student = seat.student
                        class_part = student.student_class or "Unknown"
                        sem_part = student.semester or ""
                        class_key = f"{class_part} Sem {sem_part}" if sem_part else class_part

                        groups[class_key].append({
                            'roll_number': student.roll_number,
                            'student_class': student.student_class,
                            'semester': student.semester,
                            'subject': student.subject,
                            'exam_id': seat.exam_id,
                            'course_code': getattr(student, 'course_code', ''),
                        })

            if groups:
                for key in groups:
                    groups[key].sort(key=lambda s: s['roll_number'])
                
                results.append((room_plan, dict(groups)))

        return results

    def _create_attendance_sheet(self, ws, room_plan, class_key: str, students_info: List[dict], date_str: str, start_row: int) -> int:
        """Create one attendance sheet in the worksheet. Returns the last row written."""
        room_name = room_plan.room.name
        total_students = len(students_info)
        subject_display = ""
        for info in students_info:
            if info.get('subject'):
                subject_display = info['subject']
                break
        if not subject_display:
            exam_id = students_info[0].get('exam_id', '')
            subject_display = exam_id.replace('_', ' ').title() if exam_id else ""

        semester = students_info[0].get('semester', '')
        student_class = students_info[0].get('student_class', class_key)

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

        # --- Header Table ---
        ws.cell(row=start_row, column=1, value="Room No.").font = bold_font
        ws.cell(row=start_row, column=2, value=room_name).font = normal_font
        ws.cell(row=start_row, column=3, value="Floor").font = bold_font
        floor_value = getattr(room_plan.room, 'floor', '')
        ws.cell(row=start_row, column=4, value=floor_value).font = normal_font
        ws.cell(row=start_row, column=5, value="").font = normal_font
        ws.cell(row=start_row, column=6, value="").font = normal_font

        ws.cell(row=start_row + 1, column=1, value="Date").font = bold_font
        ws.cell(row=start_row + 1, column=2, value=date_str).font = normal_font
        ws.cell(row=start_row + 1, column=3, value="Class").font = bold_font
        
        class_display = f"{student_class} - Sem {semester}" if semester else student_class
        ws.cell(row=start_row + 1, column=4, value=class_display).font = normal_font
        
        ws.cell(row=start_row + 1, column=5, value="Total Students").font = bold_font
        ws.cell(row=start_row + 1, column=6, value=total_students).font = normal_font

        for r in range(start_row, start_row + 2):
            for c in range(1, 7):
                cell = ws.cell(row=r, column=c)
                cell.border = thin_border
                cell.alignment = left_align

        # --- Student Table (5 columns) ---
        table_start_row = start_row + 3
        col_headers = ["S.No", "Roll No", "Subject", "Answer Sheet No.", "Signature"]
        
        for i, header in enumerate(col_headers):
            cell = ws.cell(row=table_start_row, column=i+1, value=header)
            cell.font = bold_font
            cell.alignment = center_align
            cell.border = thin_border

        last_row = table_start_row
        for idx, info in enumerate(students_info):
            current_row = table_start_row + 1 + idx
            last_row = current_row
            
            c1 = ws.cell(row=current_row, column=1, value=idx + 1)
            c2 = ws.cell(row=current_row, column=2, value=info['roll_number'])
            
            student_subject = info.get('subject') or subject_display
            c3 = ws.cell(row=current_row, column=3, value=student_subject)
            c4 = ws.cell(row=current_row, column=4, value="")
            c5 = ws.cell(row=current_row, column=5, value="")
            
            for c in [c1, c2, c3, c4, c5]:
                c.font = normal_font
                c.alignment = center_align
                c.border = thin_border

        ws.column_dimensions['A'].width = 6   # S.No
        ws.column_dimensions['B'].width = 15  # Roll No
        ws.column_dimensions['C'].width = 25  # Subject
        ws.column_dimensions['D'].width = 18  # Answer Sheet No.
        ws.column_dimensions['E'].width = 15  # Signature
        ws.column_dimensions['F'].width = 10  # Total Students Num
        
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        return last_row
