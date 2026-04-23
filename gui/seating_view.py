"""Seating plan visualization panel with interactive grid display."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from typing import Dict, Optional
from core.seating_engine import SeatingPlan, RoomSeatingPlan, SeatAssignment
from gui.theme import COLORS, get_exam_color


class SeatCell(QFrame):
    """Individual seat cell in the seating grid."""
    
    def __init__(self, seat: Optional[SeatAssignment], exam_color_map: Dict[str, str], size: int = 70):
        super().__init__()
        self.seat = seat
        self.size = size
        
        # Determine color
        if seat and not seat.is_empty:
            bg_color = exam_color_map.get(seat.exam_id, COLORS["primary"])
        else:
            bg_color = COLORS["empty"]
        
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid white;
            }}
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the cell display."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        
        if self.seat and not self.seat.is_empty and self.seat.student:
            # Roll number
            roll_label = QLabel(self.seat.student.roll_number)
            roll_label.setAlignment(Qt.AlignCenter)
            roll_label.setFont(QFont("Consolas", 7, QFont.Bold))
            roll_label.setStyleSheet("color: white;")
            roll_label.setWordWrap(True)
            layout.addWidget(roll_label)
            
            # Exam ID
            exam_label = QLabel(f"({self.seat.exam_id})")
            exam_label.setAlignment(Qt.AlignCenter)
            exam_label.setStyleSheet("color: #CCCCCC; font-size: 5pt;")
            exam_label.setWordWrap(True)
            layout.addWidget(exam_label)
        else:
            # Empty seat
            empty_label = QLabel("—")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setFont(QFont("Segoe UI", 12))
            empty_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            layout.addWidget(empty_label)


class RoomGridView(QFrame):
    """Grid visualization for a single room."""
    
    def __init__(self, room_plan: RoomSeatingPlan, exam_color_map: Dict[str, str]):
        super().__init__()
        self.room_plan = room_plan
        self.exam_color_map = exam_color_map
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the room grid display."""
        room = self.room_plan.room
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)
        
        # Room header
        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel(f"🏫 {room.name}")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        stats = QLabel(f"{self.room_plan.student_count()}/{room.capacity} seats filled")
        stats.setFont(QFont("Segoe UI", 11))
        stats.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header_layout.addWidget(stats)
        
        main_layout.addWidget(header)
        
        # Grid container
        grid_container = QFrame()
        grid_container.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            border-radius: 8px;
        """)
        grid_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        grid_layout.setSpacing(2)
        grid_layout.setSizeConstraint(QGridLayout.SetFixedSize)
        
        # Calculate cell size (1.5x scale)
        base_size = 105
        if room.columns > 6:
            base_size = 90
        if room.columns > 8:
            base_size = 75
        
        # Column headers
        for col in range(room.columns):
            lbl = QLabel(str(col + 1))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFont(QFont("Segoe UI", 11))
            lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
            lbl.setFixedWidth(base_size)
            grid_layout.addWidget(lbl, 0, col + 1)
        
        # Row headers and cells
        for row in range(room.rows):
            # Row header
            row_lbl = QLabel(str(row + 1))
            row_lbl.setAlignment(Qt.AlignCenter)
            row_lbl.setFont(QFont("Segoe UI", 11))
            row_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
            row_lbl.setFixedWidth(24)
            grid_layout.addWidget(row_lbl, row + 1, 0)
            
            # Seat cells
            for col in range(room.columns):
                seat = self.room_plan.get_seat(row, col)
                cell = SeatCell(seat=seat, exam_color_map=self.exam_color_map, size=base_size)
                grid_layout.addWidget(cell, row + 1, col + 1)
        
        main_layout.addWidget(grid_container)


class SeatingView(QWidget):
    """Main seating visualization panel with room grids."""
    
    def __init__(self):
        super().__init__()
        self.seating_plan: Optional[SeatingPlan] = None
        self.exam_color_map: Dict[str, str] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the panel UI."""
        self.setStyleSheet(f"background-color: {COLORS['bg_secondary']}; border-radius: 10px;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)  # Consistent padding
        main_layout.setSpacing(8)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("SEATING PLAN")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        main_layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QScrollBar:horizontal {{
                height: 10px;
                background: {COLORS['bg_secondary']};
            }}
            QScrollBar:vertical {{
                width: 10px;
                background: {COLORS['bg_secondary']};
            }}
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(10)
        
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll, 1)
        
        # Show empty state
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show the empty state message."""
        self._clear_content()
        
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setContentsMargins(0, 60, 0, 60)
        
        icon = QLabel("📋")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont("Segoe UI Emoji", 48))
        empty_layout.addWidget(icon)
        
        text = QLabel("No seating plan generated yet.\n\nAdd exams and rooms, then click\n'Generate Plan' to create one.")
        text.setAlignment(Qt.AlignCenter)
        text.setFont(QFont("Segoe UI", 12))
        text.setStyleSheet(f"color: {COLORS['text_muted']};")
        empty_layout.addWidget(text)
        
        self.content_layout.addWidget(empty_widget)
        self.content_layout.addStretch()
    
    def _clear_content(self):
        """Clear all content."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def display_plan(self, plan: SeatingPlan, exam_colors: Dict[str, str]):
        """Display the generated seating plan."""
        self.seating_plan = plan
        self.exam_color_map = exam_colors
        
        self._clear_content()
        
        if not plan.success:
            self._show_error(plan.message)
            return
        
        # Legend
        self._show_legend()
        
        # Room grids
        for room_plan in plan.room_plans:
            grid_view = RoomGridView(room_plan=room_plan, exam_color_map=self.exam_color_map)
            self.content_layout.addWidget(grid_view)
        
        # Summary
        self._show_summary()
        
        self.content_layout.addStretch()
    
    def _show_legend(self):
        """Show the exam color legend."""
        legend = QFrame()
        legend.setStyleSheet(f"""
            background-color: {COLORS['bg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
        """)
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(12, 8, 12, 8)
        legend_layout.setSpacing(16)
        
        title = QLabel("Legend:")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_secondary']};")
        legend_layout.addWidget(title)
        
        for exam_id, color in self.exam_color_map.items():
            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(6)
            
            color_box = QFrame()
            color_box.setFixedSize(16, 16)
            color_box.setStyleSheet(f"""
                background-color: {color};
                border-radius: 4px;
            """)
            item_layout.addWidget(color_box)
            
            label = QLabel(exam_id)
            label.setFont(QFont("Segoe UI", 11))
            label.setStyleSheet(f"color: {COLORS['text_primary']};")
            item_layout.addWidget(label)
            
            legend_layout.addWidget(item)
        
        legend_layout.addStretch()
        self.content_layout.addWidget(legend)
    
    def _show_summary(self):
        """Show seating plan summary."""
        if not self.seating_plan:
            return
        
        summary = QFrame()
        summary.setStyleSheet(f"""
            background-color: {COLORS['success']};
            border-radius: 10px;
        """)
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        
        text = QLabel(f"✅ {self.seating_plan.message}")
        text.setFont(QFont("Segoe UI", 12, QFont.Bold))
        text.setStyleSheet("color: white;")
        summary_layout.addWidget(text, 0, Qt.AlignCenter)
        
        self.content_layout.addWidget(summary)
    
    def _show_error(self, message: str):
        """Show error message."""
        error = QFrame()
        error.setStyleSheet(f"""
            background-color: {COLORS['danger']};
            border-radius: 10px;
        """)
        error_layout = QHBoxLayout(error)
        error_layout.setContentsMargins(16, 16, 16, 16)
        
        text = QLabel(f"❌ {message}")
        text.setFont(QFont("Segoe UI", 12, QFont.Bold))
        text.setStyleSheet("color: white;")
        error_layout.addWidget(text, 0, Qt.AlignCenter)
        
        self.content_layout.addWidget(error)
        self.content_layout.addStretch()
    
    def clear(self):
        """Clear the seating view."""
        self.seating_plan = None
        self.exam_color_map = {}
        self._show_empty_state()
