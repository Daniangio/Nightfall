from typing import Optional
from nightfall.core.common.datatypes import Position
from nightfall.client.enums import ActiveView
from nightfall.core.common.enums import BuildingType, CityTerrainType
from nightfall.core.common.game_data import BUILDING_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall.core.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction
from nightfall.core.state.game_state import GameState
import pygame

# --- Default Layout Constants ---
# These are used for initialization and as reference points for resizing.
DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT = 960, 640
TOP_BAR_HEIGHT = 40
DEFAULT_SIDE_PANEL_WIDTH = 450
MIN_SIDE_PANEL_WIDTH = 300
MAX_SIDE_PANEL_WIDTH_RATIO = 0.6 # 60% of screen width
SPLITTER_WIDTH = 8

class UIManager:
    def __init__(self):
        self.selected_city_tile: Optional[Position] = None
        self.context_menu: Optional[dict] = None
        
        # UI State
        self.active_view = ActiveView.WORLD_MAP
        self.viewed_city_id: Optional[str] = None
        self.font_s = pygame.font.Font(None, 24)
        self.orders_sent = False
        self.is_ready = False
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
        self.queue_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.splitter_rect = pygame.Rect(0, 0, 0, 0)

        # --- UI Buttons ---
        # These are dictionaries of name -> rect, also recalculated on resize
        self.buttons = {}
        self.top_bar_buttons = {}

        # Action Queue UI State
        self.queue_item_rects = []
        self.queue_item_remove_button_rects = []
        self.predicted_production = None

        # Lobby UI State
        self.lobby_buttons = {} # "create" or session_id -> rect

        # --- Resizable Panel State ---
        self.side_panel_width = DEFAULT_SIDE_PANEL_WIDTH
        self.is_dragging_splitter = False

        # Initial layout calculation
        self.on_resize(self.screen_width, self.screen_height)

    def on_resize(self, width: int, height: int):
        """Recalculates all UI element positions and sizes based on the new window size."""
        # Maintain the panel's width ratio during window resize
        width_ratio = width / self.screen_width if self.screen_width > 0 else 1
        self.side_panel_width = self.side_panel_width * width_ratio

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
        self.buttons['end_day'] = pygame.Rect(self.side_panel_rect.x + (self.side_panel_rect.width - 250) // 2, self.screen_height - 70, 250, 50)
        self.resource_panel_rect = pygame.Rect(self.side_panel_rect.x + 10, 100, self.side_panel_rect.width - 20, 120)
        self.queue_panel_rect = pygame.Rect(self.side_panel_rect.x + 10, self.resource_panel_rect.bottom + 10, self.side_panel_rect.width - 20, 300)

    def update_side_panel_width(self, new_width: int):
        self.side_panel_width = new_width
        self.on_resize(self.screen_width, self.screen_height)

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
                'disabled_reason': data.get('disabled_reason')
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
    
    def _format_ap_cost(self, ap_cost: int) -> str:
        return f" [AP:{ap_cost}]"

    def _get_context_menu_options_data(self, tile, game_state: GameState, city_id: str, action_queue: list, grid_pos: Position):
        """Generates a list of possible actions for a tile."""
        options = []
        city = game_state.cities[city_id]
        player_resources = city.resources

        # Check if an action is already queued for this tile
        is_tile_in_queue = any(hasattr(a, 'position') and a.position == grid_pos for a in action_queue)
        if is_tile_in_queue:
            # If an action is queued, all options are disabled. We can show a placeholder.
            return [{
                'text': "Action Queued",
                'action': 'none',
                'is_enabled': False,
                'disabled_reason': "An action for this tile is already in the queue."
            }]

        if tile.building:
            # --- Upgrade Action (for all buildings including Citadel) ---
            next_level = tile.building.level + 1
            building_data = BUILDING_DATA.get(tile.building.type, {})
            upgrade_data = building_data.get('upgrade', {}).get(next_level)
            ap_cost_upgrade = building_data.get('action_point_cost', 1)

            if upgrade_data:
                cost = upgrade_data.get('cost')
                can_afford_res = player_resources.can_afford(cost)
                can_afford_ap = city.action_points >= ap_cost_upgrade
                can_upgrade = can_afford_res and can_afford_ap
                
                reason = ""
                if not can_afford_res: reason = "Not enough resources."
                elif not can_afford_ap: reason = "Not enough Action Points."

                upgrade_option = {
                    'text': f"Upgrade (Lvl {next_level}){self._format_cost(cost)}{self._format_ap_cost(ap_cost_upgrade)}",
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
                ap_cost = DEMOLISH_COST_BUILDING['action_point_cost']
                can_afford_res = player_resources.can_afford(cost)
                can_afford_ap = city.action_points >= ap_cost
                can_demolish = can_afford_res and can_afford_ap

                demolish_option = {
                    'text': f"Demolish{self._format_cost(cost)}{self._format_ap_cost(ap_cost)}", 
                    'action': 'demolish', 
                    'is_enabled': can_demolish}
                if not can_demolish:
                    demolish_option['disabled_reason'] = "Not enough resources." if not can_afford_res else "Not enough Action Points."
                options.append(demolish_option)
        else: # No building
            if tile.terrain == CityTerrainType.GRASS:
                # Any production building can be built on grass
                buildable = [BuildingType.FARM, BuildingType.LUMBER_MILL, BuildingType.IRON_MINE, BuildingType.BARRACKS]
                for b_type in buildable:
                    building_data = BUILDING_DATA.get(b_type, {})
                    build_cost = building_data.get('build', {}).get('cost')
                    ap_cost = building_data.get('action_point_cost', 1)

                    can_afford_res = build_cost and player_resources.can_afford(build_cost)
                    can_afford_ap = city.action_points >= ap_cost
                    has_building_slot = city.num_buildings < city.max_buildings
                    can_build = can_afford_res and can_afford_ap and has_building_slot

                    reason = ""
                    if not has_building_slot: reason = "Building limit reached."
                    elif not can_afford_res: reason = "Not enough resources."
                    elif not can_afford_ap: reason = "Not enough Action Points."

                    building_name = b_type.name.replace('_', ' ').title()
                    build_option = {
                        'text': f"Build {building_name}{self._format_cost(build_cost)}{self._format_ap_cost(ap_cost)}",
                        'action': 'build',
                        'building_type': b_type,
                        'is_enabled': can_build,
                        'disabled_reason': reason
                    }
                    options.append(build_option)

            elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                # Demolishing plots
                cost = DEMOLISH_COST_RESOURCE['cost']
                ap_cost = DEMOLISH_COST_RESOURCE['action_point_cost']
                can_afford_res = player_resources.can_afford(cost)
                can_afford_ap = city.action_points >= ap_cost
                can_demolish = can_afford_res and can_afford_ap

                demolish_option = {
                    'text': f"Demolish Plot{self._format_cost(cost)}{self._format_ap_cost(ap_cost)}", 
                    'action': 'demolish', 
                    'is_enabled': can_demolish}
                if not can_demolish:
                    demolish_option['disabled_reason'] = "Not enough resources." if not can_afford_res else "Not enough Action Points."
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

    def get_queue_item_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the entire queue item row."""
        item_y = self.queue_panel_rect.y + 50 + item_index * 30
        return pygame.Rect(self.queue_panel_rect.x + 10, item_y, self.queue_panel_rect.width - 20, 25)

    def get_queue_item_remove_button_rect(self, item_index: int) -> pygame.Rect:
        """Gets the rect for the 'X' remove button on a queue item."""
        item_rect = self.get_queue_item_rect(item_index)
        return pygame.Rect(item_rect.right - 25, item_rect.y, 20, 25)

    def update_action_queue_ui(self, action_queue: list):
        """Updates the list of rects for the action queue 'remove' buttons."""
        self.queue_item_rects.clear()
        self.queue_item_remove_button_rects.clear()
        for i in range(len(action_queue)):
            self.queue_item_rects.append(self.get_queue_item_rect(i))
            self.queue_item_remove_button_rects.append(self.get_queue_item_remove_button_rect(i))

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
