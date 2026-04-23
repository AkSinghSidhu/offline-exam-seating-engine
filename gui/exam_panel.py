"""Exam management panel for adding/removing exams and loading students."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from typing import List, Optional, Callable
from pathlib import Path
from models.exam import Exam
from gui.theme import COLORS, get_exam_color


class ExamCard(QFrame):
    """Card widget displaying an exam with its student count."""
    
    remove_clicked = Signal(object)  # Emits the card itself
    
    def __init__(self, exam: Exam, color: str):
        super().__init__()
        self.exam = exam
        self.color = color
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the card UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border: 2px solid {self.color};
                border-radius: 10px;
            }}
        """)
        self.setFixedHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Color indicator bar
        color_bar = QFrame()
        color_bar.setFixedSize(6, 50)
        color_bar.setStyleSheet(f"""
            background-color: {self.color};
            border-radius: 3px;
        """)
        layout.addWidget(color_bar)
        
        # Info container
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Exam name
        name_label = QLabel(self.exam.name)
        name_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Student count
        count_label = QLabel(f"📚 {self.exam.student_count()} students")
        count_label.setFont(QFont("Segoe UI", 11))
        count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        info_layout.addWidget(count_label)
        
        layout.addLayout(info_layout, 1)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self))
        layout.addWidget(remove_btn)


class ExamPanel(QWidget):
    """Panel for managing exams."""
    
    exams_changed = Signal()
    
    def __init__(self, on_change: Optional[Callable] = None):
        super().__init__()
        self.exams: List[Exam] = []
        self.exam_cards: List[ExamCard] = []
        self.on_change = on_change
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the panel UI."""
        self.setStyleSheet(f"background-color: {COLORS['bg_secondary']}; border-radius: 10px;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)  # Add padding to match other panels
        main_layout.setSpacing(8)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("EXAMS")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("+ Add Exam")
        add_btn.setFixedHeight(32)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
        """)
        add_btn.clicked.connect(self._add_exam)
        header_layout.addWidget(add_btn)
        
        main_layout.addWidget(header)
        
        # Scroll area for exam list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        self.list_widget = QWidget()
        self.list_widget.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        
        scroll.setWidget(self.list_widget)
        main_layout.addWidget(scroll, 1)
        
        # Empty state label
        self.empty_label = QLabel("No exams added yet.\nClick '+ Add Exam' to load student lists.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.list_layout.insertWidget(0, self.empty_label)
        
        # Summary
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_tertiary']};
            border-radius: 6px;
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(12, 8, 12, 8)
        
        self.summary_label = QLabel("0 exams • 0 students")
        self.summary_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.summary_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        summary_layout.addWidget(self.summary_label, 0, Qt.AlignCenter)
        
        main_layout.addWidget(self.summary_frame)
    
    def _add_exam(self):
        """Open file dialog to add an exam."""
        from paths import get_students_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Student List (Excel)",
            get_students_dir(),
            "Excel files (*.xlsx *.xls);;Text files (*.txt);;CSV files (*.csv);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        # Load exams from file (auto-splits by Class+Sem)
        exams = Exam.from_file_auto_split(file_path, auto_split=True)
        
        if not exams:
            QMessageBox.critical(self, "Error", f"Failed to load students from:\n{file_path}")
            return
        
        total_students = sum(e.student_count() for e in exams)
        if total_students == 0:
            QMessageBox.warning(self, "Warning", f"No students found in:\n{file_path}")
            return
        
        # Add each exam (skip duplicates)
        added_count = 0
        skipped = []
        
        for exam in exams:
            # Check for duplicate
            is_duplicate = any(existing.id == exam.id for existing in self.exams)
            if is_duplicate:
                skipped.append(exam.name)
                continue
            
            # Assign color
            exam.color = get_exam_color(len(self.exams))
            self.exams.append(exam)
            added_count += 1
        
        if skipped:
            QMessageBox.information(
                self, 
                "Info", 
                f"Added {added_count} exam(s).\nSkipped duplicates: {', '.join(skipped)}"
            )
        
        self._refresh_list()
        
        if self.on_change:
            self.on_change()
    
    def _remove_exam(self, card: ExamCard):
        """Remove an exam from the list."""
        if card.exam in self.exams:
            self.exams.remove(card.exam)
            self._refresh_list()
            
            if self.on_change:
                self.on_change()
    
    def _refresh_list(self):
        """Refresh the exam list display."""
        # Remove existing cards
        for card in self.exam_cards:
            card.setParent(None)
            card.deleteLater()
        self.exam_cards.clear()
        
        # Show/hide empty state
        self.empty_label.setVisible(len(self.exams) == 0)
        
        # Create new cards
        for i, exam in enumerate(self.exams):
            card = ExamCard(exam=exam, color=get_exam_color(i))
            card.remove_clicked.connect(self._remove_exam)
            self.list_layout.insertWidget(i, card)
            self.exam_cards.append(card)
        
        # Update summary
        total_students = sum(e.student_count() for e in self.exams)
        self.summary_label.setText(f"{len(self.exams)} exams • {total_students} students")
    
    def get_exams(self) -> List[Exam]:
        """Return the list of loaded exams."""
        return self.exams.copy()
    
    def clear_all(self):
        """Clear all exams."""
        self.exams.clear()
        self._refresh_list()
