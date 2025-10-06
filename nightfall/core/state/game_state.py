import json
import copy
from typing import Dict, Type
from nightfall.core.components.map import GameMap
from nightfall.core.components.player import Player
from nightfall.core.common.datatypes import Position, Resources
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
        """Deserializes a game state from a dictionary (e.g., from a save file or network)."""
        game_map = GameMap.from_dict(data['game_map'])
        cities = {c_id: City.from_dict(c_data, cls.ACTION_CLASS_MAP) for c_id, c_data in data['cities'].items()}
        players = {p_id: Player.from_dict(p_data, cls.ACTION_CLASS_MAP) for p_id, p_data in data.get('players', {}).items()}
        return cls(game_map, players, cities, data.get('turn', 0))

    @classmethod
    def from_world_file(cls, filepath: str) -> 'GameState':
        """Creates a new game state from a world definition file."""
        with open(filepath, 'r') as f:
            world_data = json.load(f)

        # 1. Load World Map
        game_map = GameMap.load_from_data(world_data['world_map']['layout'])

        # 2. Load Players
        players = {}
        player_city_map = {} # Helper to assign cities to players
        for p_data in world_data['players']:
            players[p_data['id']] = Player(name=p_data['name'], city_ids=[])
            player_city_map[p_data['id']] = []

        # 3. Load Cities (Places)
        cities = {}
        for place_data in world_data['world_map']['places']:
            if place_data['type'] == 'CITY':
                city_map_path = place_data.get('city_map_path', 'nightfall/server/data/city_layouts/default_city.json')
                city = City(id=place_data['id'], name=place_data['name'], player_id=place_data['player_id'],
                            position=Position(**place_data['position']), city_map=CityMap.load_from_file(city_map_path),
                            resources=Resources(**place_data.get('initial_resources', {})))
                city.update_stats_from_citadel() # Calculate initial stats
                cities[city.id] = city
                if city.player_id in player_city_map:
                    players[city.player_id].city_ids.append(city.id)

        return cls(game_map, players, cities, turn=1)

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
        Loads a game state from a JSON save file.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        game_state = cls.from_dict(data)
        print(f"Loaded saved game state from {filepath} at turn {game_state.turn}")

        return game_state

    def deep_copy(self) -> 'GameState':
        """
        Creates a deep copy of the game state for simulations.
        A simple and effective way to deep copy is to serialize and deserialize.
        """
        # Using to_dict and from_dict is faster than JSON string conversion for in-memory copies.
        data_copy = copy.deepcopy(self.to_dict())
        return GameState.from_dict(data_copy)
