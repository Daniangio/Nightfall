import pygame

from nightfall.client.config_ui import (
    C_BLACK, C_WHITE, C_RED, C_GREEN, C_BLUE, C_YELLOW, C_GRAY, C_DARK_GRAY,
    C_DARK_BLUE, C_LIGHT_GRAY, C_CYAN, C_GOLD, WORLD_TERRAIN_COLORS, TILE_WIDTH,
    TILE_HEIGHT, WORLD_TILE_SIZE, TOP_BAR_HEIGHT,
    FONT_S, FONT_M, FONT_XS
)
from nightfall.client.asset_manager import AssetManager
from nightfall.core.common.datatypes import Position
from nightfall.client.ui.components.panel_component import SidePanelComponent
from nightfall.core.state.game_state import GameState
from nightfall.client.enums import ActiveView
from nightfall.core.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction

class Renderer:
    """
    The main rendering coordinator.
    In a component-based system, this class's role is to iterate through
    UI components and delegate the drawing responsibility to them.
    """
    def __init__(self, screen):
        self.screen = screen
        self.font_s = FONT_S
        self.font_m = FONT_M
        self.font_xs = FONT_XS
        self.assets = AssetManager()

        # Create a semi-transparent surface for upgrade indicators
        # This can be a small dummy surface that gets scaled as needed.
        self.upgrade_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
        self.upgrade_surface.fill((0, 40, 180, 70)) # Light blue, semi-transparent
        
        # A surface for the selection highlight, will be scaled on the fly
        self.selection_surface = self._create_selection_surface()

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

    def _create_selection_surface(self):
        """Creates a transparent surface with a rectangular border for selection."""
        surface = pygame.Surface((1, 1), pygame.SRCALPHA) # Dummy 1x1 size
        # Draw a thick, vibrant line for the selection indicator
        pygame.draw.rect(surface, C_CYAN, (0, 0, 1, 1), 1)
        return surface


    def draw_text(self, text, pos, font, color=C_WHITE):
        surface = font.render(str(text), True, color)
        self.screen.blit(surface, pos)

    def draw_top_bar(self, ui_manager):
        """Draws the top navigation bar."""
        top_bar_rect = ui_manager.top_bar_rect
        self.screen.fill(C_DARK_GRAY, top_bar_rect)
        pygame.draw.line(self.screen, C_BLACK, top_bar_rect.bottomleft, top_bar_rect.bottomright, 2)

        # Draw view-switching buttons
        for name, rect in ui_manager.top_bar_buttons.items():
            is_active = (name == 'view_world' and ui_manager.active_view == ActiveView.WORLD_MAP) or \
                        (name == 'view_city' and ui_manager.active_view == ActiveView.CITY_VIEW and ui_manager.viewed_city_id is not None)
            
            is_disabled = name == 'view_city' and ui_manager.viewed_city_id is None
            
            color = C_YELLOW if is_active else C_GRAY if is_disabled else C_BLUE
            border_color = C_GOLD if is_active else C_LIGHT_GRAY if is_disabled else C_DARK_BLUE
            
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=4)
            text = "World Map" if name == 'view_world' else "City View"
            text_surf = self.font_s.render(text, True, C_WHITE)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
        
        # The "Exit to Lobby" button is now drawn as part of the UI Panel.

    def draw_world_map(self, game_map, cities, ui_manager):
        zoom = ui_manager.world_zoom_level
        zoomed_tile_size = WORLD_TILE_SIZE * zoom

        for y in range(game_map.height):
            for x in range(game_map.width):
                tile = game_map.get_tile(x, y)
                # EmptyTile has terrain=None, so this check implicitly skips it.
                if tile and tile.terrain:
                    color = WORLD_TERRAIN_COLORS.get(tile.terrain.name, None)
                    screen_x = x * zoomed_tile_size - ui_manager.camera_offset.x + ui_manager.main_view_rect.x
                    screen_y = y * zoomed_tile_size - ui_manager.camera_offset.y + ui_manager.main_view_rect.y + TOP_BAR_HEIGHT
                    rect = pygame.Rect(screen_x, screen_y, zoomed_tile_size - 1, zoomed_tile_size - 1)
                    if color: # Don't draw empty tiles
                        self.screen.fill(color, rect)
        
        for city in cities.values():
            screen_x = city.position.x * zoomed_tile_size - ui_manager.camera_offset.x
            screen_y = city.position.y * zoomed_tile_size - ui_manager.camera_offset.y + TOP_BAR_HEIGHT
            rect = pygame.Rect(screen_x, screen_y, zoomed_tile_size, zoomed_tile_size)
            pygame.draw.rect(self.screen, C_YELLOW, rect, 3)

    def draw_world_map_view(self, game_state, ui_manager):
        """Draws the main world map, showing all cities."""
        self.draw_world_map(game_state.game_map, game_state.cities, ui_manager)

    def draw_city_view(self, game_state, city, ui_manager, production, action_queue, simulator):
        city_map = city.city_map
        zoom = ui_manager.city_zoom_level
        zoomed_tile_width = int(TILE_WIDTH * zoom)
        zoomed_tile_height = int(TILE_HEIGHT * zoom)

        selected_tile = ui_manager.selected_city_tile

        # Create a lookup for faster checking of queued actions by position
        queued_actions = {getattr(action, 'position'): action for action in action_queue if hasattr(action, 'position')}
        currently_building_action = action_queue[0] if action_queue else None

        # The origin point for the isometric grid (where tile 0,0 is drawn)
        # For a flat grid, the origin is just the top-left of the view.
        origin_x = 0
        origin_y = TOP_BAR_HEIGHT

        # --- Draw tiles and buildings ---
        for x in range(city_map.width):
            for y in range(city_map.height):
                tile = city_map.get_tile(x,y)
                if not tile or tile.terrain.name == 'EMPTY':
                    continue

                tile_rect = ui_manager.get_city_tile_rect(x, y)
                tile_pos_obj = Position(x, y)

                # 1. Draw base terrain sprite
                terrain_sprite_name = f"terrain_{tile.terrain.name.lower()}.png" 
                terrain_img = self.assets.get_image(terrain_sprite_name, (zoomed_tile_width, zoomed_tile_height))
                self.screen.blit(terrain_img, tile_rect.topleft)

                # 2. Draw building or queued action sprite
                building_img = None
                is_ghost = False

                if tile.building:
                    sprite_name = f"building_{tile.building.type.name.lower()}_{tile.building.level}.png"
                    building_img = self.assets.get_image(sprite_name) # Load at native resolution
                elif tile_pos_obj in queued_actions:
                    action = queued_actions[tile_pos_obj]
                    if isinstance(action, BuildBuildingAction):
                        sprite_name = f"building_{action.building_type.name.lower()}_1.png"
                        building_img = self.assets.get_image(sprite_name)
                        is_ghost = True

                if building_img:
                    # Scale building to be square, based on tile width
                    square_size = zoomed_tile_width
                    scaled_building_img = self.assets.get_image(sprite_name, scale=(square_size, square_size))
                    if building_img.get_alpha(): # If original has alpha, use it for the key
                        scaled_building_img = self.assets.get_image(building_img.get_alpha(), scale=(square_size, square_size))
                    else: # Fallback for images without alpha
                        scaled_building_img = pygame.transform.smoothscale(building_img, (square_size, square_size))

                    # Center the square building on the rectangular tile
                    building_rect = scaled_building_img.get_rect(center=tile_rect.center)
                    # Align to bottom of the tile
                    building_rect.bottom = tile_rect.bottom
                    
                    if is_ghost:
                        ghost_img = scaled_building_img.copy()
                        ghost_img.set_alpha(128)
                        self.screen.blit(ghost_img, building_rect)
                    else:
                        self.screen.blit(scaled_building_img, building_rect)

                # 3. Draw demolish/upgrade indicators on top
                if tile_pos_obj in queued_actions:
                    action = queued_actions[tile_pos_obj]
                    zoomed_upgrade_surface = pygame.transform.scale(self.upgrade_surface, (zoomed_tile_width, zoomed_tile_height))
                    if isinstance(action, UpgradeBuildingAction):
                        self.screen.blit(zoomed_upgrade_surface, tile_rect.topleft)
                        upgrade_surf = self.font_m.render("^", True, C_WHITE)
                        self.screen.blit(upgrade_surf, (tile_rect.centerx - 5, tile_rect.top))
                    elif isinstance(action, DemolishAction):
                        pygame.draw.line(self.screen, C_RED, tile_rect.topleft, tile_rect.bottomright, 4)
                        pygame.draw.line(self.screen, C_RED, tile_rect.bottomleft, tile_rect.topright, 4)

        # --- Draw Time and Selection Separately to ensure they are on top ---
        # Draw remaining time for the currently building item
        if currently_building_action and hasattr(currently_building_action, 'position'):
            pos = currently_building_action.position
            tile_rect = ui_manager.get_city_tile_rect(pos.x, pos.y)
            total_time = simulator._get_build_time(currently_building_action, game_state)
            remaining_time = max(0, total_time - currently_building_action.progress)
            
            time_surf = self.font_xs.render(ui_manager._format_time(remaining_time), True, C_WHITE)
            time_rect = time_surf.get_rect(centerx=tile_rect.centerx, top=tile_rect.bottom + 2)
            bg_rect = time_rect.inflate(4, 2)
            pygame.draw.rect(self.screen, C_BLACK, bg_rect, border_radius=3)
            self.screen.blit(time_surf, time_rect)

        if selected_tile:
            rect = ui_manager.get_city_tile_rect(selected_tile.x, selected_tile.y)
            pygame.draw.rect(self.screen, C_CYAN, rect, 3)
    
    def draw_status_screen(self, message):
        self.screen.fill(C_BLACK)
        self.draw_text(message, (self.screen.get_width() // 2 - 200, self.screen.get_height() // 2 - 50), self.font_m)

    def draw_lobby_screen(self, ui_manager):
        self.screen.fill(C_GRAY)
        self.draw_text("Project Nightfall - Lobby", (100, 50), self.font_m, C_WHITE)

        for name, rect in ui_manager.lobby_buttons.items():
            is_hovered = rect.collidepoint(pygame.mouse.get_pos())
            color = C_DARK_BLUE if is_hovered else C_BLUE
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, C_LIGHT_GRAY, rect, 1, border_radius=4)

            if name == "create":
                text = "Create New Session"
            else:
                text = f"Join Session: {name[:8]}..." # Truncate long IDs
            
            text_surf = self.font_s.render(text, True, C_WHITE)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)
