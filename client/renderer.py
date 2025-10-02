import pygame

# Constants
CITY_TILE_SIZE = 50
WORLD_TILE_SIZE = 30
SCREEN_HEIGHT = 800
CITY_VIEW_HEIGHT = 400
WORLD_MAP_WIDTH = 600
UI_PANEL_WIDTH = 600

# Colors
C_BLACK, C_WHITE, C_RED, C_GREEN = (0,0,0), (255,255,255), (200,0,0), (0,200,0)
C_BLUE, C_YELLOW, C_GRAY = (65,105,225), (255,215,0), (50,50,50)
C_LIGHT_GRAY, C_CYAN = (150,150,150), (0,255,255)
WORLD_TERRAIN_COLORS = {'PLAINS': (152, 251, 152), 'FOREST': (34, 139, 34), 'MOUNTAIN': (139, 137, 137), 'LAKE': C_BLUE}
CITY_TERRAIN_COLORS = {'GRASS': (50, 205, 50), 'FOREST_PLOT': (139, 69, 19), 'IRON_DEPOSIT': C_LIGHT_GRAY, 'WATER': C_BLUE}

class Renderer:
    """Handles all drawing to the screen."""
    def __init__(self, screen):
        self.screen = screen
        self.font_s = pygame.font.Font(None, 24)
        self.font_m = pygame.font.Font(None, 32)

    def draw(self, game_state, ui_manager, production, action_queue):
        self.screen.fill(C_BLACK)
        pygame.display.set_caption(f"Project Nightfall - Turn {game_state.turn}")
        
        city = game_state.cities["city1"]
        
        self.draw_world_map(game_state.game_map, city.position)
        self.draw_city_view(city.city_map, ui_manager.selected_city_tile)
        self.draw_ui_panel(game_state, city, production, ui_manager, action_queue)
        self.draw_context_menu(city, ui_manager)

    def draw_text(self, text, pos, font, color=C_WHITE):
        surface = font.render(text, True, color)
        self.screen.blit(surface, pos)

    def draw_world_map(self, game_map, city_pos):
        for y in range(game_map.height):
            for x in range(game_map.width):
                tile = game_map.get_tile(x, y)
                if tile:
                    color = WORLD_TERRAIN_COLORS.get(tile.terrain.name, C_WHITE)
                    rect = pygame.Rect(x * WORLD_TILE_SIZE, y * WORLD_TILE_SIZE, WORLD_TILE_SIZE, WORLD_TILE_SIZE)
                    self.screen.fill(color, rect)
        
        rect = pygame.Rect(city_pos.x * WORLD_TILE_SIZE, city_pos.y * WORLD_TILE_SIZE, WORLD_TILE_SIZE, WORLD_TILE_SIZE)
        pygame.draw.rect(self.screen, C_YELLOW, rect, 3)

    def draw_city_view(self, city_map, selected_tile):
        city_map_rect = pygame.Rect(0, SCREEN_HEIGHT - CITY_VIEW_HEIGHT, WORLD_MAP_WIDTH, CITY_VIEW_HEIGHT)
        self.screen.fill(C_GRAY, city_map_rect)
        
        for y in range(city_map.height):
            for x in range(city_map.width):
                tile = city_map.get_tile(x,y)
                if tile:
                    color = CITY_TERRAIN_COLORS.get(tile.terrain.name, C_WHITE)
                    rect = pygame.Rect(x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)
                    self.screen.fill(color, rect)
                    pygame.draw.rect(self.screen, C_BLACK, rect, 1)
                    
                    if tile.building:
                        b_char = tile.building.type.name[0]
                        lvl = str(tile.building.level)
                        text_surf = self.font_m.render(b_char, True, C_BLACK)
                        self.screen.blit(text_surf, (rect.centerx - 8, rect.centery - 12))
                        lvl_surf = self.font_s.render(lvl, True, C_RED)
                        self.screen.blit(lvl_surf, (rect.right - 10, rect.bottom - 18))
        
        if selected_tile:
            rect = pygame.Rect(selected_tile.x * CITY_TILE_SIZE, SCREEN_HEIGHT - CITY_VIEW_HEIGHT + selected_tile.y * CITY_TILE_SIZE, CITY_TILE_SIZE, CITY_TILE_SIZE)
            pygame.draw.rect(self.screen, C_CYAN, rect, 3)

    def draw_ui_panel(self, game_state, city, production, ui_manager, action_queue):
        ui_panel_rect = pygame.Rect(WORLD_MAP_WIDTH, 0, UI_PANEL_WIDTH, SCREEN_HEIGHT)
        self.screen.fill(C_GRAY, ui_panel_rect)

        y = 20
        self.draw_text(f"Turn: {game_state.turn}", (ui_panel_rect.x + 20, y), self.font_m)
        y += 80
        
        res = city.resources
        self.draw_text(f"Food: {res.food} (+{production.food})", (ui_panel_rect.x + 20, y), self.font_s)
        y += 25
        self.draw_text(f"Wood: {res.wood} (+{production.wood})", (ui_panel_rect.x + 20, y), self.font_s)
        y += 25
        self.draw_text(f"Iron: {res.iron} (+{production.iron})", (ui_panel_rect.x + 20, y), self.font_s)
        y += 40

        self.draw_text(f"Build Queue:", (ui_panel_rect.x + 20, y), self.font_m)
        y += 40
        for i, action in enumerate(action_queue):
            queue_item_y = 230 + i * 30
            item_rect = pygame.Rect(ui_panel_rect.x + 20, queue_item_y, UI_PANEL_WIDTH - 40, 25)
            pygame.draw.rect(self.screen, C_LIGHT_GRAY, item_rect, border_radius=5)
            self.draw_text(f"{i+1}. {str(action)}", (item_rect.x + 5, item_rect.y + 2), self.font_s, C_BLACK)
            
            x_rect = ui_manager.get_queue_item_remove_rect(i)
            self.draw_text("X", (x_rect.x + 5, x_rect.y + 2), self.font_s, C_RED)

        # Draw main action buttons
        end_day_rect = ui_manager.buttons['end_day']
        pygame.draw.rect(self.screen, C_GREEN, end_day_rect, border_radius=5)
        self.draw_text("Ready (End Day)", (end_day_rect.x + 30, end_day_rect.y + 15), self.font_m)

        exit_rect = ui_manager.buttons['exit_session']
        pygame.draw.rect(self.screen, C_RED, exit_rect, border_radius=5)
        self.draw_text("Exit to Lobby", (exit_rect.x + 45, exit_rect.y + 15), self.font_m)


    def draw_context_menu(self, city, ui_manager):
        if not ui_manager.context_menu:
            return
            
        # Don't draw menu if an action is already queued for this tile
        pos = ui_manager.context_menu['position']
        if any(hasattr(a, 'position') and a.position == pos for a in city.build_queue):
            return
            
        for option in ui_manager.context_menu['options']:
            pygame.draw.rect(self.screen, C_BLUE, option['rect'], border_radius=5)
            self.draw_text(option['text'], (option['rect'].x + 10, option['rect'].y + 10), self.font_s)
    
    def draw_status_screen(self, message):
        self.screen.fill(C_BLACK)
        self.draw_text(message, (self.screen.get_width() // 2 - 200, self.screen.get_height() // 2 - 50), self.font_m)

    def draw_lobby_screen(self, ui_manager):
        self.screen.fill(C_GRAY)
        self.draw_text("Project Nightfall - Lobby", (100, 50), self.font_m, C_WHITE)

        for name, rect in ui_manager.lobby_buttons.items():
            pygame.draw.rect(self.screen, C_BLUE, rect, border_radius=5)
            if name == "create":
                text = "Create New Session"
            else:
                text = f"Join Session: {name}"
            
            text_surf = self.font_s.render(text, True, C_WHITE)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
