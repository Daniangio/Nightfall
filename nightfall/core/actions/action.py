from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nightfall.core.state.game_state import GameState

class Action(ABC):
    """Abstract base class for all actions in the game."""
    def __init__(self, player_id: str, city_id: str, progress: float = 0.0):
        self.player_id = player_id
        self.city_id = city_id
        self.progress = progress

    @abstractmethod
    def execute(self, game_state: GameState) -> bool:
        """
        Executes the action, validating it and applying its effects to the
        game state. Returns True on success, False on failure.
        """
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Serializes the action to a dictionary."""
        pass

    @classmethod
    def from_dict(cls, data: dict, action_class_map: dict) -> Action:
        """
        Factory method to deserialize an action from a dictionary.
        It uses the 'action_type' field in the data to determine the
        correct subclass to instantiate.
        """
        action_type = data.get('action_type')
        if action_type in action_class_map:
            action_class = action_class_map[action_type]
            return action_class.from_dict(data)
        raise ValueError(f"Unknown action type: {action_type}")
