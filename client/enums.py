from enum import Enum, auto

class ActiveView(Enum):
    """Defines the different primary UI views the player can be in."""
    WORLD_MAP = auto()
    CITY_VIEW = auto()
    # Future views can be added here
    # CAVE_VIEW = auto()
    # ARMY_VIEW = auto()