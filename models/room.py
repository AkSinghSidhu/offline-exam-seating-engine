"""Room configuration model for the exam seating tool."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class RoomCategory(Enum):
    """Room size categories with predefined dimensions."""
    CUSTOM = "Custom"
    STANDARD = "Standard"
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return (rows, columns) for this category. Only relevant for legacy or fixed types."""
        if self == RoomCategory.CUSTOM:
            return (5, 5)
        return (0, 0)
    
    @property
    def capacity(self) -> int:
        """Return total seat capacity."""
        rows, cols = self.dimensions
        return rows * cols


@dataclass
class Room:
    """Represents an examination room with seating layout."""
    name: str
    category: RoomCategory
    rows: int = 0
    columns: int = 0
    
    def __post_init__(self):
        """Set dimensions based on category if not specified."""
        if self.rows == 0 or self.columns == 0:
            self.rows, self.columns = self.category.dimensions
    
    @property
    def capacity(self) -> int:
        """Return total seat capacity."""
        return self.rows * self.columns
    
    @classmethod
    def create(cls, name: str, category: RoomCategory) -> 'Room':
        """Factory method to create a room with predefined dimensions."""
        return cls(name=name, category=category)
    
    @classmethod
    def create_custom(cls, name: str, rows: int, columns: int) -> 'Room':
        """Create a room with custom dimensions."""
        return cls(name=name, category=RoomCategory.CUSTOM, rows=rows, columns=columns)
    
    def dimensions_text(self) -> str:
        """Return formatted dimensions string."""
        return f"{self.rows} × {self.columns}"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.category.value}: {self.capacity} seats)"
