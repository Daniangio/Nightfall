import json
import copy
from typing import Dict, Type
from nightfall.core.components.map import GameMap
from nightfall.core.components.player import Player
from nightfall.core.components.city import City, CityMap
from nightfall.core.actions.action import Action
from nightfall.core.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction

class GameState:
    """
    A container for the entire state of the game world.
    Handles its own serialization and deserialization.
    """
    ACTION_CLASS_MAP: Dict[str, Type[Action]] = {
        'BuildBuildingAction': BuildBuildingAction,
        'UpgradeBuildingAction': UpgradeBuildingAction,
        'DemolishAction': DemolishAction,
    }

    def __init__(self, game_map: GameMap, players: Dict[str, Player], cities: Dict[str, City], turn: int = 0):
        self.game_map = game_map
        self.players = players
        self.cities = cities
        self.turn = turn

    def to_dict(self) -> dict:
        """Serializes the core game state components to a dictionary."""
        return {
            'turn': self.turn,
            'game_map': self.game_map.to_dict(),
            'players': {p_id: p.to_dict() for p_id, p in self.players.items()},
            'cities': {c_id: c.to_dict() for c_id, c in self.cities.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GameState':
        """Deserializes a game state from a dictionary."""

        if 'game_map' in data:
            game_map = GameMap.from_dict(data['game_map'])
        else:
            world_map_path = 'nightfall/server/data/map.txt'
            game_map = GameMap.load_from_file(world_map_path)

        if 'cities' in data:
            cities = {c_id: City.from_dict(c_data, cls.ACTION_CLASS_MAP) for c_id, c_data in data['cities'].items()}
        else:
            city_layout_path = 'nightfall/server/data/city_layout.txt'
            city_data = {
                'id': 'city1',
                'name': 'City 1',
                'owner_id': 'player1',
                'position': {'x': 0, 'y': 0},
                'city_map': CityMap.load_from_file(city_layout_path).to_dict(),
                'resources': {'food': 1000, 'wood': 1000, 'iron': 1000},
                'build_queue': [],
                'recruitment_queue': [],
                'action_points': 0,
                'garrison': {},
            }
            cities = {
                'city1': City.from_dict(city_data, cls.ACTION_CLASS_MAP)
            }

        players = {p_id: Player.from_dict(p_data, cls.ACTION_CLASS_MAP) for p_id, p_data in data['players'].items()}
        
        return cls(game_map, players, cities, data['turn'])

    def to_json_string(self) -> str:
        """Serializes the game state to a JSON string for network transport."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json_string(cls, json_str: str) -> 'GameState':
        """Deserializes a game state from a JSON string received from the network."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save_to_file(self, filepath: str):
        """Serializes the entire game state to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"Game state saved to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str) -> 'GameState':
        """
        Loads a game state from a JSON file.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        game_state = cls.from_dict(data)
        print(f"Loaded game state from {filepath} at turn {game_state.turn}")

        return game_state

    def deep_copy(self) -> 'GameState':
        """
        Creates a deep copy of the game state for simulations.
        A simple and effective way to deep copy is to serialize and deserialize.
        """
        # Using to_dict and from_dict is faster than JSON string conversion for in-memory copies.
        data_copy = copy.deepcopy(self.to_dict())
        return GameState.from_dict(data_copy)
