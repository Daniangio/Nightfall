from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from nightfall.core.actions.action import Action
from nightfall.core.common.datatypes import Position, Resources, RecruitmentProgress
from nightfall.core.common.enums import BuildingType, CityTerrainType, UnitType
from nightfall.core.common.game_data import BUILDING_DATA

@dataclass
class Building:
    """Represents a single building on a city tile."""
    type: BuildingType
    level: int = 1

    def deep_copy(self) -> Building:
        return Building(self.type, self.level)

    def to_dict(self) -> dict:
        return {'type': self.type.name, 'level': self.level}

    @classmethod
    def from_dict(cls, data: dict) -> Building:
        return cls(BuildingType[data['type']], data['level'])

@dataclass
class CityTile:
    """Represents a single tile within a city's grid."""
    terrain: CityTerrainType
    position: Position
    building: Optional[Building] = None

    def deep_copy(self) -> CityTile:
        return CityTile(
            terrain=self.terrain,
            position=self.position,
            building=self.building.deep_copy() if self.building else None
        )

    def to_dict(self) -> dict:
        return {
            'terrain': self.terrain.name,
            'position': self.position.__dict__,
            'building': self.building.to_dict() if self.building else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> CityTile:
        return cls(
            CityTerrainType[data['terrain']],
            Position(**data['position']),
            Building.from_dict(data['building']) if data.get('building') else None
        )

class CityMap:
    """Represents the grid of tiles within a city."""
    TERRAIN_MAPPING = {
        'G': CityTerrainType.GRASS,
        'F': CityTerrainType.FOREST_PLOT,
        'I': CityTerrainType.IRON_DEPOSIT,
        'W': CityTerrainType.WATER,
    }

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        # First, create the grid with default grass tiles
        self.tiles: List[List[CityTile]] = [
            [CityTile(terrain=CityTerrainType.EMPTY, position=Position(x, y)) for y in range(height)]
            for x in range(width)
        ]

    def get_tile(self, x: int, y: int) -> Optional[CityTile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[x][y]
        return None

    def deep_copy(self) -> CityMap:
        new_map = CityMap(self.width, self.height)
        new_map.tiles = [[tile.deep_copy() for tile in row] for row in self.tiles]
        return new_map

    @classmethod
    def load_from_file(cls, filepath: str) -> 'CityMap':
        """Loads a city map layout from a JSON file."""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)

        layout_lines = data['layout']
        initial_buildings = data.get('initial_buildings', [])
        
        height = len(layout_lines)
        width = max(len(line) for line in layout_lines) if height > 0 else 0
        
        city_map = cls(width, height)
        for y, line in enumerate(layout_lines):
            for x, char in enumerate(line):
                terrain = cls.TERRAIN_MAPPING.get(char, CityTerrainType.EMPTY)
                city_map.get_tile(x, y).terrain = terrain
        
        # Place initial buildings
        for building_data in initial_buildings:
            pos = Position(**building_data['position'])
            b_type = BuildingType[building_data['type']]
            level = building_data.get('level', 1)
            city_map.get_tile(pos.x, pos.y).building = Building(b_type, level)

        print(f"Loaded city map of size {width}x{height} from {filepath}")
        return city_map
    
    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'tiles': [[tile.to_dict() if tile else None for tile in row] for row in self.tiles]
        }
    
    @classmethod
    def from_dict(cls, data):
        city_map = cls(data['width'], data['height'])
        city_map.tiles = [[CityTile.from_dict(t_data) for t_data in col] for col in data.get('tiles', [])]
        return city_map


@dataclass
class City:
    """Represents a player's city."""
    id: str
    name: str
    owner_id: str
    position: Position # Position on the world map
    city_map: CityMap
    resources: Resources = field(default_factory=Resources)
    build_queue: List[Action] = field(default_factory=list)
    num_buildings: int = 0
    max_buildings: int = 0
    action_points: int = 0
    max_action_points: int = 0
    recruitment_queue: List[RecruitmentProgress] = field(default_factory=list)
    garrison: dict = field(default_factory=dict)


    def update_stats_from_citadel(self):
        """Recalculates city-wide stats based on the Citadel's level."""
        citadel = None
        num_buildings = 0
        for row in self.city_map.tiles:
            for tile in row:
                if tile.building:
                    num_buildings += 1
                    if tile.building.type == BuildingType.CITADEL:
                        citadel = tile.building
        if not citadel:
            print(f"Warning: City '{self.name}' has no Citadel. Stats will be zero.")
            return

        self.num_buildings = num_buildings

        citadel_stats = BUILDING_DATA[BuildingType.CITADEL]['provides'].get(citadel.level, {})
        self.max_buildings = citadel_stats.get('max_buildings', 0)
        self.max_action_points = citadel_stats.get('action_points', 0)
        self.action_points = self.max_action_points


    def deep_copy(self) -> City:
        new_city = City(self.id, self.name, self.owner_id, self.position, self.city_map.deep_copy())
        new_city.resources = Resources(self.resources.food, self.resources.wood, self.resources.iron)
        new_city.action_points = self.action_points
        new_city.build_queue = [action.deep_copy() for action in self.build_queue]
        new_city.recruitment_queue = [progress.deep_copy() for progress in self.recruitment_queue]
        new_city.garrison = self.garrison.copy()

        new_city.update_stats_from_citadel() # Recalculate to be safe
        return new_city

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'owner_id': self.owner_id,
            'position': self.position.__dict__,
            'city_map': self.city_map.to_dict(),
            'resources': self.resources.__dict__,
            'build_queue': [action.to_dict() for action in self.build_queue],
            'recruitment_queue': [progress.to_dict() for progress in self.recruitment_queue],
            'action_points': self.action_points,
            'garrison': {unit_type.name: count for unit_type, count in self.garrison.items()}
        }

    @classmethod
    def from_dict(cls, data: dict, action_class_map: dict) -> City:
        queue = []
        for action_data in data.get('build_queue', []):
            action_class = action_class_map.get(action_data['action_type'])
            if action_class:
                queue.append(action_class.from_dict(action_data))
        
        recruitment_queue = []
        for progress_data in data.get('recruitment_queue', []):
            recruitment_queue.append(RecruitmentProgress.from_dict(progress_data))

        city = cls(
            id=data['id'],
            name=data['name'],
            owner_id=data['owner_id'],
            position=Position(**data['position']),
            city_map=CityMap.from_dict(data['city_map']),
            resources=Resources(**data['resources']),
            action_points=data.get('action_points', 0),
            build_queue=queue,
            recruitment_queue=recruitment_queue,
            garrison={UnitType[unit_name]: count for unit_name, count in data.get('garrison', {}).items()}
        )
        
        # Ensure stats are calculated and AP is full on creation.
        city.update_stats_from_citadel()
        return city