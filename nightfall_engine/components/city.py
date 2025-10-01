from dataclasses import dataclass, field
from typing import Dict, List, Optional
from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.common.datatypes import Resources, Position
from nightfall_engine.actions.action import Action

@dataclass
class Building:
    """Represents a single building on a city tile."""
    type: BuildingType
    level: int = 1

    def to_dict(self):
        return {'type': self.type.name, 'level': self.level}

    @classmethod
    def from_dict(cls, data):
        return cls(BuildingType[data['type']], data['level'])

@dataclass
class CityTile:
    """Represents a single tile/plot within a city."""
    terrain: CityTerrainType
    position: Position
    building: Optional[Building] = None

    def to_dict(self):
        return {
            'terrain': self.terrain.name,
            'position': self.position.__dict__,
            'building': self.building.to_dict() if self.building else None
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            CityTerrainType[data['terrain']],
            Position(**data['position']),
            Building.from_dict(data['building']) if data.get('building') else None
        )

class CityMap:
    """Represents the grid layout of a city."""
    TERRAIN_MAPPING = {
        'G': CityTerrainType.GRASS,
        'F': CityTerrainType.FOREST_PLOT,
        'I': CityTerrainType.IRON_DEPOSIT,
        'W': CityTerrainType.WATER,
    }

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: List[List[CityTile]] = [[None for _ in range(width)] for _ in range(height)]

    def get_tile(self, x: int, y: int) -> Optional[CityTile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    @classmethod
    def load_from_file(cls, filepath: str):
        """Loads a city layout from a text file."""
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
        
        height = len(lines)
        width = len(lines[0]) if height > 0 else 0
        
        city_map = cls(width, height)
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                terrain = cls.TERRAIN_MAPPING.get(char, CityTerrainType.GRASS)
                city_map.tiles[y][x] = CityTile(terrain, Position(x, y))
        
        return city_map
    
    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'tiles': [[tile.to_dict() for tile in row] for row in self.tiles]
        }
    
    @classmethod
    def from_dict(cls, data):
        city_map = cls(data['width'], data['height'])
        city_map.tiles = [[CityTile.from_dict(t_data) for t_data in row] for row in data['tiles']]
        return city_map


@dataclass
class City:
    """Represents a player-owned city, now with an internal grid."""
    id: str
    name: str
    owner_id: str
    position: Position # Position on the world map
    city_map: CityMap
    resources: Resources = field(default_factory=Resources)
    build_queue: List[Action] = field(default_factory=list)

    def get_total_building_levels(self) -> Dict[BuildingType, int]:
        """Aggregates building levels from across the city map."""
        levels = {}
        for row in self.city_map.tiles:
            for tile in row:
                if tile.building:
                    levels[tile.building.type] = levels.get(tile.building.type, 0) + tile.building.level
        return levels

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'owner_id': self.owner_id,
            'position': self.position.__dict__,
            'city_map': self.city_map.to_dict(),
            'resources': self.resources.__dict__,
            'build_queue': [action.to_dict() for action in self.build_queue]
        }
    
    @classmethod
    def from_dict(cls, data, action_class_map):
        # We need a map of action names to classes to deserialize the queue
        queue = []
        for action_data in data.get('build_queue', []):
            action_class = action_class_map.get(action_data['action_type'])
            if action_class:
                queue.append(action_class.from_dict(action_data))

        return cls(
            id=data['id'],
            name=data['name'],
            owner_id=data['owner_id'],
            position=Position(**data['position']),
            city_map=CityMap.from_dict(data['city_map']),
            resources=Resources(**data['resources']),
            build_queue=queue
        )
