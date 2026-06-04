"""
Main application window for the Exam Seating Planner.
Modern desktop GUI using PySide6.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStatusBar, QFileDialog, QMessageBox,
    QInputDialog, QProgressBar, QDateEdit
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from PySide6.QtGui import QFont, QIcon
from typing import Dict, List, Tuple
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.exam import Exam
from models.room import Room
from core.seating_engine import SeatingEngine, SeatingPlan
from core.constraint_validator import ConstraintValidator
from core.excel_exporter import ExcelExporter
from core.attendance_exporter import AttendanceExporter
from core.classwise_attendance_exporter import ClassWiseAttendanceExporter
from core.env_exporter import EnvExporter
from gui.theme import COLORS, get_main_stylesheet, get_exam_color
from gui.exam_panel import ExamPanel
from gui.room_panel import RoomPanel
from gui.seating_view import SeatingView


class AttendanceExportThread(QThread):
    """Runs both room-wise and class-wise attendance exports in a background thread."""
    # Emits list of (success, file_path) tuples — one per exporter
    finished = Signal(list)
    progress = Signal(int)

    def __init__(
        self,
        room_exporter: AttendanceExporter,
        class_exporter: ClassWiseAttendanceExporter,
        plan,
        room_path: str,
        class_path: str,
        date_str: str,
    ):
        super().__init__()
        self.room_exporter = room_exporter
        self.class_exporter = class_exporter
        self.plan = plan
        self.room_path = room_path
        self.class_path = class_path
        self.date_str = date_str

    def run(self):
        results: List[Tuple[bool, str]] = []

        # Room-wise (progress 0→50)
        def room_progress(pct: int):
            self.progress.emit(pct // 2)

        ok_room = self.room_exporter.export(
            self.plan, self.room_path, progress_callback=room_progress, date_str=self.date_str
        )
        results.append((ok_room, self.room_path))

        # Class-wise (progress 50→100)
        def class_progress(pct: int):
            self.progress.emit(50 + pct // 2)

        ok_class = self.class_exporter.export(
            self.plan, self.class_path, progress_callback=class_progress, date_str=self.date_str
        )
        results.append((ok_class, self.class_path))

        self.finished.emit(results)


class EnvExportThread(QThread):
    """Runs ENV export in a background thread."""
    finished = Signal(bool, str)
    progress = Signal(int)

    def __init__(self, exporter: EnvExporter, plan, output_path: str, template_path: str, date_str: str):
        super().__init__()
        self.exporter = exporter
        self.plan = plan
        self.output_path = output_path
        self.template_path = template_path
        self.date_str = date_str

    def run(self):
        ok = self.exporter.export(
            self.plan, self.output_path, self.template_path, self.date_str, progress_callback=self.progress.emit
        )
        self.finished.emit(ok, self.output_path)


class SeatingPlanApp(QMainWindow):
    """Main application window."""
    
    APP_TITLE = "🎓 Exam Seating Planner"
    DEFAULT_SIZE = (1400, 800)
    MIN_SIZE = (1100, 600)
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowTitle(self.APP_TITLE)
        self.resize(*self.DEFAULT_SIZE)
        self.setMinimumSize(*self.MIN_SIZE)
        
        # Apply stylesheet
        self.setStyleSheet(get_main_stylesheet())
        
        # Set Application Icon
        icon_path = self._get_resource_path("seatingengine.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            # Also set the application-wide icon
            from PySide6.QtWidgets import QApplication
            if QApplication.instance():
                QApplication.instance().setWindowIcon(QIcon(icon_path))
        
        # Initialize state
        self.seating_plan: SeatingPlan = None
        self.engine = SeatingEngine()
        self.validator = ConstraintValidator()
        self.exporter = ExcelExporter()
        self.attendance_exporter = AttendanceExporter()
        self.classwise_attendance_exporter = ClassWiseAttendanceExporter()
        self.env_exporter = EnvExporter()
        self.attendance_thread = None
        
        # Build UI
        self._setup_ui()
        
        # Center window on screen
        self._center_window()
    
    def _center_window(self):
        """Center the window on screen."""
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def _get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller."""
        if getattr(sys, 'frozen', False):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    
    def _setup_ui(self):
        """Set up the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header bar
        self._create_header(main_layout)
        
        # Main content area
        self._create_main_content(main_layout)
        
        # Status bar
        self._create_status_bar()
    
    def _create_header(self, parent_layout):
        """Create the header bar."""
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        
        # App title
        title = QLabel("🎓 EXAM SEATING PLANNER")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title)
        
        date_label = QLabel("Date:")
        date_label.setFont(QFont("Segoe UI", 11))
        date_label.setStyleSheet(f"color: {COLORS['text_muted']}; margin-left: 16px;")
        header_layout.addWidget(date_label)
        
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setDisplayFormat("dd-MM-yyyy")
        self.date_picker.setFont(QFont("Segoe UI", 11))
        self.date_picker.setStyleSheet(f"""
            QDateEdit {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid {COLORS['border']};
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: transparent;
            }}
            QDateEdit::drop-down:hover {{
                background-color: {COLORS['bg_tertiary']};
            }}
            QDateEdit::down-arrow {{
                image: none;
                width: 6px;
                height: 6px;
                background-color: {COLORS['text_secondary']};
                border-radius: 3px;
            }}
        """)
        
        # Style the calendar popup
        calendar_css = f"""
            QCalendarWidget {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['bg_primary']};
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {COLORS['bg_tertiary']};
                background-color: {COLORS['bg_primary']};
            }}
            QCalendarWidget QToolButton {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_primary']};
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {COLORS['bg_tertiary']};
            }}
            QCalendarWidget QMenu {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_primary']};
                selection-background-color: {COLORS['primary']};
                selection-color: white;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: {COLORS['text_muted']};
            }}
        """
        self.date_picker.calendarWidget().setStyleSheet(calendar_css)
        header_layout.addWidget(self.date_picker)
        
        header_layout.addStretch()
        
        # Reset button
        self.reset_btn = QPushButton("🔄 Reset All")
        self.reset_btn.setFixedSize(120, 40)
        self.reset_btn.setProperty("class", "secondary")
        self.reset_btn.clicked.connect(self._reset_all)
        header_layout.addWidget(self.reset_btn)
        
        # Generate button
        self.generate_btn = QPushButton("⚡ Generate Plan")
        self.generate_btn.setFixedSize(140, 40)
        self.generate_btn.clicked.connect(self._generate_seating)
        header_layout.addWidget(self.generate_btn)
        
        # Export Attendance button
        self.export_attendance_btn = QPushButton("📄 Attendance")
        self.export_attendance_btn.setFixedSize(120, 40)
        self.export_attendance_btn.setProperty("class", "secondary")
        self.export_attendance_btn.setEnabled(False)
        self.export_attendance_btn.clicked.connect(self._export_attendance)
        header_layout.addWidget(self.export_attendance_btn)
        
        # Export button
        self.export_btn = QPushButton("📥 Export Excel")
        self.export_btn.setFixedSize(120, 40)
        self.export_btn.setProperty("class", "secondary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_excel)
        header_layout.addWidget(self.export_btn)
        
        # Export ENV button
        self.export_env_btn = QPushButton("✉️ Generate ENV")
        self.export_env_btn.setFixedSize(130, 40)
        self.export_env_btn.setProperty("class", "secondary")
        self.export_env_btn.setEnabled(False)
        self.export_env_btn.clicked.connect(self._export_env)
        header_layout.addWidget(self.export_env_btn)
        
        parent_layout.addWidget(header)
    
    def _create_main_content(self, parent_layout):
        """Create the main content area with three panels."""
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # Exam panel (left)
        self.exam_panel = ExamPanel(on_change=self._on_data_change)
        self.exam_panel.setMinimumWidth(300)
        content_layout.addWidget(self.exam_panel, 1)
        
        # Room panel (middle)
        self.room_panel = RoomPanel(
            on_change=self._on_data_change,
            get_required_seats=self._get_total_students
        )
        self.room_panel.setMinimumWidth(300)
        content_layout.addWidget(self.room_panel, 1)
        
        # Seating view (right)
        self.seating_view = SeatingView()
        self.seating_view.setMinimumWidth(400)
        content_layout.addWidget(self.seating_view, 2)
        
        parent_layout.addWidget(content, 1)
    
    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_secondary']};
                font-size: 11px;
            }}
        """)
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("✅ Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)
        
        # Stats label (right side)
        self.stats_label = QLabel("Exams: 0 | Rooms: 0 | Students: 0 | Capacity: 0")
        self.status_bar.addPermanentWidget(self.stats_label)
    
    def _get_total_students(self) -> int:
        """Get total number of students across all exams."""
        exams = self.exam_panel.get_exams()
        return sum(e.student_count() for e in exams)
    
    def _reset_all(self):
        """Reset all rooms, exams, and seating plan."""
        self.exam_panel.clear_all()
        self.room_panel.clear_all()
        self.seating_plan = None
        self.seating_view.clear()
        self.export_btn.setEnabled(False)
        self.export_attendance_btn.setEnabled(False)
        self.export_env_btn.setEnabled(False)
        self.status_label.setText("ℹ️ Add exams and rooms to get started")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.stats_label.setText("Exams: 0 | Rooms: 0 | Students: 0 | Capacity: 0")
    
    def _on_data_change(self):
        """Handle changes in exams or rooms."""
        # Update stats
        exams = self.exam_panel.get_exams()
        rooms = self.room_panel.get_rooms()
        
        total_students = sum(e.student_count() for e in exams)
        total_capacity = sum(r.capacity for r in rooms)
        
        self.stats_label.setText(
            f"Exams: {len(exams)} | Rooms: {len(rooms)} | "
            f"Students: {total_students} | Capacity: {total_capacity}"
        )
        
        # Refresh auto-selection if in automatic mode
        self.room_panel.update_auto_selection()
        
        # Update status
        if total_students > total_capacity and total_capacity > 0:
            overflow = total_students - total_capacity
            self.status_label.setText(f"⚠️ Overflow: {overflow} students won't fit")
            self.status_label.setStyleSheet(f"color: {COLORS['warning']};")
        elif len(exams) < 2:
            self.status_label.setText("ℹ️ Add at least 2 exams for anti-cheating arrangement")
            self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        elif len(rooms) == 0:
            self.status_label.setText("ℹ️ Add exam rooms to continue")
            self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        else:
            self.status_label.setText("✅ Ready to generate seating plan")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
        
        # Clear previous seating plan
        self.seating_plan = None
        self.seating_view.clear()
        self.export_btn.setEnabled(False)
        self.export_attendance_btn.setEnabled(False)
        self.export_env_btn.setEnabled(False)
    
    def _generate_seating(self):
        """Generate the seating plan."""
        exams = self.exam_panel.get_exams()
        rooms = self.room_panel.get_rooms()
        
        if len(exams) < 2:
            QMessageBox.warning(
                self,
                "Insufficient Exams",
                "Please add at least 2 exams for anti-cheating arrangement."
            )
            return
        
        if len(rooms) == 0:
            QMessageBox.warning(
                self,
                "No Rooms",
                "Please add at least one exam room."
            )
            return
        
        # Ask for max exam types per room
        max_exams, ok = QInputDialog.getInt(
            self,
            "Exam Limit Per Room",
            "Maximum number of exam types (classes) allowed in each room:",
            2,        # default value
            2,        # minimum
            len(exams) # maximum
        )
        if not ok:
            return
        
        # Update status
        self.status_label.setText("⏳ Generating seating plan...")
        self.status_label.setStyleSheet(f"color: {COLORS['warning']};")
        
        # Build reserve pool: all rooms NOT in the selected set
        all_rooms = self.room_panel.get_all_rooms()
        selected_names = {r.name for r in rooms}
        reserve_rooms = [r for r in all_rooms if r.name not in selected_names]
        
        # Generate seating
        self.seating_plan = self.engine.generate_seating(
            exams, rooms,
            max_exams_per_room=max_exams,
            reserve_rooms=reserve_rooms
        )
        
        if self.seating_plan.success:
            # Validate constraints
            validation = self.validator.validate_seating_plan(self.seating_plan)
            
            if not validation.is_valid:
                self.status_label.setText(f"⚠️ Validation failed: {validation.violation_count()} violations")
                self.status_label.setStyleSheet(f"color: {COLORS['warning']};")
            else:
                self.status_label.setText("✅ Generated valid seating plan!")
                self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            
            # Create color map for exams
            exam_colors: Dict[str, str] = {}
            for i, exam in enumerate(exams):
                exam_colors[exam.id] = get_exam_color(i)
            
            # Display plan
            self.seating_view.display_plan(self.seating_plan, exam_colors)
            
            # Enable export
            self.export_btn.setEnabled(True)
            self.export_attendance_btn.setEnabled(True)
            self.export_env_btn.setEnabled(True)
        else:
            self.status_label.setText(f"❌ {self.seating_plan.message}")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']};")
            QMessageBox.critical(self, "Generation Failed", self.seating_plan.message)
    
    def _export_excel(self):
        """Export seating plan to Excel."""
        if not self.seating_plan or not self.seating_plan.success:
            QMessageBox.warning(self, "No Plan", "Generate a seating plan first.")
            return
        
        # Ask for save location
        from paths import get_output_dir
        date_str = self.date_picker.date().toString("dd-MM-yyyy")
        default_path = os.path.join(get_output_dir(), f"{date_str}_seating_plan.xlsx")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Seating Plan",
            default_path,
            "Excel files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        # Export
        self.status_label.setText("⏳ Exporting to Excel...")
        self.status_label.setStyleSheet(f"color: {COLORS['warning']};")
        
        success = self.exporter.export(self.seating_plan, file_path)
        
        if success:
            self.status_label.setText(f"✅ Exported to {os.path.basename(file_path)}")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            QMessageBox.information(
                self,
                "Export Successful",
                f"Seating plan exported to:\n{file_path}"
            )
        else:
            self.status_label.setText("❌ Export failed")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']};")
            QMessageBox.critical(self, "Export Failed", "Failed to export seating plan.")
    
    def _export_attendance(self):
        """Export both room-wise and class-wise attendance sheets."""
        if not self.seating_plan or not self.seating_plan.success:
            return

        from paths import get_output_dir
        output_dir = get_output_dir()

        # Auto-generate filenames:  DD-MM-YYYY_RoomWise.xlsx / DD-MM-YYYY_ClassWise.xlsx
        date_str = self.date_picker.date().toString("dd-MM-yyyy")
        room_path = os.path.join(output_dir, f"{date_str}_RoomWise.xlsx")
        class_path = os.path.join(output_dir, f"{date_str}_ClassWise.xlsx")

        self.status_label.setText("⏳ Generating attendance sheets...")
        self.status_label.setStyleSheet(f"color: {COLORS['warning']};")

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        # Disable buttons during export
        self.export_attendance_btn.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

        # Start background thread running both exporters sequentially
        self.attendance_thread = AttendanceExportThread(
            self.attendance_exporter,
            self.classwise_attendance_exporter,
            self.seating_plan,
            room_path,
            class_path,
            date_str,
        )
        self.attendance_thread.progress.connect(self.progress_bar.setValue)
        self.attendance_thread.finished.connect(self._on_attendance_exported)
        self.attendance_thread.start()

    def _on_attendance_exported(self, results: list):
        """Handle completion of both attendance sheet exports."""
        self.progress_bar.setVisible(False)

        # Re-enable buttons
        self.export_attendance_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

        # results is [(ok_room, room_path), (ok_class, class_path)]
        ok_room, room_path = results[0]
        ok_class, class_path = results[1]

        failures = []
        if not ok_room:
            failures.append("RoomWise")
        if not ok_class:
            failures.append("ClassWise")

        if not failures:
            self.status_label.setText(
                f"✅ Attendance sheets saved: {os.path.basename(room_path)}, "
                f"{os.path.basename(class_path)}"
            )
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            QMessageBox.information(
                self,
                "Attendance Sheets Generated",
                f"Two attendance sheets saved to:\n"
                f"  • {room_path}\n"
                f"  • {class_path}"
            )
        else:
            self.status_label.setText(f"❌ Export failed for: {', '.join(failures)}")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']};")
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to generate: {', '.join(failures)} attendance sheet(s)."
            )

    def _export_env(self):
        """Export the ENV document using the 13-5-26.docx template."""
        if not self.seating_plan or not self.seating_plan.success:
            return

        template_name = "13-5-26.docx"
        template_path = self._get_resource_path(template_name)
        if not os.path.exists(template_path):
            # Check current working directory
            template_path = os.path.join(os.getcwd(), template_name)
            if not os.path.exists(template_path):
                QMessageBox.critical(self, "Template Missing", f"Could not find template file '{template_name}'.")
                return

        from paths import get_output_dir
        output_dir = get_output_dir()
        date_str = self.date_picker.date().toString("dd-MM-yyyy")
        output_path = os.path.join(output_dir, f"{date_str}_ENV.docx")

        self.status_label.setText("⏳ Generating ENV document...")
        self.status_label.setStyleSheet(f"color: {COLORS['warning']};")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.export_btn.setEnabled(False)
        self.export_attendance_btn.setEnabled(False)
        self.export_env_btn.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

        self.env_thread = EnvExportThread(
            self.env_exporter,
            self.seating_plan,
            output_path,
            template_path,
            date_str
        )
        self.env_thread.progress.connect(self.progress_bar.setValue)
        self.env_thread.finished.connect(self._on_env_exported)
        self.env_thread.start()

    def _on_env_exported(self, ok: bool, path: str):
        self.progress_bar.setVisible(False)
        
        self.export_btn.setEnabled(True)
        self.export_attendance_btn.setEnabled(True)
        self.export_env_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

        if ok:
            self.status_label.setText(f"✅ ENV exported successfully")
            self.status_label.setStyleSheet(f"color: {COLORS['success']};")
            QMessageBox.information(
                self,
                "Export Complete",
                f"ENV document generated successfully at:\n{path}"
            )
        else:
            self.status_label.setText("❌ Export failed")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']};")
            QMessageBox.critical(
                self,
                "Export Failed",
                "Failed to generate ENV document. Check console for details."
            )


def main():
    """Application entry point."""
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = SeatingPlanApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
