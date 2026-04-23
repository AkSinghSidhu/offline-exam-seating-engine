"""
Deterministic seating engine for exam seating arrangement.

Uses Forward Fill + Eviction Protocol Algorithm:
1. PHASE 1: Forward Fill - Fill rooms with limited exams per room
2. PHASE 2: Evict Underutilised - Remove rooms with >= 40% empty seats
3. PHASE 3: Forward Fill Again - Re-run forward fill on evicted students (start to end)
4. PHASE 4: Emergency Room - Create new room if students still remain

This prevents underutilised rooms with too many empty seats.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.student import Student
from models.exam import Exam
from models.room import Room


# ============================================================================
# CONFIGURATION
# ============================================================================

UNDERUTILISATION_THRESHOLD = 0.4  # If a room has >= 40% empty seats, evict it


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SeatAssignment:
    """Represents a single seat assignment in the seating plan."""
    row: int
    column: int
    student: Optional[Student]
    exam_id: str
    is_empty: bool = False
    
    def display_text(self) -> str:
        """Return display text for this seat."""
        if self.is_empty:
            return "—"
        if self.student:
            return f"{self.student.roll_number}"
        return self.exam_id
    
    def full_display(self) -> str:
        """Return full display with exam info."""
        if self.is_empty:
            return "Empty"
        if self.student:
            return f"{self.student.roll_number} ({self.exam_id})"
        return f"({self.exam_id})"


@dataclass
class RoomSeatingPlan:
    """Seating plan for a single room."""
    room: Room
    grid: List[List[Optional[SeatAssignment]]] = field(default_factory=list)
    active_exams: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize empty grid if not provided."""
        if not self.grid:
            self.grid = [
                [None for _ in range(self.room.columns)]
                for _ in range(self.room.rows)
            ]
    
    def get_seat(self, row: int, col: int) -> Optional[SeatAssignment]:
        """Get seat assignment at position."""
        if 0 <= row < self.room.rows and 0 <= col < self.room.columns:
            return self.grid[row][col]
        return None
    
    def set_seat(self, row: int, col: int, assignment: SeatAssignment):
        """Set seat assignment at position."""
        if 0 <= row < self.room.rows and 0 <= col < self.room.columns:
            self.grid[row][col] = assignment
            if assignment.student:
                self.active_exams.add(assignment.exam_id)
    
    def student_count(self) -> int:
        """Count non-empty seats."""
        return sum(1 for row in self.grid for seat in row 
                   if seat and seat.student and not seat.is_empty)
    
    def clear(self):
        """Removes all students from this room."""
        self.grid = [[None for _ in range(self.room.columns)] for _ in range(self.room.rows)]
        self.active_exams = set()
    
    def get_exam_counts(self) -> Dict[str, int]:
        """Return count of students per exam."""
        counts: Dict[str, int] = {}
        for row in self.grid:
            for seat in row:
                if seat and not seat.is_empty and seat.student:
                    counts[seat.exam_id] = counts.get(seat.exam_id, 0) + 1
        return counts


@dataclass
class SeatingPlan:
    """Complete seating plan across all rooms."""
    room_plans: List[RoomSeatingPlan] = field(default_factory=list)
    success: bool = True
    message: str = ""
    
    def total_students_seated(self) -> int:
        """Return total students seated across all rooms."""
        return sum(rp.student_count() for rp in self.room_plans)
    
    def get_room_plan(self, room_name: str) -> Optional[RoomSeatingPlan]:
        """Get seating plan for a specific room."""
        for rp in self.room_plans:
            if rp.room.name == room_name:
                return rp
        return None
    
    def filter_empty_plans(self):
        """Remove room plans with no students."""
        self.room_plans = [rp for rp in self.room_plans if rp.student_count() > 0]


# ============================================================================
# SEATING ENGINE
# ============================================================================

class SeatingEngine:
    """
    Smart seating engine using Forward Fill + Eviction Protocol Algorithm.
    
    Phases:
    1. Forward Fill: Fill rooms with limited exams (MAX_EXAMS_FORWARD)
    2. Evict Underutilised: Remove rooms with >= 40% empty seats
    3. Forward Fill Again: Re-run forward fill on evicted students (start to end)
    4. Emergency: Create new room if students still remain
    """
    
    def generate_seating(self, exams: List[Exam], rooms: List[Room], max_exams_per_room: int = 2) -> SeatingPlan:
        """Generate a complete seating plan for all exams across all rooms.
        
        Args:
            exams: List of exams with students
            rooms: List of available rooms
            max_exams_per_room: Maximum number of different exam types allowed in each room
        """
        plan = SeatingPlan()
        
        if not exams or not rooms:
            plan.success = False
            plan.message = "No exams or rooms provided"
            return plan
        
        # Filter out exams with no students
        active_exams = [e for e in exams if e.student_count() > 0]
        if not active_exams:
            plan.success = False
            plan.message = "No students in any exam"
            return plan
        
        if len(active_exams) == 1:
            plan.success = False
            plan.message = "At least 2 exams required for anti-cheating arrangement"
            return plan
        
        total_students = sum(e.student_count() for e in active_exams)
        total_capacity = sum(r.capacity for r in rooms)
        
        if total_students > total_capacity:
            plan.success = False
            plan.message = f"Insufficient capacity: {total_students} students, {total_capacity} seats"
            return plan
        
        # Setup student queues
        student_queues: Dict[str, List[Student]] = {
            e.id: list(e.students) for e in active_exams
        }
        
        # Sort exams by student count (descending)
        exam_list = sorted(active_exams, key=lambda e: e.student_count(), reverse=True)
        
        # ======================
        # PHASE 1: Forward Fill
        # ======================
        print(f"   ...Phase 1: Forward Fill (max {max_exams_per_room} exams/room)")
        for room in rooms:
            room_plan = self._generate_room_seating(room, exam_list, student_queues, cap=max_exams_per_room)
            plan.room_plans.append(room_plan)
        
        # ======================
        # PHASE 2: Evict Underutilised Rooms
        # ======================
        self._evict_underutilised(plan, student_queues)
        
        # ======================
        # PHASE 3: Forward Fill Again
        # ======================
        remaining = sum(len(q) for q in student_queues.values())
        if remaining > 0:
            # Sort evicted students by roll number (ascending) within each class
            for exam_id in student_queues:
                student_queues[exam_id].sort(key=lambda s: s.roll_number)
            print(f"   ...Phase 3: Forward Fill Again for {remaining} evicted students (sorted by UID)")
            self._forward_fill_evicted(plan, exam_list, student_queues, cap=max_exams_per_room)
        
        # ======================
        # PHASE 4: Emergency Room
        # ======================
        remaining_after_backfill = sum(len(q) for q in student_queues.values())
        if remaining_after_backfill > 0:
            print(f"   ...Phase 4: Emergency seating for {remaining_after_backfill} students")
            
            # First try: find any truly unused rooms and add them
            used_room_names = {rp.room.name for rp in plan.room_plans}
            unused_rooms = [r for r in rooms if r.name not in used_room_names]
            
            for new_room in unused_rooms:
                still_remaining = sum(len(q) for q in student_queues.values())
                if still_remaining == 0:
                    break
                print(f"      [Emergency] Adding {new_room.name} for {still_remaining} remaining students")
                new_plan = self._generate_room_seating(new_room, exam_list, student_queues, cap=max_exams_per_room)
                plan.room_plans.append(new_plan)
            
            # Second try: relaxed forward fill across all rooms with higher cap
            still_remaining = sum(len(q) for q in student_queues.values())
            if still_remaining > 0:
                relaxed_cap = len(exam_list)  # Allow all exam types
                print(f"      [Emergency] Relaxed forward fill for {still_remaining} students (cap raised to {relaxed_cap})")
                self._forward_fill_evicted(plan, exam_list, student_queues, cap=relaxed_cap)
        
        # Filter out empty room plans
        plan.filter_empty_plans()
        
        # Check final result
        final_remaining = sum(len(q) for q in student_queues.values())
        seated_count = plan.total_students_seated()
        
        if final_remaining > 0:
            plan.success = False
            plan.message = f"{final_remaining} students could not be seated."
        else:
            plan.success = True
            plan.message = f"Successfully seated {seated_count} students in {len(plan.room_plans)} room(s)"
        
        return plan
    
    def _evict_underutilised(self, plan: SeatingPlan, student_queues: Dict[str, List[Student]]):
        """Pull students from rooms with >= 40% empty seats back into queue."""
        evicted_count = 0
        evicted_rooms = 0
        
        for rp in plan.room_plans:
            count = rp.student_count()
            capacity = rp.room.capacity
            if capacity == 0 or count == 0:
                continue
            
            empty_ratio = 1.0 - (count / capacity)
            
            # If room has >= 40% empty seats, pull students out
            if empty_ratio >= UNDERUTILISATION_THRESHOLD:
                utilisation_pct = (1.0 - empty_ratio) * 100
                print(f"      [Pulling from {rp.room.name}] - {count}/{capacity} seats filled ({utilisation_pct:.0f}% utilisation)")
                
                # Extract students and return to queue (at front for priority)
                for r in range(rp.room.rows):
                    for c in range(rp.room.columns):
                        seat = rp.get_seat(r, c)
                        if seat and seat.student:
                            student_queues[seat.exam_id].insert(0, seat.student)
                            evicted_count += 1
                
                # Clear the room grid (room stays in plan for forward fill)
                rp.clear()
                evicted_rooms += 1
        
        if evicted_count > 0:
            print(f"      -> Pulled {evicted_count} students from {evicted_rooms} underutilised room(s) back to queue.")
    
    def _generate_room_seating(
        self,
        room: Room,
        exam_list: List[Exam],
        student_queues: Dict[str, List[Student]],
        cap: int
    ) -> RoomSeatingPlan:
        """Generate seating for a single room using snake pattern and priority selection."""
        room_plan = RoomSeatingPlan(room=room)
        
        def has_students() -> bool:
            return any(len(q) > 0 for q in student_queues.values())
        
        # Fill column by column, always top to bottom
        for col in range(room.columns):
            for row in range(room.rows):
                if not has_students():
                    room_plan.set_seat(row, col, SeatAssignment(row, col, None, "", True))
                    continue
                
                # Build candidate list (prioritize exams already in room, within cap)
                candidates = []
                for exam in exam_list:
                    if len(student_queues.get(exam.id, [])) > 0:
                        # Only consider if already in room OR under cap
                        if exam.id in room_plan.active_exams or len(room_plan.active_exams) < cap:
                            candidates.append(exam)
                
                # Sort candidates based on whether room has reached exam cap
                if len(room_plan.active_exams) < cap:
                    # Under cap: prefer NEW exams to diversify the room up to the cap
                    candidates.sort(
                        key=lambda e: (e.id in room_plan.active_exams, -len(student_queues[e.id]))
                    )
                else:
                    # At cap: prefer exams already in room, then by remaining count
                    candidates.sort(
                        key=lambda e: (e.id in room_plan.active_exams, len(student_queues[e.id])),
                        reverse=True
                    )
                
                # Try to place a candidate
                placed = False
                for exam in candidates:
                    if self._can_place_exam(room_plan, row, col, exam.id):
                        student = student_queues[exam.id].pop(0)
                        room_plan.set_seat(row, col, SeatAssignment(row, col, student, exam.id))
                        placed = True
                        break
                
                if not placed:
                    room_plan.set_seat(row, col, SeatAssignment(row, col, None, "", True))
        
        return room_plan
    
    def _forward_fill_evicted(
        self,
        plan: SeatingPlan,
        exam_list: List[Exam],
        student_queues: Dict[str, List[Student]],
        cap: int
    ):
        """
        Re-run forward fill on evicted students from start to end.
        
        Uses the same candidate selection and placement logic as
        _generate_room_seating, but only fills empty seats in existing rooms.
        Iterates rooms from first to last (forward direction).
        """
        def has_students() -> bool:
            return any(len(q) > 0 for q in student_queues.values())
        
        if not has_students():
            return
        
        # Forward fill: iterate rooms from start to end
        for room_plan in plan.room_plans:
            # Fill column by column, always top to bottom
            for col in range(room_plan.room.columns):
                for row in range(room_plan.room.rows):
                    seat = room_plan.get_seat(row, col)
                    # Fill empty seats (None from cleared rooms, or is_empty from forward fill)
                    if seat is not None and not seat.is_empty:
                        continue  # seat is occupied, skip
                    
                    if not has_students():
                        return
                    
                    # Build candidate list (same logic as forward fill)
                    candidates = []
                    for exam in exam_list:
                        if len(student_queues.get(exam.id, [])) > 0:
                            # Only consider if already in room OR under cap
                            if exam.id in room_plan.active_exams or len(room_plan.active_exams) < cap:
                                candidates.append(exam)
                    
                    # Sort candidates based on whether room has reached exam cap
                    if len(room_plan.active_exams) < cap:
                        # Under cap: prefer NEW exams to diversify
                        candidates.sort(
                            key=lambda e: (e.id in room_plan.active_exams, -len(student_queues[e.id]))
                        )
                    else:
                        # At cap: prefer exams already in room
                        candidates.sort(
                            key=lambda e: (e.id in room_plan.active_exams, len(student_queues[e.id])),
                            reverse=True
                        )
                    
                    # Try to place a candidate
                    for exam in candidates:
                        if self._can_place_exam(room_plan, row, col, exam.id):
                            student = student_queues[exam.id].pop(0)
                            room_plan.set_seat(row, col, SeatAssignment(row, col, student, exam.id))
                            # Crucial: if this is a new exam, add it to active_exams so cap tracking works
                            if exam.id not in room_plan.active_exams:
                                room_plan.active_exams.add(exam.id)
                            break
    
    def _can_place_exam(
        self,
        room_plan: RoomSeatingPlan,
        row: int,
        col: int,
        exam_id: str
    ) -> bool:
        """Check if placing an exam at position would violate adjacency rules."""
        # Check all four directions: left, right, up, down
        for r_off, c_off in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            neighbor = room_plan.get_seat(row + r_off, col + c_off)
            if neighbor and neighbor.student and not neighbor.is_empty and neighbor.exam_id == exam_id:
                return False
        return True
