"""
Deterministic seating engine for exam seating arrangement.

Uses Pre-Plan + Fill Algorithm:
1. PHASE 0: Pre-Plan  - Bin-pack exams into rooms (small groups stay together)
2. PHASE 1: Fill      - Seat students room-by-room using only pre-assigned exams
3. PHASE 2: Backfill Batches
           - Collect leftover students per exam, sort batches descending by size.
           - For each batch: find an existing room with ≥ batch_size empty seats;
             if none available, use the next empty room.
           - A batch is NEVER split across rooms.
4. PHASE 3: Emergency - Relaxed fill if students still remain

This prevents small exam groups from scattering across multiple rooms.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import sys
import os
import math

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.student import Student
from models.exam import Exam
from models.room import Room


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
    Smart seating engine using Pre-Plan + Fill Algorithm.
    
    Phases:
    0. Pre-Plan: Bin-pack exams into rooms so small groups stay together
    1. Fill: Seat students room-by-room using only pre-assigned exams
    2. Pack Gaps: Fill remaining empty seats across all rooms
    3. Emergency: Relaxed fill if students still remain
    """
    
    def generate_seating(self, exams: List[Exam], rooms: List[Room], max_exams_per_room: int = 2,
                         reserve_rooms: Optional[List[Room]] = None) -> SeatingPlan:
        """Generate a complete seating plan for all exams across all rooms.
        
        Args:
            reserve_rooms: Extra rooms NOT in 'rooms' that Phase 2 can pull
                           from when leftover batches don't fit in the primary
                           rooms. Rooms on the same floors as 'rooms' are
                           prioritised.
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
        reserve = reserve_rooms or []
        total_capacity = sum(r.capacity for r in rooms) + sum(r.capacity for r in reserve)
        
        if total_students > total_capacity:
            plan.success = False
            plan.message = f"Insufficient capacity: {total_students} students, {total_capacity} seats"
            return plan
        
        # Sort exams by student count (descending)
        exam_list = sorted(active_exams, key=lambda e: e.student_count(), reverse=True)
        
        # ======================
        # PHASE 0: Pre-Plan Room Assignments
        # ======================
        print(f"   ...Phase 0: Pre-planning room assignments")
        room_exam_map = self._pre_plan(exam_list, rooms, max_exams_per_room)
        
        for room_name, exam_ids in room_exam_map.items():
            print(f"      [{room_name}] <- {', '.join(exam_ids)}")
        
        # Setup student queues
        student_queues: Dict[str, List[Student]] = {
            e.id: list(e.students) for e in active_exams
        }
        
        # ======================
        # PHASE 1: Fill Pre-Planned Rooms
        # ======================
        print(f"   ...Phase 1: Filling pre-planned rooms")
        # Use the room order from pre-plan (rooms with assignments)
        for room in rooms:
            assigned_exam_ids = room_exam_map.get(room.name)
            if not assigned_exam_ids:
                # Add empty room plan so it's available for emergency
                plan.room_plans.append(RoomSeatingPlan(room=room))
                continue
            
            assigned_exams = [e for e in exam_list if e.id in assigned_exam_ids]
            room_plan = self._fill_room(room, assigned_exams, student_queues)
            plan.room_plans.append(room_plan)
        
        # ======================
        # PHASE 2: Backfill Batches (never split a batch across rooms)
        # ======================
        remaining = sum(len(q) for q in student_queues.values())
        if remaining > 0:
            print(f"   ...Phase 2: Backfilling {remaining} leftover students in whole batches")
            self._backfill_batches(plan, exam_list, student_queues,
                                  max_exams_per_room, reserve_rooms or [], rooms)

        # ======================
        # PHASE 3: Emergency
        # ======================
        remaining = sum(len(q) for q in student_queues.values())
        if remaining > 0:
            print(f"   ...Phase 3: Emergency seating for {remaining} students")
            relaxed_cap = len(exam_list)
            self._pack_gaps(plan, exam_list, student_queues, relaxed_cap)
        
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
    
    # ------------------------------------------------------------------
    # PHASE 0: Pre-Plan
    # ------------------------------------------------------------------
    
    def _pre_plan(
        self,
        exam_list: List[Exam],
        rooms: List[Room],
        max_exams_per_room: int
    ) -> Dict[str, List[str]]:
        """
        Bin-pack exams into rooms before any seat placement.
        
        Guarantees:
        - Small exams are assigned to exactly ONE room
        - Large exams may span multiple rooms
        - Each room gets at most max_exams_per_room exam types
        
        Returns:
            Dict mapping room_name -> list of assigned exam IDs
        """
        # Sort rooms by capacity descending (fill biggest rooms first)
        sorted_rooms = sorted(rooms, key=lambda r: r.capacity, reverse=True)
        
        # Track state per room
        # allocated_per_exam tracks how many students of each exam are planned for this room
        room_state: List[Dict] = []
        for room in sorted_rooms:
            room_state.append({
                'room': room,
                'exam_ids': [],                         # exam types assigned
                'allocated_per_exam': {},                # exam_id -> count
                'total_allocated': 0,                    # total students planned
                'per_exam_max': (room.capacity + 1) // 2  # checkerboard limit
            })
        
        # exam_list is already sorted descending by size
        # Process each exam: assign its students to rooms
        for exam in exam_list:
            students_left = exam.student_count()
            
            while students_left > 0:
                best_idx = None
                best_score = None
                
                for i, state in enumerate(room_state):
                    room = state['room']
                    space = room.capacity - state['total_allocated']
                    if space <= 0:
                        continue
                    
                    already_in = exam.id in state['exam_ids']
                    
                    # Check exam-type cap
                    if not already_in and len(state['exam_ids']) >= max_exams_per_room:
                        continue
                    
                    # Check per-exam checkerboard limit
                    current_for_exam = state['allocated_per_exam'].get(exam.id, 0)
                    can_add = state['per_exam_max'] - current_for_exam
                    if can_add <= 0:
                        continue
                    
                    can_place = min(students_left, space, can_add)
                    waste = space - can_place
                    
                    # Scoring (lower is better):
                    # 1. Strongly prefer rooms already containing this exam (keep groups together)
                    # 2. Then prefer best-fit (least wasted space)
                    score = (0 if already_in else 1, waste)
                    
                    if best_score is None or score < best_score:
                        best_score = score
                        best_idx = i
                
                if best_idx is None:
                    break  # No room available; emergency phase will handle
                
                state = room_state[best_idx]
                room = state['room']
                space = room.capacity - state['total_allocated']
                current_for_exam = state['allocated_per_exam'].get(exam.id, 0)
                can_add = state['per_exam_max'] - current_for_exam
                can_place = min(students_left, space, can_add)
                
                state['total_allocated'] += can_place
                state['allocated_per_exam'][exam.id] = current_for_exam + can_place
                if exam.id not in state['exam_ids']:
                    state['exam_ids'].append(exam.id)
                
                students_left -= can_place
        
        # Build result: room_name -> [exam_ids]
        result: Dict[str, List[str]] = {}
        for state in room_state:
            if state['exam_ids']:
                result[state['room'].name] = state['exam_ids']
        
        return result
    
    # ------------------------------------------------------------------
    # PHASE 1: Fill Room
    # ------------------------------------------------------------------
    
    def _fill_room(
        self,
        room: Room,
        room_exams: List[Exam],
        student_queues: Dict[str, List[Student]]
    ) -> RoomSeatingPlan:
        """
        Fill a single room using ONLY the pre-assigned exam types.
        
        Uses column-by-column fill with balanced candidate selection
        (prefer the exam with most students remaining).
        """
        room_plan = RoomSeatingPlan(room=room)
        
        def has_students() -> bool:
            return any(len(student_queues.get(e.id, [])) > 0 for e in room_exams)
        
        if not has_students():
            return room_plan
        
        # Fill column by column, top to bottom
        for col in range(room.columns):
            for row in range(room.rows):
                if not has_students():
                    room_plan.set_seat(row, col, SeatAssignment(row, col, None, "", True))
                    continue
                
                # Build candidates: exams that still have students
                candidates = [e for e in room_exams if len(student_queues.get(e.id, [])) > 0]
                
                # Sort by most students remaining (balanced pairing)
                candidates.sort(key=lambda e: -len(student_queues[e.id]))
                
                # Try to place a candidate respecting adjacency
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
    
    # ------------------------------------------------------------------
    # PHASE 2: Backfill Batches
    # ------------------------------------------------------------------

    def _simulate_placeable(
        self,
        room_plan: RoomSeatingPlan,
        exam_id: str,
        batch_size: int
    ) -> int:
        """
        Dry-run: count how many students of *exam_id* can actually fit in
        *room_plan* respecting adjacency — without modifying any state.

        Simulated placements affect subsequent adjacency checks (cascading),
        so the result mirrors what a real fill would achieve.
        """
        simulated: set = set()          # (row, col) of simulated seats
        count = 0

        for col in range(room_plan.room.columns):
            for row in range(room_plan.room.rows):
                if count >= batch_size:
                    return count

                seat = room_plan.get_seat(row, col)
                if seat is not None and not seat.is_empty:
                    continue

                # Adjacency check — real neighbours + simulated neighbours
                blocked = False
                for r_off, c_off in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nr, nc = row + r_off, col + c_off
                    # Real neighbour
                    neighbor = room_plan.get_seat(nr, nc)
                    if (neighbor and neighbor.student
                            and not neighbor.is_empty
                            and neighbor.exam_id == exam_id):
                        blocked = True
                        break
                    # Simulated neighbour
                    if (nr, nc) in simulated:
                        blocked = True
                        break

                if not blocked:
                    simulated.add((row, col))
                    count += 1

        return count

    def _backfill_batches(
        self,
        plan: SeatingPlan,
        exam_list: List[Exam],
        student_queues: Dict[str, List[Student]],
        max_exams_per_room: int,
        reserve_rooms: List[Room],
        primary_rooms: List[Room]
    ):
        """
        Phase 2: Place leftover students in whole batches — never split.

        When no existing room can hold an entire batch, a fresh room is
        pulled from *reserve_rooms* (rooms on the same floors as the
        selected primary rooms are tried first).  A fresh empty room has
        zero adjacency conflicts, so the batch always fits.

        Algorithm:
        1. Collect leftover batches (exam_id → count), sort descending.
        2. For each batch, simulate placement in every in-plan room.
        3. If a room can hold the ENTIRE batch → place there.
        4. If not → pull a fresh room from the reserve pool, add it to
           the plan, and retry (the empty room will fit the batch).
        5. A batch is NEVER split across rooms.
        """

        def empty_seats(rp: RoomSeatingPlan) -> int:
            return rp.room.capacity - rp.student_count()

        def fill_batch_in_room(rp: RoomSeatingPlan, exam_id: str,
                               queue: List[Student]) -> int:
            """Seat as many students from queue into rp as possible."""
            placed = 0
            for col in range(rp.room.columns):
                for row in range(rp.room.rows):
                    if not queue:
                        return placed
                    seat = rp.get_seat(row, col)
                    if seat is not None and not seat.is_empty:
                        continue
                    if self._can_place_exam(rp, row, col, exam_id):
                        student = queue.pop(0)
                        rp.set_seat(row, col,
                                    SeatAssignment(row, col, student, exam_id))
                        placed += 1
            return placed

        def fill_n_in_room(rp: RoomSeatingPlan, exam_id: str,
                           queue: List[Student], max_n: int) -> int:
            """Seat at most *max_n* students from queue into rp."""
            placed = 0
            for col in range(rp.room.columns):
                for row in range(rp.room.rows):
                    if not queue or placed >= max_n:
                        return placed
                    seat = rp.get_seat(row, col)
                    if seat is not None and not seat.is_empty:
                        continue
                    if self._can_place_exam(rp, row, col, exam_id):
                        student = queue.pop(0)
                        rp.set_seat(row, col,
                                    SeatAssignment(row, col, student, exam_id))
                        placed += 1
            return placed

        SPLIT_MIN = 10  # minimum batch size eligible for splitting

        # --- Build priority-sorted reserve pool ----------------------------
        # Rooms on the same floors as the user's selected rooms come first,
        # then by capacity descending (prefer larger rooms).
        primary_floors = {
            getattr(r, 'floor', 'Other') for r in primary_rooms
        }
        in_plan_names = {rp.room.name for rp in plan.room_plans}
        reserve_pool = sorted(
            [r for r in reserve_rooms if r.name not in in_plan_names],
            key=lambda r: (
                0 if getattr(r, 'floor', 'Other') in primary_floors else 1,
                -r.capacity
            )
        )

        # Build list of (exam_id, count) sorted descending by count
        batches = [
            (eid, len(q)) for eid, q in student_queues.items() if len(q) > 0
        ]
        batches.sort(key=lambda x: -x[1])

        for exam_id, _ in batches:
            while len(student_queues.get(exam_id, [])) > 0:
                batch_size = len(student_queues[exam_id])

                # --- Evaluate every room with empty seats ------------------
                candidates = [
                    rp for rp in plan.room_plans
                    if empty_seats(rp) > 0
                ]

                # Simulate how many each room can actually accept
                room_fits = []
                for rp in candidates:
                    placeable = self._simulate_placeable(rp, exam_id, batch_size)
                    if placeable > 0:
                        room_fits.append((rp, placeable))

                # --- Separate full-fit rooms from partial-fit rooms --------
                full_fits = [(rp, p) for rp, p in room_fits if p >= batch_size]

                if full_fits:
                    # Sorting priority:
                    #  1. Prefer rooms already used (student_count > 0) over
                    #     freshly-added empty reserve rooms.
                    #  2. Among occupied rooms: prefer those WITHOUT this exam
                    #     (fewer adjacency issues).
                    #  3. Fewest empty seats (pack tightly, save space).
                    full_fits.sort(key=lambda t: (
                        0 if t[0].student_count() > 0 else 1,
                        0 if exam_id not in t[0].active_exams else 1,
                        empty_seats(t[0])
                    ))
                    target, placeable = full_fits[0]

                    print(f"      Batch [{exam_id}] ({batch_size} students) → "
                          f"{target.room.name} "
                          f"(can fit {placeable}, {empty_seats(target)} empty) "
                          f"[✓]")
                    fill_batch_in_room(target, exam_id, student_queues[exam_id])

                elif batch_size >= SPLIT_MIN:
                    # --- SPLIT: batch is large, try placing halves in
                    #     existing rooms instead of pulling a reserve room. --
                    half = batch_size // 2

                    # Find rooms that can each hold a half
                    half_fits = [
                        (rp, p) for rp, p in room_fits if p >= half
                    ]

                    if half_fits:
                        # Sort: occupied first, without this exam, fewest seats
                        half_fits.sort(key=lambda t: (
                            0 if t[0].student_count() > 0 else 1,
                            0 if exam_id not in t[0].active_exams else 1,
                            empty_seats(t[0])
                        ))
                        target, placeable = half_fits[0]

                        print(f"      Batch [{exam_id}] ({batch_size} students) "
                              f"split → {target.room.name} "
                              f"(placing {half}, {empty_seats(target)} empty) "
                              f"[½]")
                        fill_n_in_room(target, exam_id,
                                       student_queues[exam_id], half)
                        # While-loop retries with the remaining half
                    elif reserve_pool:
                        # Even halves don't fit — pull reserve room
                        new_room = reserve_pool.pop(0)
                        new_rp = RoomSeatingPlan(room=new_room)
                        plan.room_plans.append(new_rp)
                        print(f"      + Reserve room {new_room.name} "
                              f"({new_room.capacity} seats) added for overflow")
                        continue
                    else:
                        # No reserve rooms, partial placement
                        if room_fits:
                            room_fits.sort(key=lambda t: -t[1])
                            target, placeable = room_fits[0]
                        elif candidates:
                            candidates.sort(key=lambda rp: -empty_seats(rp))
                            target = candidates[0]
                            placeable = self._simulate_placeable(
                                target, exam_id, batch_size)
                        else:
                            break
                        print(f"      Batch [{exam_id}] ({batch_size} students) → "
                              f"{target.room.name} "
                              f"(can fit {placeable}, {empty_seats(target)} empty) "
                              f"[⚠ partial]")
                        fill_batch_in_room(target, exam_id,
                                           student_queues[exam_id])

                elif reserve_pool:
                    # Batch < SPLIT_MIN and no full fit.
                    # Pull a fresh room from the reserve pool.
                    new_room = reserve_pool.pop(0)
                    new_rp = RoomSeatingPlan(room=new_room)
                    plan.room_plans.append(new_rp)
                    print(f"      + Reserve room {new_room.name} "
                          f"({new_room.capacity} seats) added for overflow")
                    continue

                else:
                    # No full-fit room AND no reserve rooms left.
                    if room_fits:
                        room_fits.sort(key=lambda t: -t[1])
                        target, placeable = room_fits[0]
                    elif candidates:
                        candidates.sort(key=lambda rp: -empty_seats(rp))
                        target = candidates[0]
                        placeable = self._simulate_placeable(
                            target, exam_id, batch_size)
                    else:
                        break

                    print(f"      Batch [{exam_id}] ({batch_size} students) → "
                          f"{target.room.name} "
                          f"(can fit {placeable}, {empty_seats(target)} empty) "
                          f"[⚠ partial, no reserve rooms]")
                    fill_batch_in_room(target, exam_id,
                                       student_queues[exam_id])

    # ------------------------------------------------------------------
    # PHASE 3: Emergency
    # ------------------------------------------------------------------

    def _pack_gaps(
        self,
        plan: SeatingPlan,
        exam_list: List[Exam],
        student_queues: Dict[str, List[Student]],
        cap: int
    ):
        """
        Phase 3 Emergency: Fill empty seats in ANY room with remaining students.

        Iterates all rooms and tries to place remaining students
        in empty seats, respecting adjacency and exam-cap constraints.
        No near-full filtering — this is the last-resort pass.
        """
        def has_students() -> bool:
            return any(len(q) > 0 for q in student_queues.values())

        if not has_students():
            return

        for room_plan in plan.room_plans:
            for col in range(room_plan.room.columns):
                for row in range(room_plan.room.rows):
                    seat = room_plan.get_seat(row, col)
                    # Only fill empty/unset seats
                    if seat is not None and not seat.is_empty:
                        continue

                    if not has_students():
                        return

                    # Build candidates respecting room's exam cap
                    candidates = []
                    for exam in exam_list:
                        if len(student_queues.get(exam.id, [])) > 0:
                            if exam.id in room_plan.active_exams or len(room_plan.active_exams) < cap:
                                candidates.append(exam)

                    # Prefer exams already in this room, then by most remaining
                    candidates.sort(
                        key=lambda e: (0 if e.id in room_plan.active_exams else 1, -len(student_queues[e.id]))
                    )

                    for exam in candidates:
                        if self._can_place_exam(room_plan, row, col, exam.id):
                            student = student_queues[exam.id].pop(0)
                            room_plan.set_seat(row, col, SeatAssignment(row, col, student, exam.id))
                            break
    
    # ------------------------------------------------------------------
    # Adjacency Check
    # ------------------------------------------------------------------
    
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
