"""Exam data model for the exam seating tool."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path
import pandas as pd
from .student import Student


@dataclass
class Exam:
    """Represents an exam/subject with its enrolled students."""
    id: str
    name: str
    students: List[Student] = field(default_factory=list)
    color: str = "#3498db"  # Default blue color for visualization
    
    @classmethod
    def from_file(cls, file_path: str, exam_id: str = None, exam_name: str = None) -> Optional['Exam']:
        """
        Load an exam and its students from a file (single exam mode).
        For auto-splitting by class/sem, use from_file_auto_split() instead.
        """
        exams = cls.from_file_auto_split(file_path, auto_split=False)
        return exams[0] if exams else None
    
    @classmethod
    def from_file_auto_split(cls, file_path: str, auto_split: bool = True) -> List['Exam']:
        """
        Load exams from a file with optional auto-splitting.
        
        If auto_split=True and Class/Sem columns exist, automatically creates
        separate exams for each unique Class+Sem combination.
        
        For Excel: expects columns "Roll No." (required), "Class", "Sem"
        For text: expects roll_number,class,sem format
        
        Returns list of Exam objects (may contain multiple if auto-split).
        """
        path = Path(file_path)
        if not path.exists():
            return []
        
        base_id = path.stem.upper()
        base_name = path.stem.replace('_', ' ').title()
        
        try:
            # Excel file
            if path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
                
                # Find the roll number column (flexible naming)
                roll_col = None
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ['roll no.', 'roll no', 'rollno', 'roll_no', 'roll number', 'roll']:
                        roll_col = col
                        break
                
                if roll_col is None:
                    # Try first column as roll number
                    roll_col = df.columns[0]
                
                # Find class column
                class_col = None
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ['class', 'program', 'course', 'branch']:
                        class_col = col
                        break
                
                # Find semester column
                sem_col = None
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ['sem', 'semester', 'sem.']:
                        sem_col = col
                        break
                
                # Find subject column
                subject_col = None
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ['subject', 'subject name', 'paper', 'paper name', 'course name']:
                        subject_col = col
                        break
                
                # Find course code column
                course_code_col = None
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ['course code', 'subject code', 'paper code', 'course_code']:
                        course_code_col = col
                        break
                
                # Group students by class+sem if auto_split is enabled
                students_by_group: Dict[str, List[Student]] = {}
                
                for _, row in df.iterrows():
                    roll_no = row[roll_col]
                    if pd.isna(roll_no) or str(roll_no).strip() == '':
                        continue
                    
                    student_class = ""
                    if class_col and not pd.isna(row.get(class_col)):
                        student_class = str(row[class_col]).strip()
                    
                    semester = ""
                    if sem_col and not pd.isna(row.get(sem_col)):
                        semester = Student._clean_numeric_str(row[sem_col])
                    
                    subject = ""
                    if subject_col and not pd.isna(row.get(subject_col)):
                        subject = str(row[subject_col]).strip()
                        
                    course_code = ""
                    if course_code_col and not pd.isna(row.get(course_code_col)):
                        course_code = str(row[course_code_col]).strip()
                    
                    # Create group key
                    if auto_split and (student_class or semester):
                        # Create unique group key from class + sem
                        group_key = f"{student_class} Sem {semester}" if semester else student_class
                        if not student_class and semester:
                            group_key = f"Semester {semester}"
                    else:
                        group_key = base_name
                    
                    if group_key not in students_by_group:
                        students_by_group[group_key] = []
                    
                    # Create exam_id from group
                    exam_id = group_key.upper().replace(' ', '_')
                    
                    student = Student.from_excel_row(
                        roll_no=roll_no,
                        student_class=student_class,
                        semester=semester,
                        exam_id=exam_id,
                        subject=subject,
                        course_code=course_code
                    )
                    students_by_group[group_key].append(student)
                
                # Create exam objects
                exams = []
                for group_name, students in students_by_group.items():
                    exam_id = group_name.upper().replace(' ', '_')
                    exam = cls(id=exam_id, name=group_name, students=students)
                    exams.append(exam)
                
                return exams
            
            # Text file (legacy support - no auto-split)
            else:
                students = []
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        student = Student.from_line(line, base_id)
                        if student:
                            students.append(student)
                
                if students:
                    return [cls(id=base_id, name=base_name, students=students)]
                return []
                            
        except Exception as e:
            print(f"Error loading exam file: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def student_count(self) -> int:
        """Return the number of students in this exam."""
        return len(self.students)
    
    def get_next_student(self, index: int) -> Optional[Student]:
        """Get student at index, or None if out of range."""
        if 0 <= index < len(self.students):
            return self.students[index]
        return None
    
    def __str__(self) -> str:
        return f"{self.name} ({len(self.students)} students)"
