from dataclasses import dataclass, field
from typing import List

@dataclass
class Player:
    """Represents a player in the game."""
    id: str
    name: str
    city_ids: List[str] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
