from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nightfall.core.common.enums import UnitType

@dataclass
class Resources:
    """Represents a collection of game resources."""
    food: float = 0
    wood: float = 0
    iron: float = 0

    def __add__(self, other: Resources) -> Resources:
        return Resources(
            self.food + other.food,
            self.wood + other.wood,
            self.iron + other.iron
        )

    def __sub__(self, other: Resources) -> Resources:
        return Resources(
            self.food - other.food,
            self.wood - other.wood,
            self.iron - other.iron
        )

    def __mul__(self, scalar: float) -> Resources:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Resources(
            self.food * scalar,
            self.wood * scalar,
            self.iron * scalar
        )

    def can_afford(self, cost: Resources) -> bool:
        """Checks if this resource collection can cover a given cost."""
        if not cost: return True
        return self.food >= cost.food and self.wood >= cost.wood and self.iron >= cost.iron

    def __str__(self):
        return f"F:{int(self.food)}, W:{int(self.wood)}, I:{int(self.iron)}"

@dataclass(frozen=True)
class Position:
    """Represents a 2D coordinate."""
    x: int
    y: int

@dataclass
class RecruitmentProgress:
    """Tracks the progress of recruiting a batch of units."""
    unit_type: UnitType
    quantity: int
    progress: float = 0.0 # Accumulated recruitment points

    def deep_copy(self) -> RecruitmentProgress:
        return RecruitmentProgress(self.unit_type, self.quantity, self.progress)

    def to_dict(self) -> dict:
        return {
            'unit_type': self.unit_type.name,
            'quantity': self.quantity,
            'progress': self.progress
        }

    @classmethod
    def from_dict(cls, data: dict) -> RecruitmentProgress:
        return cls(UnitType[data['unit_type']], data['quantity'], data.get('progress', 0.0))