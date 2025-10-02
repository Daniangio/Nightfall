from abc import ABC, abstractmethod

class Action(ABC):
    """Abstract base class for all player actions (Command Pattern)."""
    def __init__(self, player_id: str, city_id: str):
        self.player_id = player_id
        self.city_id = city_id

    @abstractmethod
    def execute(self, game_state) -> bool:
        """Executes the action, modifying the game state. Returns True if successful."""
        pass

    @classmethod
    def from_dict(cls, data: dict, action_class_map: dict) -> 'Action':
        """
        Factory method to create an Action instance from a dictionary.
        This acts as a dispatcher to the correct subclass.
        """
        action_type = data.get('action_type')
        if not action_type:
            raise ValueError("Action data must contain 'action_type'")

        action_class = action_class_map.get(action_type)
        if not action_class:
            raise ValueError(f"Unknown action type: {action_type}")

        # Delegate to the specific class's from_dict_data method
        return action_class._from_dict_data(data)

    @classmethod
    @abstractmethod
    def _from_dict_data(cls, data: dict) -> 'Action':
        """Subclasses must implement this to deserialize their specific fields."""
        pass
