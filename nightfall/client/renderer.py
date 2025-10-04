import pygame

from nightfall.client.enums import ActiveView
# Constants
CITY_TILE_SIZE = 50
WORLD_TILE_SIZE = 40
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
CITY_VIEW_HEIGHT = 400
WORLD_MAP_WIDTH = 600
UI_PANEL_WIDTH = SCREEN_WIDTH - WORLD_MAP_WIDTH

# Colors
C_BLACK, C_WHITE, C_RED, C_GREEN = (0,0,0), (255,255,255), (200,0,0), (0,200,0)
C_BLUE, C_YELLOW, C_GRAY = (65,105,225), (255,215,0), (50,50,50)
C_DARK_GRAY = (30,30,30)
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
        
        if ui_manager.active_view == ActiveView.WORLD_MAP:
            self.draw_world_map_view(game_state, ui_manager)
        elif ui_manager.active_view == ActiveView.CITY_VIEW:
            city = game_state.cities.get(ui_manager.viewed_city_id)
            if city:
                self.draw_city_view(game_state, city, ui_manager, production, action_queue)
            else:
                # Fallback if city isn't found
                self.draw_world_map_view(game_state, ui_manager)
                print(f"Error: Tried to view city '{ui_manager.viewed_city_id}' but it was not found.")
        
        # Draw UI Panel over the main view
        city_id = ui_manager.viewed_city_id or "city1" # Fallback for panel
        city_for_panel = game_state.cities.get(city_id)
        self.draw_ui_panel(game_state, city_for_panel, production, ui_manager, action_queue)

        # Draw top bar over everything else
        self.draw_top_bar(ui_manager)

    def draw_text(self, text, pos, font, color=C_WHITE):
        surface = font.render(text, True, color)
        self.screen.blit(surface, pos)

    def draw_top_bar(self, ui_manager):
        """Draws the top navigation bar."""
        top_bar_rect = ui_manager.top_bar_rect
        self.screen.fill(C_DARK_GRAY, top_bar_rect)
        pygame.draw.line(self.screen, C_BLACK, top_bar_rect.bottomleft, top_bar_rect.bottomright, 2)

        # Draw view-switching buttons
        for name, rect in ui_manager.top_bar_buttons.items():
            is_active = (name == 'view_world' and ui_manager.active_view == ActiveView.WORLD_MAP) or \
                        (name == 'view_city' and ui_manager.active_view == ActiveView.CITY_VIEW)
            
            color = C_YELLOW if is_active else C_BLUE
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            
            text = "World Map" if name == 'view_world' else "City View"
            text_surf = self.font_s.render(text, True, C_WHITE)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
        
        # The "Exit to Lobby" button is now drawn as part of the UI Panel.

    def draw_world_map(self, game_map, cities, ui_manager):
        for y in range(game_map.height):
            for x in range(game_map.width):
                tile = game_map.get_tile(x, y)
                if tile:
                    color = WORLD_TERRAIN_COLORS.get(tile.terrain.name, C_WHITE)
                    screen_x = x * WORLD_TILE_SIZE - ui_manager.camera_offset.x
                    screen_y = y * WORLD_TILE_SIZE - ui_manager.camera_offset.y + ui_manager.top_bar_rect.height
                    rect = pygame.Rect(screen_x, screen_y, WORLD_TILE_SIZE - 1, WORLD_TILE_SIZE - 1)
                    self.screen.fill(color, rect)
        
        for city in cities.values():
            screen_x = city.position.x * WORLD_TILE_SIZE - ui_manager.camera_offset.x
            screen_y = city.position.y * WORLD_TILE_SIZE - ui_manager.camera_offset.y + ui_manager.top_bar_rect.height
            rect = pygame.Rect(screen_x, screen_y, WORLD_TILE_SIZE, WORLD_TILE_SIZE)
            pygame.draw.rect(self.screen, C_YELLOW, rect, 3)

    def draw_world_map_view(self, game_state, ui_manager):
        """Draws the main world map, showing all cities."""
        self.draw_world_map(game_state.game_map, game_state.cities, ui_manager)

    def draw_city_view(self, game_state, city, ui_manager, production, action_queue):
        city_map = city.city_map
        selected_tile = ui_manager.selected_city_tile
        
        for y in range(city_map.height):
            for x in range(city_map.width):
                tile = city_map.get_tile(x,y)
                if tile:
                    color = CITY_TERRAIN_COLORS.get(tile.terrain.name, C_WHITE)
                    rect = ui_manager.get_city_tile_rect(x, y)
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
            rect = ui_manager.get_city_tile_rect(selected_tile.x, selected_tile.y)
            pygame.draw.rect(self.screen, C_CYAN, rect, 3)
        
        self.draw_context_menu(city, ui_manager)

    def draw_ui_panel(self, game_state, city, production, ui_manager, action_queue):
        ui_panel_rect = pygame.Rect(SCREEN_WIDTH - UI_PANEL_WIDTH, 0, UI_PANEL_WIDTH, SCREEN_HEIGHT)
        self.screen.fill(C_GRAY, ui_panel_rect)

        y = 20
        if not city: # Handle case where no city is selected
            self.draw_text("No city selected.", (ui_panel_rect.x + 20, y), self.font_m)
            return
        
        # Draw global buttons that belong on the UI panel
        exit_rect = ui_manager.buttons['exit_session']
        pygame.draw.rect(self.screen, C_RED, exit_rect, border_radius=5)
        text_surf = self.font_s.render("Exit to Lobby", True, C_WHITE)
        text_rect = text_surf.get_rect(center=exit_rect.center)
        self.screen.blit(text_surf, text_rect)

        self.draw_text(f"City: {city.name}", (ui_panel_rect.x + 20, y), self.font_m)
        y += 40
        self.draw_text(f"Turn: {game_state.turn}", (ui_panel_rect.x + 20, y), self.font_m)
        y += 80
        
        # --- Resources & City Stats ---
        stats_x_offset = ui_panel_rect.x + 220
        res = city.resources
        self.draw_text(f"Food: {res.food} (+{production.food if production else 0})", (ui_panel_rect.x + 20, y), self.font_s)
        self.draw_text(f"Action Points: {city.action_points} / {city.max_action_points}", (stats_x_offset, y), self.font_s)
        y += 25
        self.draw_text(f"Wood: {res.wood} (+{production.wood})", (ui_panel_rect.x + 20, y), self.font_s)
        self.draw_text(f"Buildings: {city.num_buildings} / {city.max_buildings}", (stats_x_offset, y), self.font_s)
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


    def draw_context_menu(self, city, ui_manager):
        if not ui_manager.context_menu:
            return
            
        # Don't draw menu if an action is already queued for this tile
        pos = ui_manager.context_menu['position']
        if any(hasattr(a, 'position') and a.position == pos for a in city.build_queue):
            return
            
        for option in ui_manager.context_menu['options']:
            color = C_BLUE if option['is_enabled'] else C_GRAY
            text_color = C_WHITE if option['is_enabled'] else C_LIGHT_GRAY
            pygame.draw.rect(self.screen, color, option['rect'], border_radius=5)
            self.draw_text(option['text'], (option['rect'].x + 10, option['rect'].y + 10), self.font_s, text_color)
    
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
