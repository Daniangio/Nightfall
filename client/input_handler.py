import pygame
from client.ui_manager import UIManager
from nightfall_engine.state.game_state import GameState
from nightfall_engine.common.datatypes import Position
from nightfall_engine.actions.city_actions import (
    BuildBuildingAction, UpgradeBuildingAction, DemolishAction
)

class InputHandler:
    """
    Handles all raw user input (mouse clicks, keyboard presses) and translates
    it into game-specific commands or actions.
    """
    def __init__(self, player_id: str, city_id: str, ui_manager: UIManager):
        """
        Initializes the InputHandler.
        
        Args:
            player_id: The ID of the player this client is controlling.
            city_id: The ID of the city this client is viewing.
            ui_manager: The UI manager to interact with for context menus and buttons.
        """
        self.player_id = player_id
        self.city_id = city_id
        self.ui_manager = ui_manager

    def handle_input(self, events: list, predicted_state: GameState, action_queue: list) -> dict | None:
        """
        Processes a list of Pygame events for a single frame.

        Args:
            events: The list of events from pygame.event.get().
            predicted_state: The client's predicted game state for validation.
            action_queue: The client's current list of pending actions.

        Returns:
            A dictionary representing a client action, or None if no action was taken.
        """
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
                return self._handle_mouse_click(event.pos, predicted_state, action_queue)
        return None

    def handle_lobby_input(self, events: list, ui_manager: UIManager) -> dict | None:
        """
        Processes a list of Pygame events for the lobby screen.
        """
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
                mouse_pos = event.pos
                for name, rect in ui_manager.lobby_buttons.items():
                    if rect.collidepoint(mouse_pos):
                        if name == "create":
                            return {"type": "create_session"}
                        else: # It's a session_id
                            return {"type": "join_session", "session_id": name}
        return None


    def _handle_mouse_click(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list) -> dict | None:
        """Handles a single left mouse click at a given position."""
        # 1. Prioritize UI elements: Context menu has top priority.
        if self.ui_manager.context_menu and self.ui_manager.context_menu['rect'].collidepoint(mouse_pos):
            return self._handle_context_menu_click(mouse_pos, state, action_queue)

        # 2. Check main UI buttons
        for name, rect in self.ui_manager.buttons.items():
            if rect.collidepoint(mouse_pos):
                if name == "end_day":
                    return {"type": "end_day"}
                elif name == "exit_session":
                    return {"type": "exit_session"}
        
        # 3. Check action queue 'X' buttons
        for i, rect in enumerate(self.ui_manager.queue_item_rects):
             if rect.collidepoint(mouse_pos):
                return {"type": "remove_action", "index": i}

        # 4. If no UI was clicked, check the city grid
        city = state.cities[self.city_id]
        grid_pos = self.ui_manager.screen_to_grid(mouse_pos)
        if grid_pos and 0 <= grid_pos.x < city.city_map.width and 0 <= grid_pos.y < city.city_map.height:
            self._handle_city_tile_click(grid_pos, state)

        return None

    def _handle_city_tile_click(self, grid_pos: Position, state: GameState):
        """Sets the context menu based on a click on a city tile."""
        city = state.cities[self.city_id]
        tile = city.city_map.get_tile(grid_pos.x, grid_pos.y)
        if tile:
            self.ui_manager.set_context_menu_for_tile(grid_pos, tile)

    def _handle_context_menu_click(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list) -> dict | None:
        """Handles a click within an active context menu."""
        selected_pos = self.ui_manager.context_menu['position']
        
        for option in self.ui_manager.context_menu['options']:
            if option['rect'].collidepoint(mouse_pos):
                action_type = option['action']

                # --- Action Queue Validation ---
                is_tile_in_queue = any(hasattr(a, 'position') and a.position == selected_pos for a in action_queue)
                if is_tile_in_queue:
                    print("[CLIENT] Action failed: An action for this tile is already in the queue.")
                    self.ui_manager.clear_context_menu()
                    return None
                # --- End Validation ---

                action = None
                
                if action_type == 'build':
                    action = BuildBuildingAction(
                        player_id=self.player_id,
                        city_id=self.city_id,
                        position=selected_pos,
                        building_type=option['building_type']
                    )
                elif action_type == 'upgrade':
                    action = UpgradeBuildingAction(
                        player_id=self.player_id,
                        city_id=self.city_id,
                        position=selected_pos
                    )
                elif action_type == 'demolish':
                    action = DemolishAction(
                        player_id=self.player_id,
                        city_id=self.city_id,
                        position=selected_pos
                    )
                
                self.ui_manager.clear_context_menu()
                if action:
                    # When adding to the local queue, we add the object.
                    # When sending to the server, we'll call .to_dict() on it.
                    # The to_dict method now correctly includes player/city IDs.
                    return {"type": "add_action", "action": action}
        
        # If the click was inside the menu but not on a button, just close it
        self.ui_manager.clear_context_menu()
        return None
