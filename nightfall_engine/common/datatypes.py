from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    """Represents a 2D position on the game map. Frozen for immutability."""
    x: int
    y: int

@dataclass
class Resources:
    """A container for resource stockpiles."""
    food: int = 0
    wood: int = 0
    iron: int = 0

    def __add__(self, other):
        """Allows adding two Resources objects together."""
        if not isinstance(other, Resources):
            return NotImplemented
        return Resources(
            self.food + other.food,
            self.wood + other.wood,
            self.iron + other.iron
        )
    
    def __sub__(self, other):
        """Allows subtracting one Resources object from another."""
        if not isinstance(other, Resources):
            return NotImplemented
        return Resources(
            self.food - other.food,
            self.wood - other.wood,
            self.iron - other.iron
        )

    def can_afford(self, cost: Resources) -> bool:
        """
        Checks if this resource collection is sufficient to cover the given cost.

        Args:
            cost: A Resources object representing the cost to check against.
        """
        return self.food >= cost.food and self.wood >= cost.wood and self.iron >= cost.iron