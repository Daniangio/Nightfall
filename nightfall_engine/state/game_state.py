import json
from typing import Dict
from nightfall_engine.components.map import GameMap
from nightfall_engine.components.player import Player
from nightfall_engine.components.city import City
# We need to import the action classes for deserialization
from nightfall_engine.actions.city_actions import BuildBuildingAction

class GameState:
    """A container for the entire state of the game world."""
    ACTION_CLASS_MAP = {
        'BuildBuildingAction': BuildBuildingAction,
        # Add other action classes here as they are created
    }

    def __init__(self, game_map: GameMap, players: Dict[str, Player], cities: Dict[str, City], turn: int = 0):
        self.game_map = game_map
        self.players = players
        self.cities = cities
        self.turn = turn

    def save_to_json(self, filepath: str):
        """Serializes the entire game state to a JSON file."""
        state_dict = {
            'turn': self.turn,
            'game_map': self.game_map.to_dict(),
            'players': {p_id: p.to_dict() for p_id, p in self.players.items()},
            'cities': {c_id: c.to_dict() for c_id, c in self.cities.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=4)
        print(f"Game state saved to {filepath}")

    @classmethod
    def load_from_json(cls, filepath: str, map_filepath: str):
        """Loads a game state from JSON."""
        game_map = GameMap.load_from_file(map_filepath)
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        players = {p_id: Player.from_dict(p_data) for p_id, p_data in data['players'].items()}
        cities = {c_id: City.from_dict(c_data, cls.ACTION_CLASS_MAP) for c_id, c_data in data['cities'].items()}
        
        print(f"Loaded game state from {filepath} at turn {data['turn']}")
        return cls(game_map, players, cities, data['turn'])
