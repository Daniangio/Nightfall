from nightfall_engine.actions.action import Action
from nightfall_engine.common.datatypes import Position
from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.common.game_data import BUILDING_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall_engine.components.city import Building

class BuildBuildingAction(Action):
    def __init__(self, player_id: str, city_id: str, position: Position, building_type: BuildingType):
        super().__init__(player_id, city_id)
        self.position = position
        self.building_type = building_type

    def __str__(self):
        return f"Build {self.building_type.value} at {self.position.x},{self.position.y}"

    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'city_id': self.city_id,
            'action_type': self.__class__.__name__,
            'position': {'x': self.position.x, 'y': self.position.y},
            'building_type': self.building_type.value
        }

    @classmethod
    def _from_dict_data(cls, data: dict) -> 'BuildBuildingAction':
        return cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            position=Position(**data['position']),
            building_type=BuildingType(data['building_type'])
        )

    def execute(self, game_state: 'GameState') -> bool:
        player = game_state.players.get(self.player_id)
        city = player.get_city(self.city_id, game_state.cities) if player else None
        
        if not city:
            print(f"[ACTION FAILED] City '{self.city_id}' not found for player '{self.player_id}'.")
            return False
            
        tile = city.city_map.get_tile(self.position.x, self.position.y)
        
        # Correctly access the build cost
        build_data = BUILDING_DATA.get(self.building_type, {}).get('build', {})
        if 'cost' not in build_data:
            print(f"[ACTION FAILED] No build cost defined for {self.building_type.value}.")
            return False
        cost = build_data['cost']

        # --- Validation ---
        if tile.building:
            print(f"[ACTION FAILED] Tile at {self.position} already has a building.")
            return False
        if city.resources.food < cost.food or city.resources.wood < cost.wood or city.resources.iron < cost.iron:
            print(f"[ACTION FAILED] Not enough resources to build {self.building_type.value}.")
            return False
        
        # --- Execution ---
        city.resources -= cost
        tile.building = Building(self.building_type, 1)
        print(f"[ACTION SUCCESS] Built {self.building_type.value} at {self.position}.")
        return True


class UpgradeBuildingAction(Action):
    def __init__(self, player_id: str, city_id: str, position: Position):
        super().__init__(player_id, city_id)
        self.position = position

    def __str__(self):
        return f"Upgrade building at {self.position.x},{self.position.y}"
        
    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'city_id': self.city_id,
            'action_type': self.__class__.__name__,
            'position': {'x': self.position.x, 'y': self.position.y}
        }

    @classmethod
    def _from_dict_data(cls, data: dict) -> 'UpgradeBuildingAction':
        return cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            position=Position(**data['position'])
        )

    def execute(self, game_state: 'GameState') -> bool:
        player = game_state.players.get(self.player_id)
        city = player.get_city(self.city_id, game_state.cities) if player else None
        
        if not city:
            print(f"[ACTION FAILED] City '{self.city_id}' not found for player '{self.player_id}'.")
            return False

        tile = city.city_map.get_tile(self.position.x, self.position.y)
        
        if not tile or not tile.building:
            print(f"[ACTION FAILED] No building to upgrade at {self.position}.")
            return False
            
        building = tile.building
        building_data = BUILDING_DATA[building.type]
        next_level = building.level + 1

        # Correctly access the upgrade cost
        if 'upgrade' not in building_data or next_level not in building_data['upgrade']:
            print(f"[ACTION FAILED] Building at {self.position} is at max level.")
            return False
        
        cost = building_data['upgrade'][next_level]['cost']

        if city.resources.food < cost.food or city.resources.wood < cost.wood or city.resources.iron < cost.iron:
            print(f"[ACTION FAILED] Not enough resources to upgrade {building.type.value}.")
            return False

        city.resources -= cost
        building.level = next_level
        print(f"[ACTION SUCCESS] Upgraded {building.type.value} at {self.position} to level {next_level}.")
        return True


class DemolishAction(Action):
    def __init__(self, player_id: str, city_id: str, position: Position):
        super().__init__(player_id, city_id)
        self.position = position

    def __str__(self):
        return f"Demolish at {self.position.x},{self.position.y}"

    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'city_id': self.city_id,
            'action_type': self.__class__.__name__,
            'position': {'x': self.position.x, 'y': self.position.y}
        }

    @classmethod
    def _from_dict_data(cls, data: dict) -> 'DemolishAction':
        return cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            position=Position(**data['position'])
        )

    def execute(self, game_state: 'GameState') -> bool:
        player = game_state.players.get(self.player_id)
        city = player.get_city(self.city_id, game_state.cities) if player else None
        
        if not city:
            print(f"[ACTION FAILED] City '{self.city_id}' not found for player '{self.player_id}'.")
            return False

        tile = city.city_map.get_tile(self.position.x, self.position.y)
        
        can_demolish_building = tile and tile.building and tile.building.type != BuildingType.CITADEL
        can_demolish_plot = tile and tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]

        if not (can_demolish_building or can_demolish_plot):
            print(f"[ACTION FAILED] Nothing to demolish at {self.position}.")
            return False

        # Determine the correct cost based on what is being demolished
        cost = DEMOLISH_COST_BUILDING if can_demolish_building else DEMOLISH_COST_RESOURCE

        if not city.resources.can_afford(cost):
            print(f"[ACTION FAILED] Not enough resources to demolish.")
            return False

        city.resources -= cost

        if can_demolish_building:
            tile.building = None
            print(f"[ACTION SUCCESS] Demolished building at {self.position}.")
        elif can_demolish_plot:
            tile.terrain = CityTerrainType.GRASS
            print(f"[ACTION SUCCESS] Cleared plot at {self.position}, turning it to grass.")

        return True
