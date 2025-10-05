from abc import ABC, abstractmethod
from typing import Optional
import pygame

class BaseComponent(ABC):
    """
    Abstract base class for all UI components.
    Defines the common interface for drawing and handling events.
    """

    @abstractmethod
    def handle_event(self, event: pygame.event.Event, *args, **kwargs) -> Optional[dict]:
        """
        Process a single Pygame event. If the event is handled and results
        in a game action, return the action dictionary. Otherwise, return None.
        """
        pass

    @abstractmethod
    def draw(self, screen: pygame.Surface, *args, **kwargs):
        """Draw the component onto the provided screen surface."""
        pass