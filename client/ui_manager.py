from nightfall_engine.common.datatypes import Position
from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction
from client.config import PLAYER_ID, CITY_ID
import pygame

# ... (layout constants) ...
WORLD_MAP_WIDTH = 600
UI_PANEL_WIDTH = 600

class UIManager:
    def __init__(self):
        self.selected_city_tile: Position | None = None
        self.context_menu: dict | None = None
        # UI State
        self.orders_sent = False
        self.is_ready = False
        # Main UI buttons for click detection
        self.buttons = {
            "end_day": pygame.Rect(WORLD_MAP_WIDTH + 20, 500, 200, 50),
            "exit_session": pygame.Rect(WORLD_MAP_WIDTH + 20, 560, 200, 50)
        }

        # Action Queue UI State
        self.queue_item_rects = []
        self.predicted_production = None

        # Lobby UI State
        self.lobby_buttons = {} # "create" or session_id -> rect

    # ... (existing get_*_rect methods) ...
    def get_city_tile_rect(self, x, y):
        from client.renderer import CITY_TILE_SIZE, SCREEN_HEIGHT, CITY_VIEW_HEIGHT
        return pygame.Rect(x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)

    def get_context_menu_pos(self, item_index=0):
        if not self.selected_city_tile: return (0,0)
        from client.renderer import CITY_TILE_SIZE, SCREEN_HEIGHT, CITY_VIEW_HEIGHT
        base_pos = ( (self.selected_city_tile.x + 1) * CITY_TILE_SIZE + 5, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + self.selected_city_tile.y * CITY_TILE_SIZE )
        return (base_pos[0], base_pos[1] + item_index * 45)

    def get_context_menu_item_rect(self, item_index):
        if not self.selected_city_tile: return None
        pos = self.get_context_menu_pos(item_index)
        return pygame.Rect(pos, (160, 40))

    def set_context_menu_for_tile(self, grid_pos: Position, tile):
        """Sets the state for the context menu based on the selected tile."""
        self.selected_city_tile = grid_pos
        options_data = self._get_context_menu_options_data(tile)

        if not options_data:
            self.clear_context_menu()
            return

        menu_options = []
        for i, data in enumerate(options_data):
            menu_options.append({
                'text': data['text'],
                'rect': self.get_context_menu_item_rect(i),
                'action': data['action'],
                'building_type': data.get('building_type')
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

    def _get_context_menu_options_data(self, tile):
        """Generates a list of possible actions for a tile."""
        options = []
        if tile.building:
            if tile.building.type != BuildingType.CITADEL:
                options.append({'text': f"Upgrade (Lvl {tile.building.level + 1})", 'action': 'upgrade'})
                options.append({'text': "Demolish", 'action': 'demolish'})
        else: # No building
            if tile.terrain == CityTerrainType.GRASS:
                # Any production building can be built on grass
                options.append({'text': "Build Farm", 'action': 'build', 'building_type': BuildingType.FARM})
                options.append({'text': "Build Lumber Mill", 'action': 'build', 'building_type': BuildingType.LUMBER_MILL})
                options.append({'text': "Build Iron Mine", 'action': 'build', 'building_type': BuildingType.IRON_MINE})
            elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                # These plots can be cleared
                options.append({'text': "Demolish Plot", 'action': 'demolish'})

        return options

    def screen_to_grid(self, screen_pos: tuple[int, int]) -> Position | None:
        """Converts a screen coordinate to a city grid coordinate, if applicable."""
        from client.renderer import CITY_TILE_SIZE, SCREEN_HEIGHT, CITY_VIEW_HEIGHT, WORLD_MAP_WIDTH

        city_view_rect = pygame.Rect(0, SCREEN_HEIGHT - CITY_VIEW_HEIGHT, WORLD_MAP_WIDTH, CITY_VIEW_HEIGHT)
        if not city_view_rect.collidepoint(screen_pos):
            return None

        local_x = screen_pos[0] - city_view_rect.x
        local_y = screen_pos[1] - city_view_rect.y

        grid_x = local_x // CITY_TILE_SIZE
        grid_y = local_y // CITY_TILE_SIZE
        return Position(grid_x, grid_y)

    def get_queue_item_remove_rect(self, item_index):
        queue_item_y = 230 + item_index * 30
        return pygame.Rect(WORLD_MAP_WIDTH + UI_PANEL_WIDTH - 40, queue_item_y, 20, 25)

    def update_action_queue_ui(self, action_queue: list):
        """Updates the list of rects for the action queue 'remove' buttons."""
        self.queue_item_rects.clear()
        for i in range(len(action_queue)):
            self.queue_item_rects.append(self.get_queue_item_remove_rect(i))

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
