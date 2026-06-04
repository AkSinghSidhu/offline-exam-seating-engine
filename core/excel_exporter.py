"""
Excel exporter for generating print-ready seating plans.

Each room generates one Excel sheet with formatted seating grid.
"""
from pathlib import Path
from typing import Dict
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Border, Side, Alignment
)
from openpyxl.utils import get_column_letter


class ExcelExporter:
    """
    Exports seating plans to Excel format.
    
    Features:
    - One sheet per room
    - Color-coded by exam
    - Print-ready formatting
    - Row/column headers
    """
    
    def export(self, plan, output_path: str) -> bool:
        """
        Export seating plan to Excel file.
        
        Args:
            plan: The seating plan to export
            output_path: Path for the output Excel file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            wb = Workbook()
            # Remove default sheet
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]
            
            # Create sheet for each room
            for room_plan in plan.room_plans:
                self._create_room_sheet(wb, room_plan)
            
            # Create summary sheet
            self._create_summary_sheet(wb, plan)
            
            # Save workbook
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            wb.save(output)
            
            return True
            
        except Exception as e:
            print(f"Export error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_room_sheet(self, wb: Workbook, room_plan):
        """Create a worksheet for a single room."""
        base_title = room_plan.room.name[:31]
        title = base_title
        counter = 1
        while title in wb.sheetnames:
            suffix = f"_{counter}"
            title = f"{base_title[:31-len(suffix)]}{suffix}"
            counter += 1
            
        ws = wb.create_sheet(title=title)
        
        room = room_plan.room
        
        # Styling
        header_font = Font(bold=True)
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )
        
        # Title row
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=room.columns + 1)
        title_cell = ws.cell(row=1, column=1)
        title_cell.value = f"{room.name} - {room.category.value} ({room.capacity} seats)"
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = center_align
        
        # Column headers (seat numbers)
        for col in range(room.columns):
            cell = ws.cell(row=2, column=col + 2)
            cell.value = f"Col {col + 1}"
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border
        
        # Row headers and seat data
        for row in range(room.rows):
            # Row header
            row_header = ws.cell(row=row + 3, column=1)
            row_header.value = f"Row {row + 1}"
            row_header.font = header_font
            row_header.alignment = center_align
            row_header.border = thin_border
            
            # Seat data
            for col in range(room.columns):
                cell = ws.cell(row=row + 3, column=col + 2)
                seat = room_plan.get_seat(row, col)
                
                if seat and not seat.is_empty and seat.student:
                    # Include only roll number (UID)
                    student = seat.student
                    cell.value = f"{student.roll_number}"
                else:
                    cell.value = "—"
                
                cell.alignment = center_align
                cell.border = thin_border
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 12
        for col in range(room.columns):
            ws.column_dimensions[get_column_letter(col + 2)].width = 20
        
        # Adjust row heights
        for row in range(room.rows + 3):
            ws.row_dimensions[row + 1].height = 40 if row >= 2 else 25
        
        # Add room summary section below the seating grid
        summary_start_row = room.rows + 5  # Leave a gap after seating grid
        
        # Get exam counts for this room, broken down by class and subject
        exam_counts = {}
        for row_data in room_plan.grid:
            for seat in row_data:
                if seat and not seat.is_empty and seat.student:
                    student = seat.student
                    
                    # Handle cases where class or subject might be empty
                    s_class = student.student_class if student.student_class else "Unknown Class"
                    s_sem = f"Sem {student.semester}" if student.semester else ""
                    
                    # If subject is provided, use it, else fallback to exam_id
                    s_subject = student.subject if student.subject else student.exam_id
                    
                    if student.student_class:
                        key_parts = [s_class]
                        if s_sem:
                            key_parts.append(s_sem)
                        key_parts.append(s_subject)
                        key = " - ".join(key_parts)
                    else:
                        key = s_subject
                        
                    exam_counts[key] = exam_counts.get(key, 0) + 1

        total_students = room_plan.student_count()
        
        # Summary header
        ws.merge_cells(start_row=summary_start_row, start_column=1, 
                      end_row=summary_start_row, end_column=2)
        summary_header = ws.cell(row=summary_start_row, column=1)
        summary_header.value = "Room Summary"
        summary_header.font = Font(bold=True, size=12)
        summary_header.alignment = center_align
        
        # Total students row
        summary_start_row += 1
        ws.cell(row=summary_start_row, column=1).value = "Total Students:"
        ws.cell(row=summary_start_row, column=1).font = Font(bold=True)
        ws.cell(row=summary_start_row, column=2).value = total_students
        ws.cell(row=summary_start_row, column=2).font = Font(bold=True, size=11)
        
        # Exam breakdown rows
        summary_start_row += 1
        ws.cell(row=summary_start_row, column=1).value = "Exam-wise Breakdown:"
        ws.cell(row=summary_start_row, column=1).font = Font(bold=True, italic=True)
        
        for exam_id, count in sorted(exam_counts.items()):
            summary_start_row += 1
            # Exam name cell
            exam_cell = ws.cell(row=summary_start_row, column=1)
            exam_cell.value = exam_id
            
            # Count cell
            count_cell = ws.cell(row=summary_start_row, column=2)
            count_cell.value = count
            count_cell.alignment = center_align
    
    def _create_summary_sheet(self, wb: Workbook, plan):
        """Create a summary sheet with statistics."""
        ws = wb.create_sheet(title="Summary", index=0)
        
        center_align = Alignment(horizontal="center", vertical="center")
        bold_font = Font(bold=True)
        
        # Title
        ws.merge_cells("A1:D1")
        ws["A1"] = "Seating Plan Summary"
        ws["A1"].font = Font(bold=True, size=16)
        ws["A1"].alignment = center_align
        
        # Statistics
        ws["A3"] = "Total Students Seated:"
        ws["B3"] = plan.total_students_seated()
        ws["A3"].font = bold_font
        
        ws["A4"] = "Total Rooms Used:"
        ws["B4"] = len(plan.room_plans)
        ws["A4"].font = bold_font
        
        # Room breakdown
        ws["A6"] = "Room Breakdown"
        ws["A6"].font = Font(bold=True, size=12)
        
        headers = ["Room", "Category", "Capacity", "Seated"]
        for i, h in enumerate(headers):
            cell = ws.cell(row=7, column=i + 1)
            cell.value = h
            cell.font = bold_font
        
        for idx, room_plan in enumerate(plan.room_plans):
            row = 8 + idx
            ws.cell(row=row, column=1).value = room_plan.room.name
            ws.cell(row=row, column=2).value = room_plan.room.category.value
            ws.cell(row=row, column=3).value = room_plan.room.capacity
            ws.cell(row=row, column=4).value = room_plan.student_count()
        
        # Exam breakdown
        start_row = 8 + len(plan.room_plans) + 2
        ws.cell(row=start_row, column=1).value = "Exam Breakdown"
        ws.cell(row=start_row, column=1).font = Font(bold=True, size=12)
        
        # Collect all exam counts
        all_exam_counts: Dict[str, int] = {}
        for room_plan in plan.room_plans:
            for row_data in room_plan.grid:
                for seat in row_data:
                    if seat and not seat.is_empty and seat.student:
                        student = seat.student
                        
                        s_class = student.student_class if student.student_class else "Unknown Class"
                        s_sem = f"Sem {student.semester}" if student.semester else ""
                        s_subject = student.subject if student.subject else student.exam_id
                        
                        if student.student_class:
                            key_parts = [s_class]
                            if s_sem:
                                key_parts.append(s_sem)
                            key_parts.append(s_subject)
                            key = " - ".join(key_parts)
                        else:
                            key = s_subject
                            
                        all_exam_counts[key] = all_exam_counts.get(key, 0) + 1
        
        ws.cell(row=start_row + 1, column=1).value = "Exam"
        ws.cell(row=start_row + 1, column=2).value = "Students Seated"
        ws.cell(row=start_row + 1, column=1).font = bold_font
        ws.cell(row=start_row + 1, column=2).font = bold_font
        
        for idx, (exam_id, count) in enumerate(sorted(all_exam_counts.items())):
            row = start_row + 2 + idx
            ws.cell(row=row, column=1).value = exam_id
            ws.cell(row=row, column=2).value = count
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 12
