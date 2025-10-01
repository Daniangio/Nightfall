from enum import Enum, auto

class ResourceType(Enum):
    """Enumeration for resource types."""
    FOOD = auto()
    WOOD = auto()
    IRON = auto()

class BuildingType(Enum):
    """Enumeration for building types."""
    CITADEL = auto()
    FARM = auto()
    LUMBER_MILL = auto()
    IRON_MINE = auto()
    WAREHOUSE = auto()
    BARRACKS = auto()
    WALL = auto()

class TerrainType(Enum):
    """Enumeration for world map tile terrain types."""
    PLAINS = auto()
    FOREST = auto()
    MOUNTAIN = auto()
    LAKE = auto()

class CityTerrainType(Enum):
    """Enumeration for city plot terrain types."""
    GRASS = auto()
    FOREST_PLOT = auto()
    IRON_DEPOSIT = auto()
    WATER = auto()
