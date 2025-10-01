from nightfall_engine.common.datatypes import Position
from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction
from client.config import PLAYER_ID, CITY_ID

# Constants for layout
CITY_TILE_SIZE = 50
SCREEN_HEIGHT = 800
CITY_VIEW_HEIGHT = 400
WORLD_MAP_WIDTH = 600
UI_PANEL_WIDTH = 600

class UIManager:
    """Manages UI state, like selections and context menus."""
    def __init__(self):
        self.selected_city_tile: Position | None = None

    def get_city_tile_rect(self, x, y):
        import pygame
        return pygame.Rect(x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)

    def get_context_menu_pos(self, item_index=0):
        if not self.selected_city_tile: return (0,0)
        base_pos = ( (self.selected_city_tile.x + 1) * CITY_TILE_SIZE + 5, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + self.selected_city_tile.y * CITY_TILE_SIZE )
        return (base_pos[0], base_pos[1] + item_index * 45)

    def get_context_menu_item_rect(self, item_index):
        if not self.selected_city_tile: return None
        import pygame
        pos = self.get_context_menu_pos(item_index)
        return pygame.Rect(pos, (160, 40))

    def get_queue_item_remove_rect(self, item_index):
        import pygame
        queue_item_y = 230 + item_index * 30
        return pygame.Rect(WORLD_MAP_WIDTH + UI_PANEL_WIDTH - 40, queue_item_y, 20, 25)

    def get_context_menu_options(self, tile):
        options = []
        pos = self.selected_city_tile
        if tile.building:
            if tile.building.type != BuildingType.CITADEL:
                options.append((f"Upgrade (Lvl {tile.building.level + 1})", lambda: UpgradeBuildingAction(PLAYER_ID, CITY_ID, pos, tile.building.type, tile.building.level)))
                options.append(("Demolish", lambda: DemolishAction(PLAYER_ID, CITY_ID, pos)))
        else:
            build_options = {
                CityTerrainType.GRASS: [("Build Farm", BuildingType.FARM)],
                CityTerrainType.FOREST_PLOT: [("Build Lumber Mill", BuildingType.LUMBER_MILL)],
                CityTerrainType.IRON_DEPOSIT: [("Build Iron Mine", BuildingType.IRON_MINE)]
            }
            if tile.terrain in build_options:
                for text, b_type in build_options[tile.terrain]:
                    options.append((text, lambda b=b_type: BuildBuildingAction(PLAYER_ID, CITY_ID, pos, b)))
            
            if tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                 options.append(("Demolish", lambda: DemolishAction(PLAYER_ID, CITY_ID, pos)))
        return options
