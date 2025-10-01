from abc import ABC, abstractmethod

class Action(ABC):
    """Abstract base class for all player actions (Command Pattern)."""
    def __init__(self, player_id: str):
        self.player_id = player_id

    @abstractmethod
    def execute(self, game_state) -> bool:
        """Executes the action, modifying the game state. Returns True if successful."""
        pass
