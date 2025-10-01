from nightfall_engine.actions.action import Action
from nightfall_engine.common.enums import BuildingType
from nightfall_engine.common.datatypes import Position
from nightfall_engine.components.city import Building

class BuildBuildingAction(Action):
    """An action to construct a new building on a city tile."""
    ACTION_TYPE = "BuildBuildingAction"

    def __init__(self, player_id: str, city_id: str, position: Position, building_type: BuildingType):
        super().__init__(player_id)
        self.city_id = city_id
        self.position = position
        self.building_type = building_type

    def execute(self, game_state) -> bool:
        city = game_state.cities.get(self.city_id)
        if not city or city.owner_id != self.player_id: return False
        
        tile = city.city_map.get_tile(self.position.x, self.position.y)
        if not tile or tile.building: return False
        
        # NOTE: Simplified execution without resource check for now.
        tile.building = Building(self.building_type, 1)
        print(f"Constructed level 1 {self.building_type.name} at {self.position} in {city.name}")
        return True

    def to_dict(self):
        return {
            'action_type': self.ACTION_TYPE,
            'player_id': self.player_id,
            'city_id': self.city_id,
            'position': self.position.__dict__,
            'building_type': self.building_type.name
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['player_id'],
            data['city_id'],
            Position(**data['position']),
            BuildingType[data['building_type']]
        )
    
    def __str__(self):
        return f"Build {self.building_type.name} at ({self.position.x}, {self.position.y})"
