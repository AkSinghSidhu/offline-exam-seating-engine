"""Student data model for the exam seating tool."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Student:
    """Represents a student taking an exam."""
    roll_number: str
    student_class: str = ""  # Class/Program
    semester: str = ""       # Semester
    exam_id: str = ""
    subject: str = ""        # Subject name from input data
    
    @classmethod
    def from_line(cls, line: str, exam_id: str = "") -> Optional['Student']:
        """
        Parse a student from a file line (legacy support).
        Expected format: roll_number,class,sem or just roll_number
        """
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 3:
            return cls(roll_number=parts[0], student_class=parts[1], semester=parts[2], exam_id=exam_id)
        elif len(parts) >= 2:
            return cls(roll_number=parts[0], student_class=parts[1], exam_id=exam_id)
        elif len(parts) == 1 and parts[0]:
            return cls(roll_number=parts[0], exam_id=exam_id)
        return None
    
    @staticmethod
    def _clean_numeric_str(value) -> str:
        """Convert a value to string, stripping trailing .0 from floats."""
        s = str(value).strip()
        # If it looks like a float ending in .0, strip it (e.g. '241606001.0' -> '241606001')
        if s.endswith('.0'):
            try:
                return str(int(float(s)))
            except (ValueError, OverflowError):
                pass
        return s
    
    @classmethod
    def from_excel_row(cls, roll_no: str, student_class: str = "", semester: str = "", exam_id: str = "", subject: str = "") -> 'Student':
        """Create a student from Excel row data."""
        return cls(
            roll_number=cls._clean_numeric_str(roll_no),
            student_class=str(student_class).strip() if student_class else "",
            semester=cls._clean_numeric_str(semester) if semester else "",
            exam_id=exam_id,
            subject=str(subject).strip() if subject else ""
        )
    
    def display_text(self) -> str:
        """Return display text for seating plan."""
        return self.roll_number
    
    def full_display(self) -> str:
        """Return full display with class and semester if available."""
        parts = [self.roll_number]
        if self.student_class:
            parts.append(self.student_class)
        if self.semester:
            parts.append(f"Sem {self.semester}")
        return " | ".join(parts)
    
    def __str__(self) -> str:
        return self.display_text()
