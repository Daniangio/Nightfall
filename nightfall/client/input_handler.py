from typing import Optional
import pygame
from nightfall.client.enums import ActiveView
from nightfall.client.ui_manager import UIManager
from nightfall.core.common.datatypes import Position
from nightfall.core.state.game_state import GameState

class InputHandler:
    """
    Handles all raw user input (mouse clicks, keyboard presses) and translates
    it into game-specific commands or actions.
    """
    def __init__(self, player_id: str, city_id: str, ui_manager: UIManager):
        # These are now less important here as components can get them from UIManager
        self.player_id = player_id
        self.city_id = city_id
        self.ui_manager = ui_manager

        # For double-click detection
        self.last_click_time = 0
        self.last_click_pos = None

    def handle_input(self, events: list, predicted_state: GameState, action_queue: list) -> Optional[dict]:
        """
        Processes a list of Pygame events for a single frame.

        Args:
            events: The list of events from pygame.event.get().
            predicted_state: The client's predicted game state for validation.
            action_queue: The client's current list of pending actions.

        Returns:
            A dictionary representing a client action, or None if no action was taken.
        """
        # Make the current predicted state available for all input handler methods via the UI manager
        self.ui_manager.game_state_for_input = predicted_state

        for event in events:
            # --- Component-Based Event Handling ---
            # Iterate in reverse so top-most components get events first.
            for component in reversed(self.ui_manager.components):
                action = component.handle_event(event, game_state=predicted_state, action_queue=action_queue)
                if action:
                    return action # The component handled the event and produced an action.

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    return self._handle_mouse_down(event.pos, predicted_state, action_queue)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: # Left click
                    return self._handle_mouse_up(event.pos, predicted_state, action_queue)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event.pos, event.buttons, action_queue)

        return None

    def _is_in_main_view(self, mouse_pos):
        """Checks if the mouse is in the main game view area (not the side panel)."""
        return self.ui_manager.main_view_rect.collidepoint(mouse_pos)

    def handle_lobby_input(self, events: list, ui_manager: UIManager) -> Optional[dict]:
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

    def _handle_mouse_down(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list):
        """Handles the moment the left mouse button is pressed."""
        # The logic for splitter drags is now handled by the SidePanelComponent.
        # We only need to handle non-component logic here, like map dragging.

        # Check if the click is on a non-component UI element first
        if not self._is_in_main_view(mouse_pos):
            return None # Click was on the panel, which is handled by components

        # Check for clicks on UI elements like the 'X' button in the queue.
        # This needs to happen on MOUSEBUTTONDOWN because the UI might be re-rendered
        # before MOUSEBUTTONUP, causing a mismatch in rect positions.
        action = self._check_ui_element_clicks(mouse_pos)
        if action:
            return action

        # If the click is in the main view area, prepare for a potential drag.
        # We don't set is_dragging to True yet, that happens on mouse motion.
        if self._is_in_main_view(mouse_pos):
            self.ui_manager.drag_start_pos = mouse_pos
            if self.ui_manager.active_view == ActiveView.WORLD_MAP:
                self.ui_manager.drag_start_camera_offset = self.ui_manager.camera_offset
            elif self.ui_manager.active_view == ActiveView.CITY_VIEW:
                self.ui_manager.drag_start_camera_offset = self.ui_manager.city_camera_offset

    def _handle_mouse_up(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list) -> Optional[dict]:
        """Handles the moment the left mouse button is released."""
        # Splitter drag release is handled by the component.
        if self.ui_manager.is_dragging_splitter:
            return None

        was_dragging = self.ui_manager.is_dragging
        self.ui_manager.is_dragging = False
        self.ui_manager.drag_start_pos = None # Reset drag start info
        self.ui_manager.drag_start_camera_offset = None

        # If we were dragging, the action is over. If not, it was a click.
        if not was_dragging:
            return self._handle_mouse_click(mouse_pos, state, action_queue)
        return None

    def _handle_mouse_motion(self, mouse_pos: tuple[int, int], buttons: tuple, action_queue: list):
        """Handles mouse movement, specifically for dragging the map."""
        from nightfall.core.common.datatypes import Position
        # If we are dragging a splitter, don't also drag the map
        if self.ui_manager.is_dragging_splitter or self.ui_manager.is_dragging_queue_splitter:
            # This is now handled by the SidePanelComponent's event handler
            return

        # --- Handle Hover Effects ---
        # This is now handled by the BuildQueueComponent
        
        # A drag only starts if the mouse moves while the button is down,
        # and a drag start position has been recorded.
        if self.ui_manager.drag_start_pos and buttons[0]:
            from nightfall.client.renderer import WORLD_TILE_SIZE, CITY_TILE_SIZE

            dx = mouse_pos[0] - self.ui_manager.drag_start_pos[0]
            dy = mouse_pos[1] - self.ui_manager.drag_start_pos[1]
            
            self.ui_manager.is_dragging = True # A drag has officially started
            start_offset = self.ui_manager.drag_start_camera_offset

            new_x = start_offset.x - dx
            new_y = start_offset.y - dy

            if self.ui_manager.active_view == ActiveView.WORLD_MAP:
                game_map = self.ui_manager.game_state_for_input.game_map
                max_x = game_map.width * WORLD_TILE_SIZE - self.ui_manager.main_view_rect.width
                max_y = game_map.height * WORLD_TILE_SIZE - (self.ui_manager.main_view_rect.height - self.ui_manager.top_bar_rect.height)
                clamped_x = max(0, min(new_x, max_x))
                clamped_y = max(0, min(new_y, max_y))
                self.ui_manager.camera_offset = Position(clamped_x, clamped_y)
            elif self.ui_manager.active_view == ActiveView.CITY_VIEW:
                city_id = self.ui_manager.viewed_city_id
                city = self.ui_manager.game_state_for_input.cities.get(city_id)
                if city: # Clamp dragging to city map boundaries
                    city_map = city.city_map
                    max_x = city_map.width * CITY_TILE_SIZE - self.ui_manager.main_view_rect.width
                    max_y = city_map.height * CITY_TILE_SIZE - (self.ui_manager.main_view_rect.height - self.ui_manager.top_bar_rect.height)
                    clamped_x = max(0, min(new_x, max_x))
                    clamped_y = max(0, min(new_y, max_y))
                    self.ui_manager.city_camera_offset = Position(clamped_x, clamped_y)

    def _check_ui_element_clicks(self, mouse_pos: tuple[int, int]) -> Optional[dict]:
        """
        Checks for clicks on discrete UI elements that should respond instantly.
        This is separate from _handle_mouse_click to be called on MOUSEBUTTONDOWN.
        """
        # This logic is now handled by the BuildQueueComponent's event handler.
        # This function can be removed if no other elements use it.

        return None


    def _handle_mouse_click(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list) -> Optional[dict]:
        """Handles a single, discrete mouse click (not a drag)."""
        from nightfall.core.common.datatypes import Position
        # 1. Check global buttons first (End Day, Exit)
        # This logic is now handled by components.
        
        # 2. Check top bar view-switching buttons
        for name, rect in self.ui_manager.top_bar_buttons.items():
            if rect.collidepoint(mouse_pos):
                if name == "view_world":
                    self.ui_manager.active_view = ActiveView.WORLD_MAP
                    self.ui_manager.clear_context_menu()
                elif name == "view_city" and self.ui_manager.viewed_city_id:
                    self.ui_manager.active_view = ActiveView.CITY_VIEW
                return None # View changed, no server action needed.

        # 3. Handle view-specific clicks
        if self.ui_manager.active_view == ActiveView.WORLD_MAP:
            return self._handle_world_map_click(mouse_pos, state)
        elif self.ui_manager.active_view == ActiveView.CITY_VIEW:
            return self._handle_city_view_click(mouse_pos, state, action_queue)
        return None

    def _handle_world_map_click(self, mouse_pos: tuple[int, int], state: GameState) -> Optional[dict]:
        """Handles clicks when in the World Map view."""
        from nightfall.client.renderer import WORLD_TILE_SIZE
        
        world_x = mouse_pos[0] + self.ui_manager.camera_offset.x
        world_y = mouse_pos[1] - self.ui_manager.top_bar_rect.height + self.ui_manager.camera_offset.y
        grid_x, grid_y = world_x // WORLD_TILE_SIZE, world_y // WORLD_TILE_SIZE
        clicked_pos = Position(grid_x, grid_y)

        # Check if a city was clicked
        clicked_city = None
        for city in state.cities.values():
            if city.position == clicked_pos:
                clicked_city = city
                break
        
        if clicked_city:
            current_time = pygame.time.get_ticks()
            # Check for double-click
            if clicked_pos == self.last_click_pos and current_time - self.last_click_time < 500:
                print(f"[CLIENT] Double-clicked on city: {clicked_city.name}. Switching to city view.")
                self.ui_manager.active_view = ActiveView.CITY_VIEW
                self.last_click_pos = None # Reset double-click state
            else: # Single click
                print(f"[CLIENT] Selected city: {clicked_city.name}.")
                self.ui_manager.viewed_city_id = clicked_city.id
            self.last_click_time = current_time
            self.last_click_pos = clicked_pos
        return None

    def _handle_city_view_click(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list) -> Optional[dict]:
        """Handles clicks when in the City View."""
        # Check for clicks on various UI elements within the city view
        if self.ui_manager.context_menu and self.ui_manager.context_menu['rect'].collidepoint(mouse_pos):
            return self._handle_context_menu_click(mouse_pos, state, action_queue)

        # Note: We don't have remove buttons for the unit queue yet, so no input handling is needed there.

        grid_pos = self.ui_manager.screen_to_grid(mouse_pos)
        if grid_pos:
            # Use the currently viewed city ID
            self._handle_city_tile_click(grid_pos, state, self.ui_manager.viewed_city_id, action_queue)

        return None

    def _handle_city_tile_click(self, grid_pos: Position, state: GameState, city_id: str, action_queue: list):
        """Sets the context menu based on a click on a city tile."""
        city = state.cities[city_id]
        tile = city.city_map.get_tile(grid_pos.x, grid_pos.y)
        if tile:
            self.ui_manager.set_context_menu_for_tile(grid_pos, tile, state, city_id, action_queue)

    def _handle_context_menu_click(self, mouse_pos: tuple[int, int], state: GameState, action_queue: list) -> Optional[dict]:
        """Handles a click within an active context menu."""
        from nightfall.core.actions.city_actions import (
            BuildBuildingAction, UpgradeBuildingAction, DemolishAction
        )
        selected_pos = self.ui_manager.context_menu['position']
        
        for option in self.ui_manager.context_menu['options']:
            if option['rect'].collidepoint(mouse_pos):
                # If the action is disabled, do nothing but close the menu.
                if not option['is_enabled']:
                    print(f"[CLIENT] Action disabled: {option.get('disabled_reason', 'Not enough resources.')}")
                    self.ui_manager.clear_context_menu()
                    return None

                action_type = option['action']

                # Handle cancellation first, as it's a special case that bypasses the queue check.
                if action_type == 'cancel_action':
                    self.ui_manager.clear_context_menu()
                    return {"type": "remove_action", "index": option['action_index']}

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
