from enum import Enum, auto
from typing import Optional, TYPE_CHECKING, List
from nightfall.client.asset_manager import AssetManager
import pygame
from nightfall.client.config_ui import (
    C_GRAY, C_RED, C_RED_HOVER, C_GREEN, C_WHITE, C_YELLOW, C_LIGHT_GRAY, C_BLUE, C_DARK_BLUE, FONT_XS
)

from nightfall.client.ui.components.base_component import BaseComponent
from nightfall.client.ui.components.queue_components import BuildQueueComponent, UnitQueueComponent
from nightfall.core.common.enums import BuildingType, CityTerrainType
from nightfall.core.common.game_data import BUILDING_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall.core.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction
from nightfall.core.components.city import Building

if TYPE_CHECKING:
    # This block is only read by type checkers, not at runtime
    from nightfall.core.components.city import CityTile
    from nightfall.client.ui_manager import UIManager
    from nightfall.core.state.game_state import GameState

class SidePanelView(Enum):
    DEFAULT = auto() # The normal view with queues
    BUILD_LIST = auto() # Show list of buildings for an empty tile
    BUILDING_DETAILS = auto() # Show details for a specific building to build
    EXISTING_BUILDING_DETAILS = auto() # Show details for an existing building
    RESOURCE_PLOT_DETAILS = auto() # Show details for a resource plot (forest, iron)
    TERRAIN_DETAILS = auto() # Show details for non-interactive terrain like water

class ResourcePanelComponent(BaseComponent):
    def handle_event(self, event: pygame.event.Event, *args, **kwargs) -> Optional[dict]:
        return None # This panel is display-only

    def draw(self, screen: pygame.Surface, ui_manager: "UIManager", game_state: "GameState", city, production):
        resource_rect = ui_manager.resource_panel_rect
        pygame.draw.rect(screen, (30,30,30), resource_rect, border_radius=8)
        
        res_y = resource_rect.y + 10
        res = city.resources
        
        font_s = ui_manager.font_s
        font_xs = FONT_XS
        
        # Helper to draw text
        def draw_text(text, pos, font=font_s, color=C_WHITE):
            surface = font.render(text, True, color)
            screen.blit(surface, pos)

        draw_text(f"Food: {int(res.food)} / {int(city.max_resources.food)}", (resource_rect.x + 15, res_y))
        draw_text(f"(+{production.food if production else 0}/hr)", (resource_rect.x + 200, res_y), font=font_xs, color=C_GREEN)
        res_y += 20
        draw_text(f"Wood: {int(res.wood)} / {int(city.max_resources.wood)}", (resource_rect.x + 15, res_y))
        draw_text(f"(+{production.wood if production else 0}/hr)", (resource_rect.x + 200, res_y), font=font_xs, color=C_GREEN)
        res_y += 20
        draw_text(f"Iron: {int(res.iron)} / {int(city.max_resources.iron)}", (resource_rect.x + 15, res_y))
        draw_text(f"(+{production.iron if production else 0}/hr)", (resource_rect.x + 200, res_y), font=font_xs, color=C_GREEN)
        res_y += 20
        draw_text(f"Buildings: {city.num_buildings} / {city.max_buildings}", (resource_rect.x + 15, res_y))


class SidePanelComponent(BaseComponent):
    def __init__(self, ui_manager: "UIManager"):
        # Keep a reference to the parent UIManager
        self.ui_manager = ui_manager
        self.font_m = ui_manager.font_m
        self.font_s = ui_manager.font_s
        self.SidePanelView = SidePanelView # Make enum accessible
        self.assets = AssetManager()
        
        # The panel owns its sub-components
        self.resource_panel = ResourcePanelComponent()
        self.build_queue_panel = BuildQueueComponent(ui_manager)
        self.unit_queue_panel = UnitQueueComponent(ui_manager)

        # --- State for the new panel system ---
        self.current_view = SidePanelView.DEFAULT
        self.selected_building_for_details: Optional[BuildingType] = None
        
        # --- UI element rects for the new panels ---
        self.build_list_icon_rects: List[pygame.Rect] = []
        self.detail_panel_buttons: dict[str, pygame.Rect] = {}

    def handle_event(self, event: pygame.event.Event, game_state: "GameState", **kwargs) -> Optional[dict]:
        # The action_queue passed here is the client's local prediction queue, which is not what the UI displays.
        # The UI displays the city's build_queue. We get that from the game_state.
        city = game_state.cities.get(self.ui_manager.viewed_city_id)
        build_queue = city.build_queue if city else []
        # Delegate events to sub-components first
        action = self.build_queue_panel.handle_event(event, game_state, build_queue)
        if action: return action

        # Handle events for the detail panels if one is active
        if self.current_view != SidePanelView.DEFAULT:
            action = self._handle_detail_panel_events(event, game_state, city)
            if action: return action

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # --- Handle Splitter Drag ---
            if self.ui_manager.splitter_rect.collidepoint(event.pos):
                self.ui_manager.is_dragging_splitter = True
                return None
            if self.ui_manager.queue_splitter_rect.collidepoint(event.pos):
                self.ui_manager.is_dragging_queue_splitter = True
                return None

            # --- Handle Button Clicks ---
            if self.ui_manager.buttons['exit_session'].collidepoint(event.pos):
                return {"type": "exit_session"}

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.ui_manager.is_dragging_splitter = False
            self.ui_manager.is_dragging_queue_splitter = False

        elif event.type == pygame.MOUSEMOTION:
            if self.ui_manager.is_dragging_splitter:
                new_panel_width = self.ui_manager.screen_width - event.pos[0] # The action_queue is needed for layout recalculation
                self.ui_manager.update_side_panel_width(new_panel_width, build_queue)
            elif self.ui_manager.is_dragging_queue_splitter:
                self._handle_queue_splitter_drag(event, build_queue)

        return None # No action generated by the panel itself

    def _handle_detail_panel_events(self, event: pygame.event.Event, game_state: "GameState", city) -> Optional[dict]:
        """Handles events specifically for the build list or detail views."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        # Always check for the 'X' close button first
        close_button_rect = self.detail_panel_buttons.get('close')
        if close_button_rect and close_button_rect.collidepoint(event.pos):
            self.ui_manager.clear_selection()
            return None

        # --- Build List View ---
        if self.current_view == SidePanelView.BUILD_LIST:
            buildable = self._get_buildable_types()
            for i, rect in enumerate(self.build_list_icon_rects):
                if rect.collidepoint(event.pos):
                    self.selected_building_for_details = buildable[i]
                    self.current_view = SidePanelView.BUILDING_DETAILS
                    return None # Consumed event, view changed

        # --- Building/Resource Details View ---
        elif self.current_view in [SidePanelView.BUILDING_DETAILS, SidePanelView.EXISTING_BUILDING_DETAILS, SidePanelView.RESOURCE_PLOT_DETAILS]:
            selected_pos = self.ui_manager.selected_city_tile
            if not selected_pos: return None

            # Check for clicks on action buttons (Build, Upgrade, Demolish)
            for action_name, rect in self.detail_panel_buttons.items():
                if rect.collidepoint(event.pos):
                    # The draw method will have already determined if the button should be enabled.
                    # We can trust that if it's clickable, the action is valid.
                    action = None
                    if action_name == 'build' and self.selected_building_for_details:
                        action = BuildBuildingAction(
                            player_id=city.player_id, city_id=city.id,
                            position=selected_pos, building_type=self.selected_building_for_details
                        )
                    elif action_name == 'upgrade':
                        action = UpgradeBuildingAction(
                            player_id=city.player_id, city_id=city.id, position=selected_pos
                        )
                    elif action_name == 'demolish':
                        action = DemolishAction(
                            player_id=city.player_id, city_id=city.id, position=selected_pos
                        )
                    elif action_name == 'demolish_plot':
                        action = DemolishAction(
                            player_id=city.player_id, city_id=city.id, position=selected_pos
                        )
                    elif action_name == 'cancel':
                        # Find the index of the action in the city's build queue
                        action_index = next((i for i, a in enumerate(city.build_queue) if hasattr(a, 'position') and a.position == selected_pos), -1)
                        if action_index != -1:
                            return {"type": "remove_action", "index": action_index}
                    
                    if action:
                        # After creating an action, clear the selection and return to default view
                        self.ui_manager.clear_selection()
                        return {"type": "add_action", "action": action}
        return None

    def _get_buildable_types(self) -> List[BuildingType]:
        """Returns a list of all buildings that can be built on grass."""
        return [
            BuildingType.FARM, BuildingType.LUMBER_MILL, BuildingType.IRON_MINE,
            BuildingType.BARRACKS, BuildingType.WAREHOUSE, BuildingType.BUILDERS_HUT
        ]

    def _handle_queue_splitter_drag(self, event: pygame.event.Event, action_queue: list):
        from nightfall.client.ui_manager import DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT
        total_y_start = self.ui_manager.resource_panel_rect.bottom + 10
        total_y_end = DEFAULT_SCREEN_HEIGHT - 10
        total_height = total_y_end - total_y_start
        if total_height <= 0: return

        splitter_pos_relative = event.pos[1] - total_y_start
        max_content_height = 40 + (len(action_queue) * 30)
        clamped_splitter_pos = min(splitter_pos_relative, max_content_height)

        new_ratio = clamped_splitter_pos / total_height
        self.ui_manager.queue_split_ratio = max(0.05, min(0.95, new_ratio))
        self.ui_manager.update_queue_layouts(action_queue)

    def _update_view_based_on_selection(self, game_state: "GameState"):
        """
        Checks the selected tile in UIManager and updates the panel's
        current_view state accordingly.
        """
        selected_pos = self.ui_manager.selected_city_tile
        if not selected_pos:
            self.current_view = SidePanelView.DEFAULT
            return

        city = game_state.cities.get(self.ui_manager.viewed_city_id)
        if not city: return

        tile = city.city_map.get_tile(selected_pos.x, selected_pos.y)
        if not tile: return

        # If a build/upgrade is already queued for this tile, show existing building details
        is_tile_in_queue = any(hasattr(a, 'position') and a.position == selected_pos for a in city.build_queue)

        if tile.building or is_tile_in_queue:
            self.current_view = SidePanelView.EXISTING_BUILDING_DETAILS
        elif tile.terrain == CityTerrainType.GRASS:
            # If we are not already in a detail view for a building on this tile
            if self.current_view not in [SidePanelView.BUILD_LIST, SidePanelView.BUILDING_DETAILS]:
                 self.current_view = SidePanelView.BUILD_LIST
        elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
            self.current_view = SidePanelView.RESOURCE_PLOT_DETAILS
        elif tile.terrain in [CityTerrainType.WATER]:
            self.current_view = SidePanelView.TERRAIN_DETAILS
        else: # Empty tiles, etc.
            self.ui_manager.clear_selection() # Go back to default

    def draw(self, screen: pygame.Surface, game_state: "GameState", city, production, action_queue, simulator):
        side_panel_rect = self.ui_manager.side_panel_rect
        screen.fill(C_GRAY, side_panel_rect)

        # This is the main logic gate for what the panel displays
        self._update_view_based_on_selection(game_state)

        # Draw splitter
        splitter_color = C_YELLOW if self.ui_manager.is_dragging_splitter else C_LIGHT_GRAY
        pygame.draw.rect(screen, splitter_color, self.ui_manager.splitter_rect)

        if not city:
            screen.blit(self.font_m.render("No city selected.", True, C_WHITE), (side_panel_rect.x + 20, 20))
            return

        # --- Draw Panel Header ---
        screen.blit(self.font_m.render(f"City: {city.name}", True, C_WHITE), (side_panel_rect.x + 20, 20))
        
        exit_rect = self.ui_manager.buttons['exit_session']
        is_hovered = exit_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, C_RED_HOVER if is_hovered else C_RED, exit_rect, border_radius=4)
        pygame.draw.rect(screen, C_WHITE, exit_rect, 1, border_radius=4)
        text_surf = self.font_s.render("Exit to Lobby", True, C_WHITE)
        screen.blit(text_surf, text_surf.get_rect(center=exit_rect.center))

        # --- Draw Panel Content Based on View ---
        if self.current_view == SidePanelView.DEFAULT:
            self._draw_default_view(screen, game_state, city, production, simulator, action_queue)
        elif self.current_view == SidePanelView.BUILD_LIST:
            self._draw_build_list_view(screen, city)
        elif self.current_view == SidePanelView.BUILDING_DETAILS:
            self._draw_building_details_view(screen, city, game_state, simulator)
        elif self.current_view == SidePanelView.EXISTING_BUILDING_DETAILS:
            self._draw_existing_building_view(screen, city, game_state, simulator)
        elif self.current_view == SidePanelView.RESOURCE_PLOT_DETAILS:
            self._draw_resource_plot_view(screen, city)
        elif self.current_view == SidePanelView.TERRAIN_DETAILS:
            self._draw_terrain_details_view(screen, city)

    def _draw_default_view(self, screen, game_state, city, production, simulator, action_queue):
        """Draws the standard view with resource panel and queues."""
        self.resource_panel.draw(screen, self.ui_manager, game_state, city, production)
        self.build_queue_panel.draw(screen, self.ui_manager, game_state, simulator, action_queue)
        self.unit_queue_panel.draw(screen, self.ui_manager, city)

        # Draw queue splitter
        splitter_color = C_YELLOW if self.ui_manager.is_dragging_queue_splitter else C_LIGHT_GRAY
        pygame.draw.rect(screen, splitter_color, self.ui_manager.queue_splitter_rect)

    def _draw_build_list_view(self, screen: pygame.Surface, city):
        """Draws the list of buildable buildings for an empty grass tile."""
        panel_rect = self.ui_manager.side_panel_rect
        self._draw_detail_panel_header(screen, "Build on Grass Plot")

        self.build_list_icon_rects.clear()
        buildable_types = self._get_buildable_types()
        mouse_pos = pygame.mouse.get_pos()

        # --- Grid Layout Constants ---
        ICON_SIZE = (64, 64)
        ICON_PADDING = 15
        
        # --- Calculate Grid Properties ---
        available_width = panel_rect.width - (ICON_PADDING * 2)
        icons_per_row = max(1, available_width // (ICON_SIZE[0] + ICON_PADDING))
        row_width = icons_per_row * ICON_SIZE[0] + (icons_per_row - 1) * ICON_PADDING
        start_x = panel_rect.x + (panel_rect.width - row_width) / 2
        y_pos = 100

        for i, b_type in enumerate(buildable_types):
            row = i // icons_per_row
            col = i % icons_per_row

            icon_x = start_x + col * (ICON_SIZE[0] + ICON_PADDING)
            icon_y = y_pos + row * (ICON_SIZE[1] + ICON_PADDING)
            icon_rect = pygame.Rect(icon_x, icon_y, ICON_SIZE[0], ICON_SIZE[1])
            
            # Draw icon
            sprite_name = f"building_{b_type.name.lower()}_1.png"
            icon_img = self.assets.get_image(sprite_name, scale=ICON_SIZE)
            screen.blit(icon_img, icon_rect.topleft)
            if icon_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, C_YELLOW, icon_rect, 2, border_radius=4)

            self.build_list_icon_rects.append(icon_rect)

    def _draw_building_details_view(self, screen: pygame.Surface, city, game_state, simulator):
        """Draws details for a building selected from the build list."""
        if not self.selected_building_for_details: return
        b_type = self.selected_building_for_details
        building_name = b_type.name.replace('_', ' ').title()
        self._draw_detail_panel_header(screen, f"Build: {building_name}")

        panel_rect = self.ui_manager.side_panel_rect

        # --- Draw Icon and Description ---
        sprite_name = f"building_{b_type.name.lower()}_1.png"
        y_pos = self._draw_icon_and_get_next_pos(screen, sprite_name, 90)

        building_data = BUILDING_DATA.get(b_type, {})
        description = building_data.get('description', 'No description available.') # You need to add this to game_data.py
        desc_surf = self.font_s.render(description, True, C_WHITE)
        screen.blit(desc_surf, (panel_rect.x + 15, y_pos))
        y_pos += 40

        # --- Draw Production Info ---
        # Calculate for the level that will be built (level 1)
        hypothetical_building = Building(b_type, 1)
        selected_pos = self.ui_manager.selected_city_tile
        production = simulator.calculate_building_production(hypothetical_building, selected_pos, city.city_map)

        if production.food > 0 or production.wood > 0 or production.iron > 0:
            prod_title_surf = self.font_s.render("Production at Lvl 1:", True, C_YELLOW)
            screen.blit(prod_title_surf, (panel_rect.x + 15, y_pos))
            y_pos += 25
            
            prod_text = f"  Food: {production.food}/hr, Wood: {production.wood}/hr, Iron: {production.iron}/hr"
            prod_surf = self.font_s.render(prod_text, True, C_WHITE)
            screen.blit(prod_surf, (panel_rect.x + 15, y_pos))
            y_pos += 25

        # --- Draw Next Level Production Info ---
        next_level_data = building_data.get('upgrade', {}).get(2, {})
        if next_level_data:
            hypothetical_building_lvl2 = Building(b_type, 2)
            next_production = simulator.calculate_building_production(hypothetical_building_lvl2, selected_pos, city.city_map)
            
            if next_production.food > 0 or next_production.wood > 0 or next_production.iron > 0:
                next_prod_title_surf = self.font_s.render("Production at Lvl 2:", True, C_LIGHT_GRAY)
                screen.blit(next_prod_title_surf, (panel_rect.x + 15, y_pos))
                y_pos += 25

                next_prod_text = f"  Food: {next_production.food}/hr, Wood: {next_production.wood}/hr, Iron: {next_production.iron}/hr"
                next_prod_surf = self.font_s.render(next_prod_text, True, C_LIGHT_GRAY)
                screen.blit(next_prod_surf, (panel_rect.x + 15, y_pos))
                y_pos += 25

        # --- Draw Bonus Breakdown ---
        bonus_breakdown = self._get_bonus_breakdown(hypothetical_building, selected_pos, city.city_map)
        if bonus_breakdown:
            bonus_title_surf = self.font_s.render("Adjacency Bonuses:", True, C_YELLOW)
            screen.blit(bonus_title_surf, (panel_rect.x + 15, y_pos))
            y_pos += 25
            for line in bonus_breakdown:
                line_surf = self.font_s.render(f"  {line}", True, C_WHITE)
                screen.blit(line_surf, (panel_rect.x + 15, y_pos))
                y_pos += 20


        # Draw Build Button
        self._draw_action_buttons(screen, city, game_state, 'build', b_type=b_type)

    def _get_bonus_breakdown(self, building: Building, position: "Position", city_map: "CityMap") -> list[str]:
        """Generates a list of strings describing each adjacency bonus source."""
        breakdown = []
        building_data = BUILDING_DATA.get(building.type, {})
        adjacency_rules = building_data.get('adjacency_bonus', {})
        if not adjacency_rules:
            return []

        for neighbor_pos in city_map.get_neighbors(position.x, position.y):
            neighbor_tile = city_map.get_tile(neighbor_pos.x, neighbor_pos.y)
            if not neighbor_tile:
                continue

            # Check for terrain bonus
            if neighbor_tile.terrain.name in adjacency_rules:
                bonus = adjacency_rules[neighbor_tile.terrain.name]
                breakdown.append(f"+{int(bonus*100)}% from {neighbor_tile.terrain.name.replace('_', ' ').title()}")
            # Check for building bonus
            if neighbor_tile.building and neighbor_tile.building.type.name in adjacency_rules:
                bonus = adjacency_rules[neighbor_tile.building.type.name]
                breakdown.append(f"+{int(bonus*100)}% from {neighbor_tile.building.type.name.replace('_', ' ').title()}")
        return breakdown

    def _draw_existing_building_view(self, screen: pygame.Surface, city: "City", game_state: "GameState", simulator: "Simulator"):
        """Draws details for a building that is already on a tile."""
        selected_pos = self.ui_manager.selected_city_tile
        if not selected_pos: return

        # Check if an action is queued for this tile
        queued_action = next((a for a in city.build_queue if hasattr(a, 'position') and a.position == selected_pos), None)

        # If an action is queued, we might need to display info about a building that doesn't exist yet.
        if queued_action and isinstance(queued_action, BuildBuildingAction):
            building = Building(queued_action.building_type, 0) # Treat as level 0, will be 1 on completion
        else: # Existing building or a queued action on an existing building (upgrade/demolish)
            tile = city.city_map.get_tile(selected_pos.x, selected_pos.y)
            # If there's a queued action but no building (i.e., demolishing a resource plot),
            # we can't proceed with drawing building details, but we still need to draw the cancel button.
            if not tile or (not tile.building and not queued_action): return
            building = tile.building

        building_level_text = f" (Lvl {building.level})" if building and building.level > 0 else ""
        building_name_str = building.type.name.replace('_', ' ').title() if building else "Action in Progress"
        building_name = f"{building_name_str}{building_level_text}"
        self._draw_detail_panel_header(screen, building_name)

        # --- Draw Icon and Description ---
        if building:
            sprite_name = f"building_{building.type.name.lower()}_{building.level}.png"
            y_pos = self._draw_icon_and_get_next_pos(screen, sprite_name, 90)
            panel_rect = self.ui_manager.side_panel_rect

        # --- Draw Description ---
        if building:
            building_data = BUILDING_DATA.get(building.type, {})
            description = building_data.get('description', 'No description available.')
            desc_surf = self.font_s.render(description, True, C_WHITE)
            screen.blit(desc_surf, (panel_rect.x + 15, y_pos))
            y_pos += 40

            # --- Draw Current Production Info ---
            production = simulator.calculate_building_production(building, selected_pos, city.city_map)
            if production.food > 0 or production.wood > 0 or production.iron > 0:
                prod_title_surf = self.font_s.render("Current Production:", True, C_YELLOW)
                screen.blit(prod_title_surf, (panel_rect.x + 15, y_pos))
                y_pos += 25
                
                prod_text = f"  Food: {production.food}/hr, Wood: {production.wood}/hr, Iron: {production.iron}/hr"
                prod_surf = self.font_s.render(prod_text, True, C_WHITE)
                screen.blit(prod_surf, (panel_rect.x + 15, y_pos))
                y_pos += 25

            # --- Draw Next Level Production Info ---
            next_level = building.level + 1
            next_level_data = building_data.get('upgrade', {}).get(next_level, {})
            if next_level_data:
                hypothetical_building_next = Building(building.type, next_level)
                next_production = simulator.calculate_building_production(hypothetical_building_next, selected_pos, city.city_map)
                
                if next_production.food > 0 or next_production.wood > 0 or next_production.iron > 0:
                    next_prod_title_surf = self.font_s.render(f"Production at Lvl {next_level}:", True, C_LIGHT_GRAY)
                    screen.blit(next_prod_title_surf, (panel_rect.x + 15, y_pos))
                    y_pos += 25

                    next_prod_text = f"  Food: {next_production.food}/hr, Wood: {next_production.wood}/hr, Iron: {next_production.iron}/hr"
                    next_prod_surf = self.font_s.render(next_prod_text, True, C_LIGHT_GRAY)
                    screen.blit(next_prod_surf, (panel_rect.x + 15, y_pos))
                    y_pos += 25
            else:
                max_lvl_surf = self.font_s.render("Max level reached.", True, C_YELLOW)
                screen.blit(max_lvl_surf, (panel_rect.x + 15, y_pos))
                y_pos += 25

            # --- Draw Bonus Breakdown ---
            bonus_breakdown = self._get_bonus_breakdown(building, selected_pos, city.city_map)
            if bonus_breakdown:
                bonus_title_surf = self.font_s.render("Adjacency Bonuses:", True, C_YELLOW)
                screen.blit(bonus_title_surf, (panel_rect.x + 15, y_pos))
                y_pos += 25
                for line in bonus_breakdown:
                    line_surf = self.font_s.render(f"  {line}", True, C_WHITE)
                    screen.blit(line_surf, (panel_rect.x + 15, y_pos))
                    y_pos += 20

        if queued_action:
            # If an action is in the queue, only show the Cancel button
            self._draw_action_buttons(screen, city, game_state, 'cancel')
        else:
            # Otherwise, show standard action buttons
            self._draw_action_buttons(screen, city, game_state, 'upgrade', building=building)
            if building and building.type != BuildingType.CITADEL:
                self._draw_action_buttons(screen, city, game_state, 'demolish', building=building)

    def _draw_resource_plot_view(self, screen: pygame.Surface, city):
        """Draws details for a resource plot like a forest or iron deposit."""
        selected_pos = self.ui_manager.selected_city_tile
        if not selected_pos: return

        queued_action = next((a for a in city.build_queue if hasattr(a, 'position') and a.position == selected_pos), None)

        tile = city.city_map.get_tile(selected_pos.x, selected_pos.y)
        if not tile: return

        plot_name = tile.terrain.name.replace('_', ' ').title()
        self._draw_detail_panel_header(screen, plot_name)

        # --- Draw Icon and get next position ---
        sprite_name = f"resource_{tile.terrain.name.lower()}.png"
        self._draw_icon_and_get_next_pos(screen, sprite_name, 90)

        if queued_action:
            # If a demolish action is queued, show the Cancel button
            self._draw_action_buttons(screen, city, None, 'cancel')
        else:
            # Otherwise, show the Demolish button
            self._draw_action_buttons(screen, city, None, 'demolish_plot')

    def _draw_terrain_details_view(self, screen: pygame.Surface, city):
        """Draws details for a non-interactive terrain tile like water."""
        selected_pos = self.ui_manager.selected_city_tile
        if not selected_pos: return
        tile = city.city_map.get_tile(selected_pos.x, selected_pos.y)
        if not tile: return

        terrain_name = tile.terrain.name.replace('_', ' ').title()
        self._draw_detail_panel_header(screen, terrain_name)
        # Draw the terrain icon
        sprite_name = f"resource_{tile.terrain.name.lower()}.png"
        self._draw_icon_and_get_next_pos(screen, sprite_name, 90)
        # No action buttons are drawn for this view.

    def _draw_detail_panel_header(self, screen: pygame.Surface, title: str):
        """Draws the common header for all detail panels (title and close button)."""
        panel_rect = self.ui_manager.side_panel_rect
        self.detail_panel_buttons.clear()

        # Title
        title_surf = self.font_s.render(title, True, C_WHITE)
        screen.blit(title_surf, (panel_rect.x + 10, 60))

        # Close button ('X')
        close_rect = pygame.Rect(panel_rect.right - 30, 55, 20, 20)
        is_hovered = close_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, C_RED_HOVER if is_hovered else C_RED, close_rect, border_radius=4)
        close_surf = self.font_s.render("X", True, C_WHITE)
        screen.blit(close_surf, close_surf.get_rect(center=close_rect.center))
        self.detail_panel_buttons['close'] = close_rect

    def _draw_icon_and_get_next_pos(self, screen: pygame.Surface, sprite_name: str, y_pos: int) -> int:
        """Draws a centered icon in the panel and returns the y-position below it."""
        panel_rect = self.ui_manager.side_panel_rect
        icon_size = (64, 64)
        icon_img = self.assets.get_image(sprite_name, scale=icon_size)
        icon_rect = icon_img.get_rect(centerx=panel_rect.centerx, top=y_pos)
        screen.blit(icon_img, icon_rect)
        return icon_rect.bottom + 15

    def _draw_action_buttons(self, screen: pygame.Surface, city, game_state, action_type: str, **kwargs):
        """A helper to draw the Build/Upgrade/Demolish buttons and handle their enabled state."""
        panel_rect = self.ui_manager.side_panel_rect
        button_rect = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 60, panel_rect.width - 40, 40)
        
        # Adjust rect for multiple buttons
        if action_type == 'upgrade':
            button_rect.width = (panel_rect.width - 60) // 2
        elif action_type == 'demolish':
            button_rect.width = (panel_rect.width - 60) // 2
            button_rect.x += button_rect.width + 20

        # Determine button properties and enabled state
        is_enabled = False
        text = "ACTION"
        mouse_pos = pygame.mouse.get_pos()
        
        if action_type == 'build':
            b_type = kwargs.get('b_type')
            cost = BUILDING_DATA[b_type]['build']['cost']
            is_enabled = city.resources.can_afford(cost) and city.num_buildings < city.max_buildings
            text = "Build"
        elif action_type == 'upgrade':
            building = kwargs.get('building')
            next_level_data = BUILDING_DATA[building.type]['upgrade'].get(building.level + 1)
            if next_level_data:
                is_enabled = city.resources.can_afford(next_level_data['cost'])
                text = f"Upgrade (Lvl {building.level + 1})"
            else:
                is_enabled = False
                text = "Max Level"
        elif action_type == 'demolish':
            is_enabled = city.resources.can_afford(DEMOLISH_COST_BUILDING['cost'])
            text = "Demolish"
        elif action_type == 'demolish_plot':
            is_enabled = city.resources.can_afford(DEMOLISH_COST_RESOURCE['cost'])
            text = "Clear Plot"
        elif action_type == 'cancel':
            is_enabled = True # Always possible to cancel
            text = "Cancel Action"

        # Draw the button
        is_hovered = button_rect.collidepoint(mouse_pos)
        base_color = C_BLUE if is_enabled else C_GRAY
        border_color = C_DARK_BLUE if is_enabled else C_LIGHT_GRAY
        
        final_color = C_DARK_BLUE if is_hovered and is_enabled else base_color
        pygame.draw.rect(screen, final_color, button_rect, border_radius=5)
        pygame.draw.rect(screen, border_color, button_rect, 1, border_radius=5)
        text_surf = self.font_s.render(text, True, C_WHITE)
        screen.blit(text_surf, text_surf.get_rect(center=button_rect.center))

        if is_enabled:
            self.detail_panel_buttons[action_type] = button_rect
