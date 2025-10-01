import pygame
from nightfall_engine.state.game_state import GameState
from nightfall_engine.engine.simulator import Simulator
from nightfall_engine.actions.city_actions import BuildBuildingAction
from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.common.datatypes import Position

# --- Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
WORLD_MAP_WIDTH = 600
UI_PANEL_WIDTH = SCREEN_WIDTH - WORLD_MAP_WIDTH
CITY_VIEW_HEIGHT = 400
WORLD_TILE_SIZE = 30
CITY_TILE_SIZE = 50
PLAYER_ID = "player1"
CITY_ID = "city1"

# --- Colors ---
C_BLACK, C_WHITE, C_RED, C_GREEN = (0,0,0), (255,255,255), (200,0,0), (0,200,0)
C_BLUE, C_YELLOW, C_GRAY = (65,105,225), (255,215,0), (50,50,50)
C_LIGHT_GRAY, C_CYAN = (150,150,150), (0,255,255)

WORLD_TERRAIN_COLORS = {'PLAINS': (152, 251, 152), 'FOREST': (34, 139, 34), 'MOUNTAIN': (139, 137, 137), 'LAKE': C_BLUE}
CITY_TERRAIN_COLORS = {'GRASS': (50, 205, 50), 'FOREST_PLOT': (139, 69, 19), 'IRON_DEPOSIT': C_LIGHT_GRAY, 'WATER': C_BLUE}

class PygameClient:
    def __init__(self, state_path: str, map_path: str):
        self.state_path = state_path
        self.map_path = map_path
        self.game_state = GameState.load_from_json(state_path, map_path)
        self.simulator = Simulator()
        
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.font_s = pygame.font.Font(None, 24)
        self.font_m = pygame.font.Font(None, 32)
        
        self.selected_city_tile: Position | None = None
        self.player_city = self.game_state.cities[CITY_ID]

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                self.handle_input(event)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.end_turn()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
            mouse_pos = pygame.mouse.get_pos()
            self.handle_city_tile_click(mouse_pos)
            self.handle_context_menu_click(mouse_pos)
            self.handle_queue_click(mouse_pos)

    def handle_city_tile_click(self, mouse_pos):
        city_map = self.player_city.city_map
        for y in range(city_map.height):
            for x in range(city_map.width):
                rect = pygame.Rect(x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)
                if rect.collidepoint(mouse_pos):
                    self.selected_city_tile = Position(x,y)
                    return

    def handle_context_menu_click(self, mouse_pos):
        if not self.selected_city_tile: return
        tile = self.player_city.city_map.get_tile(self.selected_city_tile.x, self.selected_city_tile.y)
        if not tile: return

        # For now, only one buildable option: Farm on Grass
        if not tile.building and tile.terrain == CityTerrainType.GRASS:
            menu_rect = pygame.Rect(self.get_context_menu_pos(), (120, 40))
            if menu_rect.collidepoint(mouse_pos):
                action = BuildBuildingAction(PLAYER_ID, CITY_ID, self.selected_city_tile, BuildingType.FARM)
                self.player_city.build_queue.append(action)
                self.selected_city_tile = None # Close menu

    def handle_queue_click(self, mouse_pos):
        for i, action in enumerate(self.player_city.build_queue):
            queue_item_rect = pygame.Rect(WORLD_MAP_WIDTH + 20, 300 + i * 30, UI_PANEL_WIDTH - 40, 25)
            if queue_item_rect.collidepoint(mouse_pos):
                self.player_city.build_queue.pop(i)
                return

    def end_turn(self):
        self.simulator.simulate_turn(self.game_state)
        self.game_state.save_to_json(self.state_path)
        self.selected_city_tile = None

    def draw(self):
        self.screen.fill(C_BLACK)
        pygame.display.set_caption(f"Project Nightfall - Turn {self.game_state.turn}")
        self.draw_world_map()
        self.draw_city_view()
        self.draw_ui_panel()
        self.draw_context_menu()

    def draw_world_map(self):
        game_map = self.game_state.game_map
        for y in range(game_map.height):
            for x in range(game_map.width):
                tile = game_map.get_tile(x, y)
                if tile:
                    color = WORLD_TERRAIN_COLORS.get(tile.terrain.name, C_WHITE)
                    rect = pygame.Rect(x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE, WORLD_TILE_SIZE, WORLD_TILE_SIZE)
                    pygame.draw.rect(self.screen, color, rect)
        # Draw city on world map
        city_pos = self.player_city.position
        rect = pygame.Rect(city_pos.x * WORLD_TILE_SIZE, city_pos.y * WORLD_TILE_SIZE, WORLD_TILE_SIZE, WORLD_TILE_SIZE)
        pygame.draw.rect(self.screen, C_YELLOW, rect, 3)

    def draw_city_view(self):
        city_map_rect = pygame.Rect(0, SCREEN_HEIGHT - CITY_VIEW_HEIGHT, WORLD_MAP_WIDTH, CITY_VIEW_HEIGHT)
        pygame.draw.rect(self.screen, C_GRAY, city_map_rect)
        
        city_map = self.player_city.city_map
        for y in range(city_map.height):
            for x in range(city_map.width):
                tile = city_map.get_tile(x,y)
                if tile:
                    color = CITY_TERRAIN_COLORS.get(tile.terrain.name, C_WHITE)
                    rect = pygame.Rect(x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, C_BLACK, rect, 1) # Border
                    
                    if tile.building:
                        # Draw building representation (a letter for now)
                        b_char = tile.building.type.name[0]
                        lvl = str(tile.building.level)
                        text_surf = self.font_m.render(b_char, True, C_BLACK)
                        self.screen.blit(text_surf, (rect.centerx - 8, rect.centery - 12))
                        text_surf_lvl = self.font_s.render(lvl, True, C_RED)
                        self.screen.blit(text_surf_lvl, (rect.right - 10, rect.bottom - 18))
        
        if self.selected_city_tile:
            rect = pygame.Rect(self.selected_city_tile.x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + self.selected_city_tile.y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)
            pygame.draw.rect(self.screen, C_CYAN, rect, 3) # Selection highlight

    def draw_ui_panel(self):
        ui_panel = pygame.Rect(WORLD_MAP_WIDTH, 0, UI_PANEL_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, C_GRAY, ui_panel)

        def draw_text(text, pos, font, color=C_WHITE):
            surface = font.render(text, True, color)
            self.screen.blit(surface, pos)

        y_offset = 20
        draw_text(f"Turn: {self.game_state.turn}", (ui_panel.x + 20, y_offset), self.font_m)
        y_offset += 40
        draw_text(f"City: {self.player_city.name}", (ui_panel.x + 20, y_offset), self.font_m)
        y_offset += 40
        
        res = self.player_city.resources
        draw_text(f"Food: {res.food}", (ui_panel.x + 20, y_offset), self.font_s)
        # Draw other resources...
        y_offset += 80

        draw_text("Build Queue (1/turn):", (ui_panel.x + 20, y_offset), self.font_m)
        y_offset += 40
        for i, action in enumerate(self.player_city.build_queue):
            queue_item_rect = pygame.Rect(ui_panel.x + 20, y_offset + i * 30, UI_PANEL_WIDTH - 40, 25)
            pygame.draw.rect(self.screen, C_LIGHT_GRAY, queue_item_rect, border_radius=5)
            draw_text(f"{i+1}. {action}", (ui_panel.x + 25, y_offset + 2 + i * 30), self.font_s, C_BLACK)
            # Add a small 'X' to indicate clickable
            draw_text("X", (queue_item_rect.right - 15, y_offset + 2 + i * 30), self.font_s, C_RED)

    def get_context_menu_pos(self):
        if not self.selected_city_tile: return (0,0)
        return ( (self.selected_city_tile.x + 1) * CITY_TILE_SIZE + 5,
                 SCREEN_HEIGHT - CITY_VIEW_HEIGHT + self.selected_city_tile.y * CITY_TILE_SIZE )
    
    def draw_context_menu(self):
        if not self.selected_city_tile: return
        tile = self.player_city.city_map.get_tile(self.selected_city_tile.x, self.selected_city_tile.y)
        if not tile: return
        
        menu_pos = self.get_context_menu_pos()
        # For now, only one option for one case
        if not tile.building and tile.terrain == CityTerrainType.GRASS:
            menu_rect = pygame.Rect(menu_pos, (120, 40))
            pygame.draw.rect(self.screen, C_BLUE, menu_rect, border_radius=5)
            text_surf = self.font_s.render("Build Farm", True, C_WHITE)
            self.screen.blit(text_surf, (menu_pos[0] + 10, menu_pos[1] + 10))
        # Add logic here for 'Upgrade' and 'Demolish' on existing buildings
