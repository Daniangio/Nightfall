from typing import Optional
from nightfall.core.common.datatypes import Position
from nightfall.client.config_ui import FONT_S, FONT_M, TOP_BAR_HEIGHT, SPLITTER_WIDTH, QUEUE_SPACING, MIN_ZOOM, MAX_ZOOM, WORLD_TILE_SIZE, ZOOM_INCREMENT, TILE_WIDTH, TILE_HEIGHT
from nightfall.client.enums import ActiveView
from nightfall.client.ui.components.panel_component import SidePanelComponent

from nightfall.core.common.enums import BuildingType, CityTerrainType
from nightfall.core.common.game_data import BUILDING_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall.core.state.game_state import GameState
import pygame

# --- Default Layout Constants ---
# These are used for initialization and as reference points for resizing.
DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT = 1280, 720 # This can stay here as it's for the initial window
DEFAULT_SIDE_PANEL_WIDTH = 320
MIN_SIDE_PANEL_WIDTH = 250
MAX_SIDE_PANEL_WIDTH_RATIO = 0.6 # 60% of screen width

class UIManager:
    """
    Manages the overall UI state, layout, and coordination between components.
    It holds the state that multiple components might need to reference.
    """
    def __init__(self):
        self.selected_city_tile: Optional[Position] = None
        
        # UI State
        self.active_view = ActiveView.WORLD_MAP
        self.viewed_city_id: Optional[str] = None
        self.font_s = FONT_S
        self.orders_sent = False
        self.font_m = FONT_M
        self.game_state_for_input: Optional[GameState] = None # Hack for input handler

        # Camera and dragging state for map views
        self.camera_offset = Position(0, 0)
        self.city_camera_offset = Position(0, 0)
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_start_camera_offset = None

        # --- Zoom State ---
        self.world_zoom_level = 1.0
        self.city_zoom_level = 1.0


        # --- UI Rects ---
        # These will be recalculated on window resize
        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_height = DEFAULT_SCREEN_HEIGHT
        self.main_view_rect = pygame.Rect(0, 0, 0, 0)
        self.side_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.top_bar_rect = pygame.Rect(0, 0, 0, 0)
        self.resource_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.build_queue_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.queue_splitter_rect = pygame.Rect(0, 0, 0, 0)
        self.unit_queue_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.splitter_rect = pygame.Rect(0, 0, 0, 0)

        # --- UI Buttons ---
        # These are dictionaries of name -> rect, also recalculated on resize
        self.buttons = {}
        self.top_bar_buttons = {}

        # Action Queue UI State
        self.queue_item_rects = []
        self.queue_item_remove_button_rects = []
        self.queue_item_up_button_rects = []
        self.queue_item_down_button_rects = []
        self.hovered_remove_button_index: Optional[int] = None
        self.hovered_up_button_index: Optional[int] = None
        self.hovered_down_button_index: Optional[int] = None
        self.predicted_production = None

        # --- Scroll State ---
        self.build_queue_scroll_offset = 0
        self.unit_queue_scroll_offset = 0
        self.build_queue_visible_items = 0
        self.unit_queue_visible_items = 0

        # --- Component-Based UI ---
        self.components = []
        self.side_panel_component = SidePanelComponent(self)
        # Note: The renderer will call side_panel_component.draw() directly.
        self.components.append(self.side_panel_component)


        # Lobby UI State
        self.lobby_buttons = {} # "create" or session_id -> rect

        # --- Resizable Panel State ---
        self.side_panel_width = DEFAULT_SIDE_PANEL_WIDTH
        self.is_dragging_splitter = False
        self.queue_split_ratio = 0.5 # Ratio of space for the TOP (build) queue. 0.0 to 1.0
        self.is_dragging_queue_splitter = False

        # Initial layout calculation
        self.on_resize(self.screen_width, self.screen_height)

    def center_camera_on_map(self, game_map):
        """Sets the camera offset to center the map in the current view."""
        if self.active_view == ActiveView.WORLD_MAP:
            zoom = self.world_zoom_level
            map_pixel_width = game_map.width * WORLD_TILE_SIZE * zoom
            map_pixel_height = game_map.height * WORLD_TILE_SIZE * zoom
            view_center_x = self.main_view_rect.width / 2
            view_center_y = (self.main_view_rect.height - TOP_BAR_HEIGHT) / 2
            
            # To center the map, the camera's top-left should be offset from the map's center
            # by half the view's size.
            self.camera_offset = Position(map_pixel_width / 2 - view_center_x, map_pixel_height / 2 - view_center_y)

        elif self.active_view == ActiveView.CITY_VIEW:
            zoom = self.city_zoom_level
            map_pixel_width = game_map.width * TILE_WIDTH * zoom
            map_pixel_height = game_map.height * TILE_HEIGHT * zoom
            view_center_x = self.main_view_rect.width / 2
            view_center_y = (self.main_view_rect.height - TOP_BAR_HEIGHT) / 2

            self.city_camera_offset = Position(map_pixel_width / 2 - view_center_x, map_pixel_height / 2 - view_center_y)

    def on_resize(self, width: int, height: int, action_queue: Optional[list] = None):
        """Recalculates all UI element positions and sizes based on the new window size."""
        # Maintain the panel's width ratio during window resize
        width_ratio = width / self.screen_width if self.screen_width > 0 else 1
        self.side_panel_width = int(self.side_panel_width * width_ratio)

        self.screen_width = width
        self.screen_height = height

        # Clamp the panel width to its min/max
        max_panel_width = self.screen_width * MAX_SIDE_PANEL_WIDTH_RATIO
        self.side_panel_width = max(MIN_SIDE_PANEL_WIDTH, min(self.side_panel_width, max_panel_width))

        main_view_width = self.screen_width - self.side_panel_width
        self.main_view_rect = pygame.Rect(0, 0, main_view_width, self.screen_height)
        self.side_panel_rect = pygame.Rect(main_view_width, 0, self.side_panel_width, self.screen_height)
        self.top_bar_rect = pygame.Rect(0, 0, main_view_width, TOP_BAR_HEIGHT)
        self.splitter_rect = pygame.Rect(main_view_width - (SPLITTER_WIDTH // 2), 0, SPLITTER_WIDTH, self.screen_height)

        self.top_bar_buttons['view_world'] = pygame.Rect(10, 5, 100, 25)
        self.top_bar_buttons['view_city'] = pygame.Rect(120, 5, 100, 25)
        self.buttons['exit_session'] = pygame.Rect(self.side_panel_rect.right - 130, 5, 120, 25)
        self.resource_panel_rect = pygame.Rect(self.side_panel_rect.x + 10, 50, self.side_panel_rect.width - 20, 95)
        
        self.update_queue_layouts(action_queue if action_queue is not None else [])

    def update_queue_layouts(self, build_action_queue: list):
        """Calculates the layout for the build and unit queue panels."""
        # --- Constants for queue panels ---
        queue_header_height = 30 # Space for title
        item_height = 25 # Height of one queue item
        scroll_button_space = 35 # Extra padding needed if scroll buttons are visible
        min_panel_height = queue_header_height
        
        # --- Calculate available space for both queues ---
        total_available_y_start = self.resource_panel_rect.bottom + 10
        total_available_y_end = self.screen_height - 10 # End of the panel
        total_available_height = total_available_y_end - total_available_y_start - QUEUE_SPACING

        # --- Determine required height for each queue based on content ---
        build_queue_len = len(build_action_queue)
        unit_queue_len = 0 # We need to get this from the game state
        if self.game_state_for_input and self.viewed_city_id:
            city = self.game_state_for_input.cities.get(self.viewed_city_id)
            if city:
                unit_queue_len = len(city.recruitment_queue)

        build_content_height = min_panel_height + (build_queue_len * item_height)
        unit_content_height = min_panel_height + (unit_queue_len * item_height)

        # If content fits, shrink panels to content size to create the "dynamic" feel
        if build_content_height + unit_content_height < total_available_height:
            build_queue_height = build_content_height
            unit_queue_height = unit_content_height
            # IMPORTANT: Update the split ratio to match the content-fitted size.
            # This prevents the layout from snapping back to the old ratio when content overflows later.
            if total_available_height > 0:
                 # We calculate the ratio based on the bottom of the unit queue panel
                 self.queue_split_ratio = build_queue_height / total_available_height
        else:
            # --- Allocate space based on the split ratio if content overflows ---
            build_queue_height = max(min_panel_height, total_available_height * self.queue_split_ratio)
            unit_queue_height = max(min_panel_height, total_available_height * (1 - self.queue_split_ratio))

        # --- Set final Rects ---
        panel_x = self.side_panel_rect.x + 10
        panel_width = self.side_panel_rect.width - 20
        self.build_queue_panel_rect = pygame.Rect(panel_x, total_available_y_start, panel_width, build_queue_height)
        
        splitter_y = self.build_queue_panel_rect.bottom + (QUEUE_SPACING // 2)
        self.queue_splitter_rect = pygame.Rect(panel_x, splitter_y, panel_width, SPLITTER_WIDTH)
        self.unit_queue_panel_rect = pygame.Rect(panel_x, self.queue_splitter_rect.bottom + (QUEUE_SPACING // 2), panel_width, unit_queue_height)

        # --- Calculate visible items (and if scroll buttons are needed) ---
        build_panel_content_area = self.build_queue_panel_rect.height - queue_header_height
        potential_visible_items = max(0, build_panel_content_area // item_height)
        # If scrolling will be needed, reserve space for the buttons, which might reduce the number of visible items.
        if build_queue_len > potential_visible_items:
            self.build_queue_visible_items = max(0, (build_panel_content_area - scroll_button_space) // item_height)
        else:
            self.build_queue_visible_items = potential_visible_items

        unit_panel_content_area = self.unit_queue_panel_rect.height - queue_header_height
        self.unit_queue_visible_items = max(0, unit_panel_content_area // item_height)
        if unit_queue_len > self.unit_queue_visible_items: # If scrolling is needed
            self.unit_queue_visible_items = max(0, (unit_panel_content_area - scroll_button_space) // item_height)

        self.buttons['build_queue_scroll_up'] = pygame.Rect(self.build_queue_panel_rect.right - 40, self.build_queue_panel_rect.y + 10, 20, 20)
        self.buttons['build_queue_scroll_down'] = pygame.Rect(self.build_queue_panel_rect.right - 40, self.build_queue_panel_rect.bottom - 30, 20, 20)

    def update_side_panel_width(self, new_width: int, action_queue: list):
        self.side_panel_width = new_width
        self.on_resize(self.screen_width, self.screen_height, action_queue)
    
    def get_city_tile_rect(self, x: int, y: int) -> pygame.Rect:
        """Calculates the on-screen rect for a city tile, including zoom and camera offset."""
        zoomed_tile_width = TILE_WIDTH * self.city_zoom_level
        zoomed_tile_height = TILE_HEIGHT * self.city_zoom_level
        screen_x = x * zoomed_tile_width - self.city_camera_offset.x
        screen_y = y * zoomed_tile_height - self.city_camera_offset.y + TOP_BAR_HEIGHT
        return pygame.Rect(screen_x, screen_y, zoomed_tile_width, zoomed_tile_height)

    def clear_selection(self):
        """Clears the selected tile and resets the side panel view."""
        self.selected_city_tile = None
        self.side_panel_component.current_view = self.side_panel_component.SidePanelView.DEFAULT
        self.side_panel_component.selected_building_for_details = None

    def screen_to_grid(self, screen_pos_in: tuple[int, int]) -> Optional[Position]:
        """Converts a screen coordinate to a city grid coordinate, if applicable."""
        # Check if click is within the main view area, below the top bar
        if not self.main_view_rect.collidepoint(screen_pos_in) or screen_pos_in[1] < TOP_BAR_HEIGHT:
            return None

        zoomed_tile_width = TILE_WIDTH * self.city_zoom_level
        zoomed_tile_height = TILE_HEIGHT * self.city_zoom_level

        # Adjust for camera offset
        world_x = screen_pos_in[0] + self.city_camera_offset.x
        world_y = screen_pos_in[1] - TOP_BAR_HEIGHT + self.city_camera_offset.y

        grid_x = int(world_x // zoomed_tile_width)
        grid_y = int(world_y // zoomed_tile_height)
        return Position(grid_x, grid_y)

    def get_build_queue_item_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the entire queue item row."""
        # item_index here is the VISIBLE index (0, 1, 2...)
        visible_index = item_index
        item_y = self.build_queue_panel_rect.y + 30 + visible_index * 25
        return pygame.Rect(self.build_queue_panel_rect.x + 10, item_y, self.build_queue_panel_rect.width - 20, 25)

    def get_build_queue_item_remove_button_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the 'X' remove button on a queue item."""
        item_rect = self.get_build_queue_item_rect(item_index)
        return pygame.Rect(item_rect.right - 25, item_rect.y, 20, 25)

    def get_build_queue_item_up_button_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the 'up' arrow button on a queue item."""
        remove_rect = self.get_build_queue_item_remove_button_rect(item_index)
        return pygame.Rect(remove_rect.left - 25, remove_rect.y, 20, 25)

    def get_build_queue_item_down_button_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the 'down' arrow button on a queue item."""
        up_rect = self.get_build_queue_item_up_button_rect(item_index)
        return pygame.Rect(up_rect.left - 25, up_rect.y, 20, 25)
    
    def update_action_queue_ui(self, action_queue: list):
        """Updates the list of rects for the *visible* action queue 'remove' buttons."""
        self.queue_item_rects.clear()
        self.queue_item_remove_button_rects.clear()
        self.queue_item_up_button_rects.clear()
        self.queue_item_down_button_rects.clear()

        # Clamp scroll offset
        max_scroll = max(0, len(action_queue) - self.build_queue_visible_items)
        self.build_queue_scroll_offset = max(0, min(self.build_queue_scroll_offset, max_scroll))
        self.update_queue_layouts(action_queue) # Recalculate layout based on new queue length

        start_index = self.build_queue_scroll_offset
        end_index = self.build_queue_scroll_offset + self.build_queue_visible_items

        for i, absolute_index in enumerate(range(start_index, min(end_index, len(action_queue)))):
            # Pass the visible index (i) to get the correct screen position
            self.queue_item_rects.append(self.get_build_queue_item_rect(i))
            self.queue_item_remove_button_rects.append(self.get_build_queue_item_remove_button_rect(i))
            self.queue_item_up_button_rects.append(self.get_build_queue_item_up_button_rect(i))
            self.queue_item_down_button_rects.append(self.get_build_queue_item_down_button_rect(i))

    def _format_time(self, seconds: float) -> str:
        """Formats seconds into a string like '[1m 25s]'."""
        if seconds <= 0: return ""
        hours = int(seconds // (60 * 60))
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{hours}h {mins}m {secs}s"

    def update_lobby_buttons(self, sessions: dict):
        """Create and position buttons for the lobby screen."""
        # sessions here is just the keys, not the full dict
        self.lobby_buttons.clear()
        y_pos = 150
        # Button for creating a new session
        self.lobby_buttons["create"] = pygame.Rect(self.screen_width / 2 - 150, y_pos, 300, 50)
        y_pos += 80

        # Buttons for each available session
        for i, session_id in enumerate(sessions):
            self.lobby_buttons[session_id] = pygame.Rect(self.screen_width / 2 - 150, y_pos + i * 60, 300, 50)

    def clear_lobby_buttons(self):
        self.lobby_buttons.clear()
