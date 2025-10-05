from typing import Optional
from nightfall.core.common.enums import TerrainType
from nightfall.core.common.datatypes import Position

class Tile:
    """Represents a single tile on the game map."""
    def __init__(self, terrain: TerrainType, position: Position):
        self.terrain = terrain
        self.position = position
        # Future additions: city_id, army_id, special_resource, etc.

    def to_dict(self):
        return {'terrain': self.terrain.name, 'position': self.position.__dict__}

    @classmethod
    def from_dict(cls, data):
        return cls(
            TerrainType[data['terrain']],
            Position(**data['position'])
        )

class GameMap:
    """Represents the game world grid."""
    TERRAIN_MAPPING = {
        ' ': TerrainType.EMPTY,
        'P': TerrainType.PLAINS,
        'F': TerrainType.FOREST,
        'M': TerrainType.MOUNTAIN,
        'L': TerrainType.LAKE,
    }

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles = [[None for _ in range(width)] for _ in range(height)]

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    @classmethod
    def load_from_file(cls, filepath: str):
        """Loads a map layout from a text file, allowing for blank spaces."""
        with open(filepath, 'r') as f:
            # rstrip to remove newline but keep other whitespace
            lines = [line.rstrip('\n') for line in f.readlines()]
        
        height = len(lines)
        width = max(len(line) for line in lines) if height > 0 else 0
        
        game_map = cls(width, height)
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                terrain = cls.TERRAIN_MAPPING.get(char, TerrainType.EMPTY)
                game_map.tiles[y][x] = Tile(terrain, Position(x, y))
        print(f"Loaded map of size {width}x{height} from {filepath}")
        return game_map

    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'tiles': [[tile.to_dict() if tile else {} for tile in row] for row in self.tiles]
        }

    @classmethod
    def from_dict(cls, data):
        game_map = cls(data['width'], data['height'])
        game_map.tiles = [[Tile.from_dict(tile_data) for tile_data in row] for row in data.get('tiles', [])]
        return game_map
