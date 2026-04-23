"""
Constraint validation engine for exam seating plans.

Validates that no same-exam students are seated adjacent
horizontally or vertically (diagonals are allowed).
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from core.seating_engine import RoomSeatingPlan, SeatingPlan


@dataclass
class Violation:
    """Represents an adjacency constraint violation."""
    room_name: str
    position1: Tuple[int, int]
    position2: Tuple[int, int]
    exam_id: str
    direction: str  # 'horizontal' or 'vertical'
    
    def __str__(self) -> str:
        return (
            f"{self.room_name}: Same exam '{self.exam_id}' at "
            f"({self.position1[0]}, {self.position1[1]}) and "
            f"({self.position2[0]}, {self.position2[1]}) - {self.direction}"
        )


@dataclass
class ValidationResult:
    """Result of constraint validation."""
    is_valid: bool
    violations: List[Violation] = field(default_factory=list)
    message: str = ""
    
    def add_violation(self, violation: Violation):
        """Add a violation to the result."""
        self.violations.append(violation)
        self.is_valid = False
    
    def violation_count(self) -> int:
        """Return total number of violations."""
        return len(self.violations)


class ConstraintValidator:
    """
    Validates seating plans against anti-cheating constraints.
    
    Rules:
    - Same exam students cannot be adjacent horizontally (left/right)
    - Same exam students cannot be adjacent vertically (up/down)
    - Diagonal adjacency is allowed
    """
    
    def validate_seating_plan(self, plan: SeatingPlan) -> ValidationResult:
        """
        Validate a complete seating plan across all rooms.
        
        Args:
            plan: The seating plan to validate
            
        Returns:
            ValidationResult with any violations found
        """
        result = ValidationResult(is_valid=True)
        
        for room_plan in plan.room_plans:
            room_result = self.validate_room(room_plan)
            for violation in room_result.violations:
                result.add_violation(violation)
        
        if result.is_valid:
            result.message = "All constraints satisfied"
        else:
            result.message = f"Found {result.violation_count()} violations"
        
        return result
    
    def validate_room(self, room_plan: RoomSeatingPlan) -> ValidationResult:
        """
        Validate seating in a single room.
        
        Args:
            room_plan: The room seating plan to validate
            
        Returns:
            ValidationResult with any violations found
        """
        result = ValidationResult(is_valid=True)
        room = room_plan.room
        
        for row in range(room.rows):
            for col in range(room.columns):
                seat = room_plan.get_seat(row, col)
                if not seat or seat.is_empty:
                    continue
                
                # Check right neighbor (horizontal)
                if col < room.columns - 1:
                    right_seat = room_plan.get_seat(row, col + 1)
                    if right_seat and not right_seat.is_empty:
                        if seat.exam_id == right_seat.exam_id:
                            result.add_violation(Violation(
                                room_name=room.name,
                                position1=(row, col),
                                position2=(row, col + 1),
                                exam_id=seat.exam_id,
                                direction="horizontal"
                            ))
                
                # Check bottom neighbor (vertical)
                if row < room.rows - 1:
                    bottom_seat = room_plan.get_seat(row + 1, col)
                    if bottom_seat and not bottom_seat.is_empty:
                        if seat.exam_id == bottom_seat.exam_id:
                            result.add_violation(Violation(
                                room_name=room.name,
                                position1=(row, col),
                                position2=(row + 1, col),
                                exam_id=seat.exam_id,
                                direction="vertical"
                            ))
        
        return result
    
    def get_violation_summary(self, result: ValidationResult) -> str:
        """Get a human-readable summary of violations."""
        if result.is_valid:
            return "✅ No violations found. Seating plan is valid."
        
        lines = [f"❌ Found {result.violation_count()} violations:"]
        for v in result.violations[:10]:  # Show first 10
            lines.append(f"  • {v}")
        
        if result.violation_count() > 10:
            lines.append(f"  ... and {result.violation_count() - 10} more")
        
        return "\n".join(lines)
