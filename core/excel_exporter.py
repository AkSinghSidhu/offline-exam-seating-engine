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
    
    # Default exam colors (will cycle through these)
    EXAM_COLORS = [
        "4A90D9",  # Blue
        "50C878",  # Emerald
        "F4A460",  # Sandy Brown
        "DA70D6",  # Orchid
        "20B2AA",  # Light Sea Green
        "FFB347",  # Pastel Orange
        "87CEEB",  # Sky Blue
        "DDA0DD",  # Plum
    ]
    
    EMPTY_COLOR = "E0E0E0"  # Light gray for empty seats
    HEADER_COLOR = "2C3E50"  # Dark header
    
    def __init__(self):
        self.exam_color_map: Dict[str, str] = {}
    
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
            
            # Assign colors to exams
            self._assign_exam_colors(plan)
            
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
    
    def _assign_exam_colors(self, plan):
        """Assign colors to each exam in the plan."""
        exam_ids = set()
        for room_plan in plan.room_plans:
            for row in room_plan.grid:
                for seat in row:
                    if seat and not seat.is_empty:
                        exam_ids.add(seat.exam_id)
        
        for i, exam_id in enumerate(sorted(exam_ids)):
            self.exam_color_map[exam_id] = self.EXAM_COLORS[i % len(self.EXAM_COLORS)]
    
    def _create_room_sheet(self, wb: Workbook, room_plan):
        """Create a worksheet for a single room."""
        ws = wb.create_sheet(title=room_plan.room.name[:31])  # Excel limit
        
        room = room_plan.room
        
        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color=self.HEADER_COLOR, end_color=self.HEADER_COLOR, fill_type="solid")
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
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border
        
        # Row headers and seat data
        for row in range(room.rows):
            # Row header
            row_header = ws.cell(row=row + 3, column=1)
            row_header.value = f"Row {row + 1}"
            row_header.font = header_font
            row_header.fill = header_fill
            row_header.alignment = center_align
            row_header.border = thin_border
            
            # Seat data
            for col in range(room.columns):
                cell = ws.cell(row=row + 3, column=col + 2)
                seat = room_plan.get_seat(row, col)
                
                if seat and not seat.is_empty and seat.student:
                    # Include roll number, class, sem
                    student = seat.student
                    info_parts = [student.roll_number]
                    if hasattr(student, 'student_class') and student.student_class:
                        info_parts.append(student.student_class)
                    if hasattr(student, 'semester') and student.semester:
                        info_parts.append(f"Sem {student.semester}")
                    cell.value = f"{' | '.join(info_parts)}\n({seat.exam_id})"
                    color = self.exam_color_map.get(seat.exam_id, "FFFFFF")
                    cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                else:
                    cell.value = "—"
                    cell.fill = PatternFill(start_color=self.EMPTY_COLOR, end_color=self.EMPTY_COLOR, fill_type="solid")
                
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
        
        # Get exam counts for this room
        exam_counts = room_plan.get_exam_counts()
        total_students = room_plan.student_count()
        
        # Summary header
        ws.merge_cells(start_row=summary_start_row, start_column=1, 
                      end_row=summary_start_row, end_column=3)
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
            
            # Color indicator cell
            color = self.exam_color_map.get(exam_id, "FFFFFF")
            color_cell = ws.cell(row=summary_start_row, column=2)
            color_cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
            color_cell.border = thin_border
            
            # Count cell
            count_cell = ws.cell(row=summary_start_row, column=3)
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
            counts = room_plan.get_exam_counts()
            for exam_id, count in counts.items():
                all_exam_counts[exam_id] = all_exam_counts.get(exam_id, 0) + count
        
        ws.cell(row=start_row + 1, column=1).value = "Exam"
        ws.cell(row=start_row + 1, column=2).value = "Students Seated"
        ws.cell(row=start_row + 1, column=1).font = bold_font
        ws.cell(row=start_row + 1, column=2).font = bold_font
        
        for idx, (exam_id, count) in enumerate(sorted(all_exam_counts.items())):
            row = start_row + 2 + idx
            ws.cell(row=row, column=1).value = exam_id
            ws.cell(row=row, column=2).value = count
            
            # Color indicator
            color = self.exam_color_map.get(exam_id, "FFFFFF")
            ws.cell(row=row, column=3).fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 12
