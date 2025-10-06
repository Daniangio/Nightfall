from typing import Optional
from nightfall.core.common.datatypes import Position
from nightfall.client.enums import ActiveView
from nightfall.client.ui.components.panel_component import SidePanelComponent

from nightfall.core.common.enums import BuildingType, CityTerrainType
from nightfall.core.common.game_data import BUILDING_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall.core.state.game_state import GameState
import pygame

# --- Default Layout Constants ---
# These are used for initialization and as reference points for resizing.
DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT = 640, 480
TOP_BAR_HEIGHT = 40
DEFAULT_SIDE_PANEL_WIDTH = 450
MIN_SIDE_PANEL_WIDTH = 300
MAX_SIDE_PANEL_WIDTH_RATIO = 0.6 # 60% of screen width
SPLITTER_WIDTH = 8

class UIManager:
    """
    Manages the overall UI state, layout, and coordination between components.
    It holds the state that multiple components might need to reference.
    """
    def __init__(self):
        self.selected_city_tile: Optional[Position] = None
        self.context_menu: Optional[dict] = None
        
        # UI State
        self.active_view = ActiveView.WORLD_MAP
        self.viewed_city_id: Optional[str] = None
        self.font_s = pygame.font.Font(None, 24)
        self.orders_sent = False
        self.font_m = pygame.font.Font(None, 32)
        self.game_state_for_input: Optional[GameState] = None # Hack for input handler

        # Camera and dragging state for map views
        self.camera_offset = Position(0, 0)
        self.city_camera_offset = Position(0, 0)
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_start_camera_offset = None

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
        self.hovered_remove_button_index: Optional[int] = None
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

        self.top_bar_buttons['view_world'] = pygame.Rect(10, 5, 120, 30)
        self.top_bar_buttons['view_city'] = pygame.Rect(140, 5, 120, 30)
        self.buttons['exit_session'] = pygame.Rect(self.side_panel_rect.right - 160, 5, 150, 30)
        self.resource_panel_rect = pygame.Rect(self.side_panel_rect.x + 10, 100, self.side_panel_rect.width - 20, 120)
        
        self.update_queue_layouts(action_queue if action_queue is not None else [])

    def update_queue_layouts(self, build_action_queue: list):
        """Calculates the layout for the build and unit queue panels."""
        # --- Constants for queue panels ---
        queue_header_height = 40 # Space for title
        item_height = 30 # Height of one queue item
        scroll_button_space = 35 # Extra padding needed if scroll buttons are visible
        min_panel_height = queue_header_height
        
        # --- Calculate available space for both queues ---
        total_available_y_start = self.resource_panel_rect.bottom + 10
        total_available_y_end = self.screen_height - 10 # End of the panel
        total_available_height = total_available_y_end - total_available_y_start

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
        self.queue_splitter_rect = pygame.Rect(panel_x, self.build_queue_panel_rect.bottom, panel_width, SPLITTER_WIDTH)
        self.unit_queue_panel_rect = pygame.Rect(panel_x, self.queue_splitter_rect.bottom, panel_width, unit_queue_height)

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

    def get_city_tile_rect(self, x, y):
        from nightfall.client.renderer import CITY_TILE_SIZE
        return pygame.Rect(x * CITY_TILE_SIZE - self.city_camera_offset.x, y * CITY_TILE_SIZE - self.city_camera_offset.y + TOP_BAR_HEIGHT, CITY_TILE_SIZE, CITY_TILE_SIZE)

    def get_context_menu_pos(self, item_index=0):
        if not self.selected_city_tile: return (0,0)
        from nightfall.client.renderer import CITY_TILE_SIZE
        base_pos = ( (self.selected_city_tile.x + 1) * CITY_TILE_SIZE - self.city_camera_offset.x + 5, self.selected_city_tile.y * CITY_TILE_SIZE - self.city_camera_offset.y + TOP_BAR_HEIGHT )
        return (base_pos[0], base_pos[1] + item_index * 45)

    def set_context_menu_for_tile(self, grid_pos: Position, tile, game_state: GameState, city_id: str, action_queue: list):
        """Sets the state for the context menu based on the selected tile."""
        self.selected_city_tile = grid_pos
        options_data = self._get_context_menu_options_data(tile, game_state, city_id, action_queue, grid_pos)

        if not options_data:
            self.clear_context_menu()
            return

        menu_options = []
        padding_x = 20  # 10px on each side
        item_height = 40

        for i, data in enumerate(options_data):
            text_width, _ = self.font_s.size(data['text'])
            item_width = text_width + padding_x
            menu_options.append({
                'text': data['text'],
                'rect': pygame.Rect(self.get_context_menu_pos(i), (item_width, item_height)),
                'action': data['action'],
                'building_type': data.get('building_type'),
                'is_enabled': data.get('is_enabled', True),
                'disabled_reason': data.get('disabled_reason'),
                'action_index': data.get('action_index') # Pass the index for cancel actions
            })
        
        # Calculate the full bounding rect for the menu
        full_rect = menu_options[0]['rect'].unionall([opt['rect'] for opt in menu_options])

        self.context_menu = {
            'position': grid_pos,
            'rect': full_rect,
            'options': menu_options
        }

    def clear_context_menu(self):
        self.context_menu = None
        self.selected_city_tile = None

    def _format_cost(self, cost: Optional[Position]) -> str:
        """Formats a Resources object into a string like '(F:10 W:20 I:5)'."""
        if not cost: return ""
        parts = []
        if cost.food > 0: parts.append(f"F:{cost.food}")
        if cost.wood > 0: parts.append(f"W:{cost.wood}")
        if cost.iron > 0: parts.append(f"I:{cost.iron}")
        return f" ({' '.join(parts)})" if parts else ""

    def _format_time(self, seconds: float) -> str:
        """Formats seconds into a string like '[1m 25s]'."""
        if seconds <= 0: return ""
        hours = int(seconds // (60 * 60))
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{hours}h {mins}m {secs}s"

    def _get_context_menu_options_data(self, tile, game_state: GameState, city_id: str, action_queue: list, grid_pos: Position):
        """Generates a list of possible actions for a tile."""
        options = []
        city = game_state.cities[city_id]
        player_resources = city.resources

        # Check if an action is already queued for this tile and find its index
        action_index_in_queue = -1
        for i, action in enumerate(action_queue):
            if hasattr(action, 'position') and action.position == grid_pos:
                action_index_in_queue = i
                break

        if action_index_in_queue != -1:
            # If an action is queued, the only option is to cancel it.
            return [{
                'text': "Cancel Queued Action",
                'action': 'cancel_action',
                'is_enabled': True,
                'action_index': action_index_in_queue,
                'disabled_reason': None
            }]

        if tile.building:
            # --- Upgrade Action (for all buildings including Citadel) ---
            next_level = tile.building.level + 1
            building_data = BUILDING_DATA.get(tile.building.type, {})
            upgrade_data = building_data.get('upgrade', {}).get(next_level)

            if upgrade_data:
                cost = upgrade_data.get('cost')
                time = upgrade_data.get('time')
                can_afford_res = player_resources.can_afford(cost)
                can_upgrade = can_afford_res
                
                reason = ""
                if not can_afford_res: reason = "Not enough resources."

                upgrade_option = {
                    'text': f"Upgrade (Lvl {next_level}){self._format_cost(cost)}{self._format_time(time)}",
                    'action': 'upgrade',
                    'is_enabled': can_upgrade,
                    'disabled_reason': reason
                }
                options.append(upgrade_option)
            else: # Max level reached
                options.append({
                    'text': "Upgrade (Max Level)",
                    'action': 'upgrade',
                    'is_enabled': False,
                    'disabled_reason': "This building has reached its maximum level."
                })

            # --- Demolish Action (not for Citadel) ---
            if tile.building.type != BuildingType.CITADEL:
                # Demolish action
                cost = DEMOLISH_COST_BUILDING['cost']
                time = DEMOLISH_COST_BUILDING['time']
                can_afford_res = player_resources.can_afford(cost)
                can_demolish = can_afford_res

                demolish_option = {
                    'text': f"Demolish{self._format_cost(cost)}{self._format_time(time)}",
                    'action': 'demolish', 
                    'is_enabled': can_demolish}
                if not can_demolish:
                    demolish_option['disabled_reason'] = "Not enough resources."
                options.append(demolish_option)
        else: # No building
            if tile.terrain == CityTerrainType.GRASS:
                # Any production building can be built on grass
                buildable = [BuildingType.FARM, BuildingType.LUMBER_MILL, BuildingType.IRON_MINE, BuildingType.BARRACKS]
                for b_type in buildable:
                    building_data = BUILDING_DATA.get(b_type, {})
                    build_cost = building_data.get('build', {}).get('cost')
                    build_time = building_data.get('build', {}).get('time')

                    can_afford_res = build_cost and player_resources.can_afford(build_cost)
                    has_building_slot = city.num_buildings < city.max_buildings
                    can_build = can_afford_res and has_building_slot

                    reason = ""
                    if not has_building_slot: reason = "Building limit reached."
                    elif not can_afford_res: reason = "Not enough resources."

                    building_name = b_type.name.replace('_', ' ').title()
                    build_option = {
                        'text': f"Build {building_name}{self._format_cost(build_cost)}{self._format_time(build_time)}",
                        'action': 'build',
                        'building_type': b_type,
                        'is_enabled': can_build,
                        'disabled_reason': reason
                    }
                    options.append(build_option)

            elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                # Demolishing plots
                cost = DEMOLISH_COST_RESOURCE['cost']
                time = DEMOLISH_COST_RESOURCE['time']
                can_afford_res = player_resources.can_afford(cost)
                can_demolish = can_afford_res

                demolish_option = {
                    'text': f"Demolish Plot{self._format_cost(cost)}{self._format_time(time)}",
                    'action': 'demolish', 
                    'is_enabled': can_demolish}
                if not can_demolish:
                    demolish_option['disabled_reason'] = "Not enough resources."
                options.append(demolish_option)

        return options

    def screen_to_grid(self, screen_pos: tuple[int, int]) -> Optional[Position]:
        """Converts a screen coordinate to a city grid coordinate, if applicable."""
        from nightfall.client.renderer import CITY_TILE_SIZE

        # Check if click is within the main view area, below the top bar
        if not self.main_view_rect.collidepoint(screen_pos) or screen_pos[1] < TOP_BAR_HEIGHT:
            return None

        local_x, local_y = screen_pos[0] + self.city_camera_offset.x, screen_pos[1] - TOP_BAR_HEIGHT + self.city_camera_offset.y

        grid_x = local_x // CITY_TILE_SIZE
        grid_y = local_y // CITY_TILE_SIZE
        return Position(grid_x, grid_y)

    def get_build_queue_item_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the entire queue item row."""
        # item_index here is the VISIBLE index (0, 1, 2...)
        visible_index = item_index
        item_y = self.build_queue_panel_rect.y + 40 + visible_index * 30
        return pygame.Rect(self.build_queue_panel_rect.x + 10, item_y, self.build_queue_panel_rect.width - 20, 25)

    def get_build_queue_item_remove_button_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the 'X' remove button on a queue item."""
        item_rect = self.get_build_queue_item_rect(item_index)
        return pygame.Rect(item_rect.right - 25, item_rect.y, 20, 25)
    
    def update_action_queue_ui(self, action_queue: list):
        """Updates the list of rects for the *visible* action queue 'remove' buttons."""
        self.queue_item_rects.clear()
        self.queue_item_remove_button_rects.clear()

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

    def update_lobby_buttons(self, sessions: dict):
        """Create and position buttons for the lobby screen."""
        self.lobby_buttons.clear()
        y_pos = 150
        # Button for creating a new session
        self.lobby_buttons["create"] = pygame.Rect(100, y_pos, 300, 50)
        y_pos += 80

        # Buttons for each available session
        for i, session_id in enumerate(sessions.keys()):
            self.lobby_buttons[session_id] = pygame.Rect(100, y_pos + i * 60, 300, 50)

    def clear_lobby_buttons(self):
        self.lobby_buttons.clear()
