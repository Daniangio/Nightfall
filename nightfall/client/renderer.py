import pygame

from nightfall.core.common.datatypes import Position
from nightfall.client.ui.components.panel_component import SidePanelComponent
from nightfall.core.state.game_state import GameState
from nightfall.client.enums import ActiveView
from nightfall.core.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction
# Constants
CITY_TILE_SIZE = 50
WORLD_TILE_SIZE = 40 # This can remain as it defines the world grid scale


# Colors
C_BLACK, C_WHITE, C_RED, C_GREEN = (0,0,0), (255,255,255), (200,0,0), (0,200,0)
C_BLUE, C_YELLOW, C_GRAY = (65,105,225), (255,215,0), (50,50,50)
C_DARK_GRAY = (30,30,30)
C_LIGHT_GRAY, C_CYAN = (150,150,150), (0,255,255)
C_GOLD = (255, 215, 0)
WORLD_TERRAIN_COLORS = {'PLAINS': (152, 251, 152), 'FOREST': (34, 139, 34), 'MOUNTAIN': (139, 137, 137), 'LAKE': C_BLUE}
CITY_TERRAIN_COLORS = {'GRASS': (50, 205, 50), 'FOREST_PLOT': (139, 69, 19), 'IRON_DEPOSIT': C_LIGHT_GRAY, 'WATER': C_BLUE}

class Renderer:
    """
    The main rendering coordinator.
    In a component-based system, this class's role is to iterate through
    UI components and delegate the drawing responsibility to them.
    """
    def __init__(self, screen):
        self.screen = screen
        self.font_s = pygame.font.Font(None, 24)
        self.font_m = pygame.font.Font(None, 32) 
        self.font_xs = pygame.font.Font(None, 18)
        # Create a semi-transparent surface for ghost buildings
        self.ghost_surface = pygame.Surface((CITY_TILE_SIZE, CITY_TILE_SIZE), pygame.SRCALPHA)
        self.ghost_surface.fill((200, 200, 200, 100)) # Light gray, semi-transparent
        # Create a semi-transparent surface for upgrade indicators
        self.upgrade_surface = pygame.Surface((CITY_TILE_SIZE, CITY_TILE_SIZE), pygame.SRCALPHA)
        self.upgrade_surface.fill((0, 40, 180, 70)) # Light blue, semi-transparent
        # The renderer will eventually not need these, but components might borrow them for now.

    def draw(self, game_state, ui_manager, production, action_queue, simulator):
        self.screen.fill(C_BLACK)
        
        if ui_manager.active_view == ActiveView.WORLD_MAP:
            self.draw_world_map_view(game_state, ui_manager)
        elif ui_manager.active_view == ActiveView.CITY_VIEW:
            city = game_state.cities.get(ui_manager.viewed_city_id)
            if city:
                self.draw_city_view(game_state, city, ui_manager, production, action_queue, simulator)
            else:
                # Fallback if city isn't found
                self.draw_world_map_view(game_state, ui_manager)
                print(f"Error: Tried to view city '{ui_manager.viewed_city_id}' but it was not found.")
        
        # Draw UI Panel over the main view
        city_id = ui_manager.viewed_city_id or "city1" # Fallback for panel
        city_for_panel = game_state.cities.get(city_id)
        
        # --- Component-Based Drawing ---
        for component in ui_manager.components:
            # The SidePanelComponent needs the simulator, so we pass it along.
            # Other components might not use all arguments, which is fine with keyword args.
            if isinstance(component, SidePanelComponent):
                 component.draw(self.screen, game_state=game_state, city=city_for_panel, production=production, action_queue=action_queue, simulator=simulator)
            else:
                 # Fallback for other potential components
                 component.draw(self.screen, game_state=game_state, city=city_for_panel, production=production, action_queue=action_queue)
        
        # Draw top bar over everything else (order matters)
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
                # EmptyTile has terrain=None, so this check implicitly skips it.
                if tile and tile.terrain:
                    color = WORLD_TERRAIN_COLORS.get(tile.terrain.name, None)
                    screen_x = x * WORLD_TILE_SIZE - ui_manager.camera_offset.x + ui_manager.main_view_rect.x
                    screen_y = y * WORLD_TILE_SIZE - ui_manager.camera_offset.y + ui_manager.main_view_rect.y
                    rect = pygame.Rect(screen_x, screen_y, WORLD_TILE_SIZE - 1, WORLD_TILE_SIZE - 1)
                    if color: # Don't draw empty tiles
                        self.screen.fill(color, rect)
        
        for city in cities.values():
            screen_x = city.position.x * WORLD_TILE_SIZE - ui_manager.camera_offset.x
            screen_y = city.position.y * WORLD_TILE_SIZE - ui_manager.camera_offset.y + ui_manager.top_bar_rect.height
            rect = pygame.Rect(screen_x, screen_y, WORLD_TILE_SIZE, WORLD_TILE_SIZE)
            pygame.draw.rect(self.screen, C_YELLOW, rect, 3)

    def draw_world_map_view(self, game_state, ui_manager):
        """Draws the main world map, showing all cities."""
        self.draw_world_map(game_state.game_map, game_state.cities, ui_manager)

    def draw_city_view(self, game_state, city, ui_manager, production, action_queue, simulator):
        city_map = city.city_map
        selected_tile = ui_manager.selected_city_tile

        # Create a lookup for faster checking of queued actions by position
        queued_actions = {getattr(action, 'position'): action for action in action_queue if hasattr(action, 'position')}
        currently_building_action = action_queue[0] if action_queue else None
        
        for y in range(city_map.height):
            for x in range(city_map.width):
                tile = city_map.get_tile(x,y)
                # EmptyTile has terrain=None, so this check implicitly skips it.
                if tile and tile.terrain:
                    color = CITY_TERRAIN_COLORS.get(tile.terrain.name, None)
                    rect = ui_manager.get_city_tile_rect(x, y)
                    if color is None: # Don't draw empty tiles
                        continue
                    self.screen.fill(color, rect)
                    pygame.draw.rect(self.screen, C_BLACK, rect, 1)
                    
                    tile_pos = Position(x, y)
                    
                    if tile.building:
                        b_char = tile.building.type.name[0]
                        lvl = str(tile.building.level)
                        text_surf = self.font_m.render(b_char, True, C_BLACK)
                        self.screen.blit(text_surf, (rect.centerx - 8, rect.centery - 12))
                        lvl_surf = self.font_xs.render(lvl, True, C_GOLD)
                        self.screen.blit(lvl_surf, (rect.right - 10, rect.bottom - 18))

                        # Draw upgrade indicator if queued
                        if tile_pos in queued_actions and isinstance(queued_actions[tile_pos], UpgradeBuildingAction):
                            self.screen.blit(self.upgrade_surface, rect.topleft)
                            upgrade_surf = self.font_m.render("^", True, C_DARK_GRAY)
                            self.screen.blit(upgrade_surf, (rect.left + 2, rect.top))
                        # Draw demolish indicator if queued on a building
                        elif tile_pos in queued_actions and isinstance(queued_actions[tile_pos], DemolishAction):
                            pygame.draw.line(self.screen, C_RED, (rect.left + 5, rect.top + 5), (rect.right - 5, rect.bottom - 5), 4)
                            pygame.draw.line(self.screen, C_RED, (rect.left + 5, rect.bottom - 5), (rect.right - 5, rect.top + 5), 4)


                    elif tile_pos in queued_actions:
                        # This is a "ghost" building (a BuildBuildingAction on an empty tile)
                        queued_action = queued_actions[tile_pos]
                        if isinstance(queued_action, BuildBuildingAction):
                            self.screen.blit(self.ghost_surface, rect.topleft)
                            b_char = queued_action.building_type.name[0]
                            text_surf = self.font_m.render(b_char, True, (0,0,0,150)) # Semi-transparent text
                            self.screen.blit(text_surf, (rect.centerx - 8, rect.centery - 12))
                        # Draw demolish indicator if queued on a plot
                        elif isinstance(queued_action, DemolishAction):
                            pygame.draw.line(self.screen, C_RED, (rect.left + 5, rect.top + 5), (rect.right - 5, rect.bottom - 5), 4)
                            pygame.draw.line(self.screen, C_RED, (rect.left + 5, rect.bottom - 5), (rect.right - 5, rect.top + 5), 4)

        # --- Draw Time and Selection Separately to ensure they are on top ---
        # Draw remaining time for the currently building item
        if currently_building_action and hasattr(currently_building_action, 'position'):
            pos = currently_building_action.position
            rect = ui_manager.get_city_tile_rect(pos.x, pos.y)
            total_time = simulator._get_build_time(currently_building_action, game_state)
            remaining_time = max(0, total_time - currently_building_action.progress)
            
            time_surf = self.font_xs.render(ui_manager._format_time(remaining_time), True, C_WHITE)
            time_rect = time_surf.get_rect(centerx=rect.centerx, top=rect.bottom + 2)
            bg_rect = time_rect.inflate(4, 2)
            pygame.draw.rect(self.screen, C_BLACK, bg_rect, border_radius=3)
            self.screen.blit(time_surf, time_rect)

        if selected_tile:
            rect = ui_manager.get_city_tile_rect(selected_tile.x, selected_tile.y)
            pygame.draw.rect(self.screen, C_CYAN, rect, 3)
        
        self.draw_context_menu(city, ui_manager)

    def draw_scroll_button(self, rect, text, is_enabled):
        """Draws a single scroll arrow button."""
        color = C_BLUE if is_enabled else C_DARK_GRAY
        text_color = C_WHITE if is_enabled else C_LIGHT_GRAY
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        text_surf = self.font_m.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def draw_context_menu(self, city, ui_manager):
        if not ui_manager.context_menu:
            return
            
        # Don't draw menu if an action is already queued for this tile
        # This logic is now handled inside UIManager._get_context_menu_options_data
        # pos = ui_manager.context_menu['position']
        # if any(hasattr(a, 'position') and a.position == pos for a in city.build_queue):
        #     return
            
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
