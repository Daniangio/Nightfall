from nightfall.core.actions.action import Action
from nightfall.core.common.datatypes import Position
from nightfall.core.common.enums import BuildingType, CityTerrainType, UnitType
from nightfall.core.common.game_data import BUILDING_DATA, UNIT_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall.core.components.city import Building

class BuildBuildingAction(Action):
    def __init__(self, player_id: str, city_id: str, position: Position, building_type: BuildingType):
        super().__init__(player_id, city_id, 0.0)
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
            'building_type': self.building_type.value,
            'progress': self.progress
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'BuildBuildingAction':
        action = cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            position=Position(**data['position']),
            building_type=BuildingType(data['building_type']),
        )
        action.progress = data.get('progress', 0.0)
        return action

    def execute(self, game_state: 'GameState') -> bool:
        player = game_state.players.get(self.player_id)
        city = player.get_city(self.city_id, game_state.cities) if player else None
        
        if not city:
            print(f"[ACTION FAILED] City '{self.city_id}' not found for player '{self.player_id}'.")
            return False
            
        tile = city.city_map.get_tile(self.position.x, self.position.y)
        
        build_data = BUILDING_DATA.get(self.building_type, {}).get('build', {})
        if 'cost' not in build_data:
            print(f"[ACTION FAILED] No build cost defined for {self.building_type.value}.")
            return False
        cost = build_data['cost']

        # --- Validation ---
        if city.num_buildings >= city.max_buildings:
            print(f"[ACTION FAILED] City is at its maximum building limit ({city.max_buildings}).")
            return False
        if tile.building:
            print(f"[ACTION FAILED] Tile at {self.position} already has a building.")
            return False
        # Check if another action for this tile is already in the city's build queue
        if any(hasattr(a, 'position') and a.position == self.position for a in city.build_queue):
            print(f"[ACTION FAILED] An action for tile {self.position} is already in the build queue.")
            return False
        if not city.resources.can_afford(cost):
            print(f"[ACTION FAILED] Not enough resources to build {self.building_type.value}.")
            return False
        
        # --- Execution ---
        city.resources -= cost
        city.build_queue.append(self)
        print(f"[ACTION SUCCESS] Queued build for {self.building_type.value} at {self.position}.")
        return True


class UpgradeBuildingAction(Action):
    def __init__(self, player_id: str, city_id: str, position: Position):
        super().__init__(player_id, city_id, 0.0)
        self.position = position

    def __str__(self):
        return f"Upgrade building at {self.position.x},{self.position.y}"
        
    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'city_id': self.city_id,
            'action_type': self.__class__.__name__,
            'position': {'x': self.position.x, 'y': self.position.y},
            'progress': self.progress
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UpgradeBuildingAction':
        action = cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            position=Position(**data['position']),
        )
        action.progress = data.get('progress', 0.0)
        return action

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

        # --- Validation ---
        if 'upgrade' not in building_data or next_level not in building_data['upgrade']:
            print(f"[ACTION FAILED] Building at {self.position} is at max level.")
            return False
        
        cost = building_data['upgrade'][next_level]['cost']

        if not city.resources.can_afford(cost):
            print(f"[ACTION FAILED] Not enough resources to upgrade {building.type.value}.")
            return False

        # --- Execution ---
        city.resources -= cost
        city.build_queue.append(self)
        print(f"[ACTION SUCCESS] Queued upgrade for {building.type.value} at {self.position} to level {next_level}.")
        return True


class DemolishAction(Action):
    def __init__(self, player_id: str, city_id: str, position: Position):
        super().__init__(player_id, city_id, 0.0)
        self.position = position

    def __str__(self):
        return f"Demolish at {self.position.x},{self.position.y}"

    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'city_id': self.city_id,
            'action_type': self.__class__.__name__,
            'position': {'x': self.position.x, 'y': self.position.y},
            'progress': self.progress
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DemolishAction':
        action = cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            position=Position(**data['position']),
        )
        action.progress = data.get('progress', 0.0)
        return action

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
        demolish_data = DEMOLISH_COST_BUILDING if can_demolish_building else DEMOLISH_COST_RESOURCE
        cost = demolish_data['cost']

        # --- Validation ---
        if not city.resources.can_afford(cost):
            print(f"[ACTION FAILED] Not enough resources to demolish.")
            return False

        city.resources -= cost
        city.build_queue.append(self)
        print(f"[ACTION SUCCESS] Queued demolish for {self.position}.")
        return True


class RecruitUnitAction(Action):
    def __init__(self, player_id: str, city_id: str, unit_type: UnitType, quantity: int):
        super().__init__(player_id, city_id, 0.0)
        self.unit_type = unit_type
        self.quantity = quantity

    def __str__(self):
        return f"Recruit {self.quantity} {self.unit_type.name.title()}"

    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'city_id': self.city_id,
            'action_type': self.__class__.__name__,
            'unit_type': self.unit_type.name,
            'quantity': self.quantity,
            'progress': self.progress
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RecruitUnitAction':
        action = cls(
            player_id=data['player_id'],
            city_id=data['city_id'],
            unit_type=UnitType[data['unit_type']],
            quantity=data['quantity'],
        )
        action.progress = data.get('progress', 0.0)
        return action

    def execute(self, game_state: 'GameState') -> bool:
        player = game_state.players.get(self.player_id)
        city = player.get_city(self.city_id, game_state.cities) if player else None
        
        if not city:
            print(f"[ACTION FAILED] City '{self.city_id}' not found for player '{self.player_id}'.")
            return False

        unit_data = UNIT_DATA.get(self.unit_type)
        if not unit_data:
            print(f"[ACTION FAILED] Unit type {self.unit_type} not found in game data.")
            return False

        total_cost = Resources(
            food=unit_data['cost'].food * self.quantity,
            wood=unit_data['cost'].wood * self.quantity,
            iron=unit_data['cost'].iron * self.quantity
        )

        if not city.resources.can_afford(total_cost):
            print(f"[ACTION FAILED] Not enough resources to recruit {self.quantity} {self.unit_type.name.title()}.")
            return False

        city.resources -= total_cost
        city.recruitment_queue.append(self)
        print(f"[ACTION SUCCESS] Queued recruitment of {self.quantity} {self.unit_type.name.title()}.")
        return True
