from typing import Dict, List, Optional
from nightfall_engine.components.city import City
from nightfall_engine.actions.action import Action

class Player:
    """Represents a player in the game."""
    def __init__(self, name: str, city_ids: List[str], action_queue: List[Action] = None):
        self.name = name
        self.city_ids = city_ids
        self.action_queue = action_queue if action_queue is not None else []

    def get_city(self, city_id: str, all_cities: Dict[str, City]) -> Optional[City]:
        """
        A helper method to retrieve a player's city object from the global
        cities dictionary. Returns None if the city_id does not belong to the player
        or doesn't exist.
        """
        if city_id in self.city_ids and city_id in all_cities:
            return all_cities[city_id]
        return None

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'city_ids': self.city_ids,
            'action_queue': [action.to_dict() for action in self.action_queue]
        }

    @classmethod
    def from_dict(cls, data: dict, action_class_map: dict) -> 'Player':
        # Action queue is loaded empty, as it's a turn-by-turn construct
        # set by the server from player orders. However, when the server
        # receives orders, it needs to deserialize them.
        action_queue = []
        if 'action_queue' in data:
            # This path is used on the server when deserializing orders.
            # It's also used on the client for deep copies during prediction.
            action_queue = [Action.from_dict(d, action_class_map) for d in data['action_queue']]
        return cls(data['name'], data['city_ids'], action_queue)
