"""Room configuration panel for adding/removing exam rooms."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QCheckBox, QButtonGroup
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
import pandas as pd
import os
import itertools
from typing import List, Optional, Callable, Dict
from models.room import Room, RoomCategory
from gui.theme import COLORS, get_mode_toggle_stylesheet


class RoomSelectionItem(QFrame):
    """A single room row with checkbox for selection."""
    
    toggled = Signal(object, bool)  # room, is_selected
    
    def __init__(self, room: Room, is_selected: bool = False):
        super().__init__()
        self.room = room
        self._is_selected = is_selected
        
        self._setup_ui()
        self._update_appearance()
    
    def _setup_ui(self):
        """Set up the item UI."""
        self.setFixedHeight(44)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self._is_selected)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.checkbox)
        
        # Room name
        self.name_label = QLabel(self.room.name)
        self.name_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(self.name_label, 1)
        
        # Dimensions
        dim_label = QLabel(f"{self.room.rows}×{self.room.columns}")
        dim_label.setFont(QFont("Segoe UI", 11))
        dim_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(dim_label)
        
        # Capacity badge
        capacity_frame = QFrame()
        capacity_frame.setStyleSheet(f"""
            background-color: {COLORS['primary_light']};
            border-radius: 4px;
        """)
        cap_layout = QHBoxLayout(capacity_frame)
        cap_layout.setContentsMargins(8, 2, 8, 2)
        
        cap_label = QLabel(f"{self.room.capacity} seats")
        cap_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        cap_label.setStyleSheet(f"color: {COLORS['primary']};")
        cap_layout.addWidget(cap_label)
        
        layout.addWidget(capacity_frame)
    
    def _on_checkbox_changed(self, state):
        """Handle checkbox state change."""
        self._is_selected = state == Qt.Checked.value
        self._update_appearance()
        self.toggled.emit(self.room, self._is_selected)
    
    def _update_appearance(self):
        """Update visual appearance based on selection state."""
        if self._is_selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_primary']};
                    border: 2px solid {COLORS['primary']};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                }}
            """)
    
    def set_selected(self, selected: bool):
        """Set the selection state."""
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(selected)
        self.checkbox.blockSignals(False)
        self._is_selected = selected
        self._update_appearance()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the checkbox."""
        self.checkbox.setEnabled(enabled)
        if not enabled:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                }}
            """)
        else:
            self._update_appearance()
    
    def is_selected(self) -> bool:
        return self._is_selected


class RoomPanel(QWidget):
    """Panel for managing exam rooms with manual or automatic selection."""
    
    rooms_changed = Signal()
    
    def __init__(self, on_change: Optional[Callable] = None, get_required_seats: Optional[Callable[[], int]] = None):
        super().__init__()
        self.rooms: List[Room] = []  # Manually selected rooms
        self.available_rooms: List[Room] = []
        self.selection_items: Dict[str, RoomSelectionItem] = {}
        self.on_change = on_change
        self.get_required_seats = get_required_seats
        self.selection_mode = "manual"
        
        self.floor_checkboxes: Dict[str, QCheckBox] = {}  # floor -> checkbox
        self.floor_rooms: Dict[str, List[str]] = {}  # floor -> list of room names
        
        self.load_rooms_from_excel()
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
        
        title = QLabel("ROOMS")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        main_layout.addWidget(header)
        
        # Mode toggle
        mode_frame = QFrame()
        mode_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_tertiary']};
            border-radius: 8px;
        """)
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(12, 8, 12, 8)
        mode_layout.setSpacing(8)
        
        mode_label = QLabel("Selection Mode:")
        mode_label.setFont(QFont("Segoe UI", 11))
        mode_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        mode_layout.addWidget(mode_label)
        
        self.manual_btn = QPushButton("Manual")
        self.manual_btn.setCheckable(True)
        self.manual_btn.setChecked(True)
        self.manual_btn.clicked.connect(lambda: self._set_mode("manual"))
        mode_layout.addWidget(self.manual_btn)
        
        self.auto_btn = QPushButton("Automatic")
        self.auto_btn.setCheckable(True)
        self.auto_btn.clicked.connect(lambda: self._set_mode("automatic"))
        mode_layout.addWidget(self.auto_btn)
        
        mode_layout.addStretch()
        main_layout.addWidget(mode_frame)
        
        self._update_mode_buttons()
        
        # Scroll area for room list
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
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()
        
        scroll.setWidget(self.list_widget)
        main_layout.addWidget(scroll, 1)
        
        # Populate room list
        self._populate_room_list()
        
        # Summary
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_tertiary']};
            border-radius: 6px;
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(12, 8, 12, 8)
        
        self.capacity_label = QLabel("0 rooms • 0 seats")
        self.capacity_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.capacity_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        summary_layout.addWidget(self.capacity_label, 0, Qt.AlignCenter)
        
        main_layout.addWidget(self.summary_frame)
        
        self._update_capacity()
    
    def _update_mode_buttons(self):
        """Update the appearance of mode buttons."""
        self.manual_btn.setStyleSheet(get_mode_toggle_stylesheet(self.selection_mode == "manual"))
        self.auto_btn.setStyleSheet(get_mode_toggle_stylesheet(self.selection_mode == "automatic"))
        self.manual_btn.setChecked(self.selection_mode == "manual")
        self.auto_btn.setChecked(self.selection_mode == "automatic")
    
    def _set_mode(self, mode: str):
        """Set the selection mode."""
        self.selection_mode = mode
        self._update_mode_buttons()
        
        is_manual = mode == "manual"
        
        for item in self.selection_items.values():
            item.set_enabled(is_manual)
        
        if not is_manual:
            # Auto-select rooms and show them
            auto_rooms = self._auto_select_rooms()
            for name, item in self.selection_items.items():
                is_auto_selected = any(r.name == name for r in auto_rooms)
                item.set_selected(is_auto_selected)
            total = sum(r.capacity for r in auto_rooms)
            self.capacity_label.setText(f"{len(auto_rooms)} rooms (auto) • {total} seats")
        else:
            self._update_capacity()
        
        if self.on_change:
            self.on_change()
    
    def _populate_room_list(self):
        """Populate the room selection list grouped by floor with floor checkboxes."""
        # Clear existing items
        for item in self.selection_items.values():
            item.setParent(None)
            item.deleteLater()
        self.selection_items.clear()
        self.floor_checkboxes.clear()
        self.floor_rooms.clear()
        
        # Also clear any existing floor header widgets
        while self.list_layout.count() > 1:  # Keep the stretch at the end
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                child.widget().deleteLater()
        
        if not self.available_rooms:
            empty_label = QLabel("No rooms found.\nPlace room_detail.xlsx in app folder.")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setFont(QFont("Segoe UI", 12))
            empty_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.list_layout.insertWidget(0, empty_label)
            return
        
        def get_floor(r):
            return getattr(r, 'floor', 'Other')
        
        sorted_rooms = sorted(self.available_rooms, key=lambda r: (get_floor(r), r.name))
        
        idx = 0
        for floor, group in itertools.groupby(sorted_rooms, key=get_floor):
            # Floor header with checkbox
            floor_frame = QFrame()
            floor_frame.setStyleSheet(f"""
                background-color: {COLORS['bg_tertiary']};
                border-radius: 4px;
            """)
            floor_layout = QHBoxLayout(floor_frame)
            floor_layout.setContentsMargins(6, 6, 6, 6)
            floor_layout.setSpacing(8)
            
            floor_cb = QCheckBox()
            floor_cb.setChecked(False)
            floor_cb.stateChanged.connect(lambda state, f=floor: self._on_floor_toggle(f, state == Qt.Checked.value))
            floor_layout.addWidget(floor_cb)
            self.floor_checkboxes[floor] = floor_cb
            
            floor_label = QLabel(f"{floor}")
            floor_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
            floor_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
            floor_layout.addWidget(floor_label, 1)
            
            self.list_layout.insertWidget(idx, floor_frame)
            idx += 1
            
            # Track rooms per floor
            self.floor_rooms[floor] = []
            
            # Room items
            for room in group:
                is_selected = any(r.name == room.name for r in self.rooms)
                item = RoomSelectionItem(room=room, is_selected=is_selected)
                item.toggled.connect(self._on_room_toggle)
                self.list_layout.insertWidget(idx, item)
                self.selection_items[room.name] = item
                self.floor_rooms[floor].append(room.name)
                idx += 1
    
    def _on_floor_toggle(self, floor: str, checked: bool):
        """Handle floor checkbox toggle — select/deselect all rooms on a floor."""
        room_names = self.floor_rooms.get(floor, [])
        
        if self.selection_mode == "manual":
            # In manual mode: select/deselect all rooms on this floor
            for name in room_names:
                item = self.selection_items.get(name)
                if item:
                    item.set_selected(checked)
                    # Update internal rooms list
                    existing = next((r for r in self.rooms if r.name == name), None)
                    if checked and not existing:
                        self.rooms.append(item.room)
                    elif not checked and existing:
                        self.rooms.remove(existing)
            
            self._update_capacity()
        else:
            # In automatic mode: re-run auto-selection with floor filter
            auto_rooms = self._auto_select_rooms()
            for name, item in self.selection_items.items():
                is_auto_selected = any(r.name == name for r in auto_rooms)
                item.set_selected(is_auto_selected)
            total = sum(r.capacity for r in auto_rooms)
            self.capacity_label.setText(f"{len(auto_rooms)} rooms (auto) • {total} seats")
        
        if self.on_change:
            self.on_change()
    
    def _on_room_toggle(self, room: Room, selected: bool):
        """Handle room selection toggle."""
        existing = next((r for r in self.rooms if r.name == room.name), None)
        
        if selected and not existing:
            self.rooms.append(room)
        elif not selected and existing:
            self.rooms.remove(existing)
        
        self._update_capacity()
        
        if self.on_change:
            self.on_change()
    
    def _update_capacity(self):
        """Update the capacity summary."""
        total = sum(r.capacity for r in self.rooms)
        count = len(self.rooms)
        self.capacity_label.setText(f"{count} rooms • {total} seats")
    
    def load_rooms_from_excel(self):
        """Load rooms from data/rooms/ folder."""
        try:
            from paths import get_rooms_dir
            rooms_dir = get_rooms_dir()
            
            # Look for room_detail.xlsx first, then any .xlsx file
            path = os.path.join(rooms_dir, "room_detail.xlsx")
            if not os.path.exists(path):
                # Try to find any xlsx file in the rooms directory
                xlsx_files = [f for f in os.listdir(rooms_dir) if f.endswith('.xlsx')]
                if xlsx_files:
                    path = os.path.join(rooms_dir, xlsx_files[0])
                else:
                    return
            
            df = pd.read_excel(path)
            if {'Room', 'Row', 'Col'}.issubset(df.columns):
                self.available_rooms.clear()
                for _, row in df.iterrows():
                    name = str(row['Room'])
                    try:
                        r = int(row['Row'])
                        c = int(row['Col'])
                        floor = str(row['Floor']) if 'Floor' in df.columns else "Other"
                        
                        room = Room.create_custom(name, r, c)
                        room.category = RoomCategory.STANDARD
                        setattr(room, 'floor', floor)
                        self.available_rooms.append(room)
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Error loading rooms: {e}")
    
    def get_rooms(self) -> List[Room]:
        """Return the list of selected rooms."""
        if self.selection_mode == "automatic":
            return self._auto_select_rooms()
        return self.rooms.copy()
    
    def get_all_rooms(self) -> List[Room]:
        """Return ALL available rooms from the database (the full pool)."""
        return self.available_rooms.copy()
    
    def _auto_select_rooms(self) -> List[Room]:
        """Automatically select optimal rooms to fit all students.
        
        Only considers rooms from floors that have their checkbox checked.
        If no floors are checked, considers all available rooms.
        """
        required_seats = 0
        if self.get_required_seats:
            required_seats = self.get_required_seats()
        
        if required_seats <= 0:
            return []
        
        # Determine which floors are checked
        checked_floors = {
            floor for floor, cb in self.floor_checkboxes.items() if cb.isChecked()
        }
        
        # Filter available rooms by checked floors (if any are checked)
        if checked_floors:
            pool = [r for r in self.available_rooms if getattr(r, 'floor', 'Other') in checked_floors]
        else:
            pool = list(self.available_rooms)
        
        # Sort by capacity descending (prefer fewer large rooms)
        available = sorted(pool, key=lambda r: r.capacity, reverse=True)
        
        selected = []
        remaining = required_seats
        
        for room in available:
            if remaining <= 0:
                break
            selected.append(room)
            remaining -= room.capacity
        
        return selected
    
    def update_auto_selection(self):
        """Refresh auto-selection display when student count changes."""
        if self.selection_mode == "automatic":
            auto_rooms = self._auto_select_rooms()
            for name, item in self.selection_items.items():
                is_auto_selected = any(r.name == name for r in auto_rooms)
                item.set_selected(is_auto_selected)
            total = sum(r.capacity for r in auto_rooms)
            self.capacity_label.setText(f"{len(auto_rooms)} rooms (auto) • {total} seats")
    
    def clear_all(self):
        """Clear all selected rooms."""
        self.rooms.clear()
        for item in self.selection_items.values():
            item.set_selected(False)
        self._update_capacity()
