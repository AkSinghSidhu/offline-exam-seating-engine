"""
Class-wise attendance sheet exporter for generating Word documents.

Generates one attendance sheet per class (class + semester) per room,
following the template:
- Header: Room No, Class, Semester, Date, Total Students
- Table: S.No | Roll No | Subject | Signature

Performance-optimised: uses table-level border XML (O(1) per table)
and direct XML cell writes instead of python-docx property wrappers.
"""
from pathlib import Path
from datetime import date
from typing import Dict, List, Tuple
from collections import defaultdict

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml


# Pre-built border XML string (reused for every table — O(1) per table)
_BORDER_XML = (
    '<w:tblBorders %s>'
    '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '</w:tblBorders>'
) % nsdecls('w')


class ClassWiseAttendanceExporter:
    """Exports attendance sheets as a Word document, one page per class per room."""

    def export(self, plan, output_path: str, progress_callback=None) -> bool:
        """
        Export class-wise attendance sheets to a Word document.

        Args:
            plan: The SeatingPlan containing room_plans
            output_path: Path for the output .docx file
            progress_callback: Optional callable taking an integer percentage

        Returns:
            True if export successful, False otherwise
        """
        try:
            doc = Document()

            # Set default font
            style = doc.styles['Normal']
            font = style.font
            font.name = 'Calibri'
            font.size = Pt(10)

            # Set narrow margins
            section = doc.sections[0]
            section.top_margin = Cm(1.5)
            section.bottom_margin = Cm(1.5)
            section.left_margin = Cm(1.5)
            section.right_margin = Cm(1.5)

            # Gather grouped students but preserve room order from plan
            # (Room order matches the preview and the RoomWise exporter)
            class_groups_by_room = self._group_students_by_room_and_class_ordered(plan)

            if not class_groups_by_room:
                return False

            # Count total sheets for progress
            total_sheets = sum(len(groups) for groups in class_groups_by_room)
            produced_sheets = 0
            first_sheet = True

            # Iterate rooms in exactly the order they appear in the plan
            for room_plan, groups in class_groups_by_room:
                room_name = room_plan.room.name
                # Sort classes within the room alphabetically
                for class_key, students_info in sorted(groups.items()):
                    if not first_sheet:
                        doc.add_page_break()
                    first_sheet = False

                    self._create_attendance_sheet(doc, room_name, class_key, students_info)

                    produced_sheets += 1
                    if progress_callback:
                        progress_callback(int(produced_sheets / total_sheets * 100))

            # Save document
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            doc.save(output)

            return True

        except Exception as e:
            print(f"Class-wise attendance export error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _group_students_by_room_and_class_ordered(self, plan) -> List[Tuple[object, Dict[str, List[dict]]]]:
        """
        Collect every seated student, preserving the original room order.

        Returns:
            List of tuples: (room_plan, Dict[class_sem_key, list_of_students])
            This guarantees rooms are processed in the exact order as the SeatingPlan (and RoomWise).
        """
        results = []

        for room_plan in plan.room_plans:
            num_rows = len(room_plan.grid)
            num_cols = len(room_plan.grid[0]) if num_rows > 0 else 0
            
            groups: Dict[str, List[dict]] = defaultdict(list)

            # Column-major scan to match seating fill direction
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
                        })

            if groups:
                # Sort each class group's students by roll number
                for key in groups:
                    groups[key].sort(key=lambda s: s['roll_number'])
                
                results.append((room_plan, dict(groups)))

        return results

    def _create_attendance_sheet(self, doc, room_name: str, class_key: str, students_info: List[dict]):
        """Create one attendance sheet (one page) in the document."""
        total_students = len(students_info)
        today = date.today().strftime("%d-%m-%Y")

        # Determine subject display — prefer explicit subject field
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

        # --- Header Table ---
        header_table = doc.add_table(rows=2, cols=4)
        header_table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Row 1: Room No | Floor
        self._set_cell(header_table.cell(0, 0), "Room No.", bold=True)
        self._set_cell(header_table.cell(0, 1), room_name)
        self._set_cell(header_table.cell(0, 2), "Floor", bold=True)
        self._set_cell(header_table.cell(0, 3), "1st")

        # Row 2: Date | Total Students
        self._set_cell(header_table.cell(1, 0), "Date", bold=True)
        self._set_cell(header_table.cell(1, 1), today)
        self._set_cell(header_table.cell(1, 2), "Total Students", bold=True)
        self._set_cell(header_table.cell(1, 3), str(total_students))

        self._apply_table_borders(header_table)

        # Spacer
        doc.add_paragraph("")

        # --- Student Table (6 columns) ---
        num_rows = total_students + 1  # +1 for header row
        student_table = doc.add_table(rows=num_rows, cols=6)
        student_table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header row
        col_headers = ["S.No", "Roll No", "Class", "Sem", "Subject", "Signature"]
        for i, header in enumerate(col_headers):
            self._set_cell(student_table.cell(0, i), header, bold=True)

        # Student rows — fast XML fill
        for idx, info in enumerate(students_info):
            row_cells = student_table.rows[idx + 1].cells
            self._set_cell_fast(row_cells[0], str(idx + 1))
            self._set_cell_fast(row_cells[1], info['roll_number'])
            self._set_cell_fast(row_cells[2], info.get('student_class', class_key))
            self._set_cell_fast(row_cells[3], info.get('semester', semester))
            student_subject = info.get('subject') or subject_display
            self._set_cell_fast(row_cells[4], student_subject)
            # Signature column (row_cells[5]) left empty

        self._apply_table_borders(student_table)

        self._set_column_widths(student_table, [
            Cm(1.2),   # S.No
            Cm(2.5),   # Roll No
            Cm(4.0),   # Class
            Cm(1.2),   # Sem
            Cm(6.5),   # Subject
            Cm(3.0),   # Signature
        ])

    def _set_cell(self, cell, text: str, bold: bool = False):
        """Set cell text with formatting (used for headers/small tables)."""
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = paragraph.add_run(text)
        run.font.size = Pt(10)
        run.font.name = 'Calibri'
        run.bold = bold

    def _set_cell_fast(self, cell, text: str):
        """Fast cell text setter — writes directly to underlying XML (~3x speedup)."""
        tc = cell._tc
        for p in tc.findall(qn('w:p')):
            tc.remove(p)
        p = OxmlElement('w:p')
        r = OxmlElement('w:r')
        t = OxmlElement('w:t')
        t.text = text
        if text and (text[0] == ' ' or text[-1] == ' '):
            t.set(qn('xml:space'), 'preserve')
        r.append(t)
        p.append(r)
        tc.append(p)

    def _apply_table_borders(self, table):
        """Apply thin borders to entire table in ONE XML operation (O(1))."""
        tbl = table._tbl
        tblPr = tbl.tblPr
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.insert(0, tblPr)

        for existing in tblPr.findall(qn('w:tblBorders')):
            tblPr.remove(existing)

        borders = parse_xml(_BORDER_XML)
        tblPr.append(borders)

    def _set_column_widths(self, table, widths):
        """Set column widths via first row only (Word propagates to all rows)."""
        if table.rows:
            first_row = table.rows[0]
            for idx, width in enumerate(widths):
                if idx < len(first_row.cells):
                    first_row.cells[idx].width = width
