from nightfall_engine.actions.action import Action
from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.common.datatypes import Position, Resources
from nightfall_engine.components.city import Building
from nightfall_engine.common.game_data import BUILDING_DATA, DEMOLISH_COST

class BuildBuildingAction(Action):
    """An action to construct a new building on a city tile."""
    ACTION_TYPE = "BuildBuildingAction"

    def __init__(self, player_id: str, city_id: str, position: Position, building_type: BuildingType):
        super().__init__(player_id)
        self.city_id = city_id
        self.position = position
        self.building_type = building_type

    def get_cost(self) -> Resources:
        return BUILDING_DATA.get(self.building_type, {}).get('build', {}).get('cost', Resources())

    def execute(self, game_state) -> bool:
        city = game_state.cities.get(self.city_id)
        if not city or city.owner_id != self.player_id: return False
        
        tile = city.city_map.get_tile(self.position.x, self.position.y)
        if not tile or tile.building: return False
        
        # Server-side validation
        cost = self.get_cost()
        if city.resources.food < cost.food or city.resources.wood < cost.wood or city.resources.iron < cost.iron:
            print(f"Action failed: Not enough resources for {self}")
            return False

        # Validate terrain type for building
        buildable_terrains = {
            BuildingType.FARM: [CityTerrainType.GRASS],
            BuildingType.LUMBER_MILL: [CityTerrainType.FOREST_PLOT],
            BuildingType.IRON_MINE: [CityTerrainType.IRON_DEPOSIT],
        }
        if tile.terrain not in buildable_terrains.get(self.building_type, []):
             print(f"Action failed: Cannot build {self.building_type.name} on {tile.terrain.name}")
             return False

        city.resources -= cost

        tile.building = Building(self.building_type, 1)
        print(f"Constructed level 1 {self.building_type.name} at {self.position} in {city.name}")
        return True

    def to_dict(self):
        return {'action_type': self.ACTION_TYPE, 'player_id': self.player_id, 'city_id': self.city_id, 'position': self.position.__dict__, 'building_type': self.building_type.name}

    @classmethod
    def from_dict(cls, data):
        return cls(data['player_id'], data['city_id'], Position(**data['position']), BuildingType[data['building_type']])
    
    def __str__(self):
        return f"Build {self.building_type.name} at ({self.position.x}, {self.position.y})"

class UpgradeBuildingAction(Action):
    """An action to upgrade an existing building."""
    ACTION_TYPE = "UpgradeBuildingAction"
    
    def __init__(self, player_id: str, city_id: str, position: Position, building_type: BuildingType, from_level: int):
        super().__init__(player_id)
        self.city_id = city_id
        self.position = position
        self.building_type = building_type
        self.from_level = from_level
    
    def get_cost(self) -> Resources:
        upgrade_costs = BUILDING_DATA.get(self.building_type, {}).get('upgrade', {})
        return upgrade_costs.get(self.from_level, {}).get('cost', Resources())

    def execute(self, game_state) -> bool:
        city = game_state.cities.get(self.city_id)
        if not city or city.owner_id != self.player_id: return False
        
        tile = city.city_map.get_tile(self.position.x, self.position.y)
        if not tile or not tile.building or tile.building.level != self.from_level: return False
        
        cost = self.get_cost()
        if city.resources.food < cost.food or city.resources.wood < cost.wood or city.resources.iron < cost.iron:
            print(f"Action failed: Not enough resources for {self}")
            return False
        
        city.resources -= cost
        tile.building.level += 1
        print(f"Upgraded {tile.building.type.name} at {self.position} to level {tile.building.level}")
        return True

    def to_dict(self):
        return {'action_type': self.ACTION_TYPE, 'player_id': self.player_id, 'city_id': self.city_id, 'position': self.position.__dict__, 'building_type': self.building_type.name, 'from_level': self.from_level}
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['player_id'], data['city_id'], Position(**data['position']), BuildingType[data['building_type']], data['from_level'])

    def __str__(self): 
        return f"Upgrade {self.building_type.name} at ({self.position.x}, {self.position.y})"


class DemolishAction(Action):
    """An action to demolish a building or clear a plot."""
    ACTION_TYPE = "DemolishAction"

    def __init__(self, player_id: str, city_id: str, position: Position):
        super().__init__(player_id)
        self.city_id = city_id
        self.position = position
    
    def get_cost(self) -> Resources:
        return DEMOLISH_COST

    def execute(self, game_state) -> bool:
        city = game_state.cities.get(self.city_id)
        if not city or city.owner_id != self.player_id: return False
        
        tile = city.city_map.get_tile(self.position.x, self.position.y)
        if not tile: return False
        
        cost = self.get_cost()
        if city.resources.food < cost.food or city.resources.wood < cost.wood or city.resources.iron < cost.iron:
            print(f"Action failed: Not enough resources for {self}")
            return False

        city.resources -= cost
        
        if tile.building:
            if tile.building.type == BuildingType.CITADEL:
                print(f"Action failed: Cannot demolish Citadel.")
                city.resources += cost # Refund
                return False
            print(f"Demolished {tile.building.type.name} at {self.position}")
            tile.building = None
        elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
            print(f"Cleared {tile.terrain.name} at {self.position}")
            tile.terrain = CityTerrainType.GRASS
        
        return True

    def to_dict(self):
        return {'action_type': self.ACTION_TYPE, 'player_id': self.player_id, 'city_id': self.city_id, 'position': self.position.__dict__}
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['player_id'], data['city_id'], Position(**data['position']))

    def __str__(self):
        return f"Demolish at ({self.position.x}, {self.position.y})"
