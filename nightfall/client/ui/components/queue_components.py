from typing import Optional, TYPE_CHECKING
import pygame

from nightfall.client.ui.components.base_component import BaseComponent

if TYPE_CHECKING:
    # This block is only read by type checkers, not at runtime
    from nightfall.client.ui_manager import UIManager
    from nightfall.core.state.game_state import GameState

# Colors
C_BLACK, C_WHITE, C_RED = (0,0,0), (255,255,255), (200,0,0)
C_BLUE, C_DARK_GRAY, C_LIGHT_GRAY = (65,105,225), (30,30,30), (150,150,150)

class BuildQueueComponent(BaseComponent):
    def __init__(self, ui_manager: "UIManager"):
        self.ui_manager = ui_manager
        self.font_s = ui_manager.font_s
        self.font_m = ui_manager.font_m

    def handle_event(self, event: pygame.event.Event, game_state: "GameState", action_queue: list) -> Optional[dict]:
        if event.type == pygame.MOUSEMOTION:
            self.ui_manager.hovered_remove_button_index = None
            for i, rect in enumerate(self.ui_manager.queue_item_remove_button_rects):
                if rect.collidepoint(event.pos):
                    self.ui_manager.hovered_remove_button_index = i

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Handle scroll button clicks
            # Handle remove item clicks
            for i, rect in enumerate(self.ui_manager.queue_item_remove_button_rects):
                if rect.collidepoint(event.pos):
                    absolute_index = self.ui_manager.build_queue_scroll_offset + i
                    return {"type": "remove_action", "index": absolute_index}
            
            if self.ui_manager.buttons['build_queue_scroll_up'].collidepoint(event.pos):
                if self.ui_manager.build_queue_scroll_offset > 0:
                    self.ui_manager.build_queue_scroll_offset -= 1
                return None # Consumed event, no action
            
            if self.ui_manager.buttons['build_queue_scroll_down'].collidepoint(event.pos):
                self.ui_manager.build_queue_scroll_offset += 1 # UIManager will clamp it
                return None


        return None

    def draw(self, screen: pygame.Surface, ui_manager: "UIManager", action_queue: list):
        build_queue_rect = ui_manager.build_queue_panel_rect
        pygame.draw.rect(screen, C_DARK_GRAY, build_queue_rect, border_radius=8)
        screen.blit(self.font_s.render(f"Building Queue ({len(action_queue)})", True, C_WHITE), (build_queue_rect.x + 20, build_queue_rect.y + 10))

        # Draw scroll buttons
        can_scroll_up = ui_manager.build_queue_scroll_offset > 0
        can_scroll_down = ui_manager.build_queue_scroll_offset + ui_manager.build_queue_visible_items < len(action_queue)
        
        if build_queue_rect.height > 50 and (can_scroll_up or can_scroll_down):
            up_rect = ui_manager.buttons.get('build_queue_scroll_up')
            down_rect = ui_manager.buttons.get('build_queue_scroll_down')
            if up_rect and can_scroll_up: self._draw_scroll_button(screen, up_rect, '^', True)
            if down_rect and can_scroll_down: self._draw_scroll_button(screen, down_rect, 'v', True)

        # Draw visible items
        start_index = ui_manager.build_queue_scroll_offset
        end_index = start_index + ui_manager.build_queue_visible_items
        visible_actions = action_queue[start_index:min(end_index, len(action_queue))]

        for i, action in enumerate(visible_actions):
            absolute_index = start_index + i
            item_rect = ui_manager.get_build_queue_item_rect(i)
            pygame.draw.rect(screen, C_LIGHT_GRAY, item_rect, border_radius=5)
            screen.blit(self.font_s.render(f"{absolute_index + 1}. {str(action)}", True, C_BLACK), (item_rect.x + 5, item_rect.y + 2))
            
            x_rect = ui_manager.get_build_queue_item_remove_button_rect(i)
            if ui_manager.hovered_remove_button_index == i:
                pygame.draw.rect(screen, (100, 100, 100), x_rect, border_radius=3)

            text_surf = self.font_s.render("X", True, C_RED)
            screen.blit(text_surf, text_surf.get_rect(center=x_rect.center))

    def _draw_scroll_button(self, screen, rect, text, is_enabled):
        color = C_BLUE if is_enabled else C_DARK_GRAY
        text_color = C_WHITE if is_enabled else C_LIGHT_GRAY
        pygame.draw.rect(screen, color, rect, border_radius=5)
        text_surf = self.font_m.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

class UnitQueueComponent(BaseComponent):
    def __init__(self, ui_manager: "UIManager"):
        self.ui_manager = ui_manager
        self.font_s = ui_manager.font_s

    def handle_event(self, event: pygame.event.Event, *args, **kwargs) -> Optional[dict]:
        # Placeholder for future interactions like reordering or canceling units
        return None

    def draw(self, screen: pygame.Surface, ui_manager: "UIManager", city):
        unit_queue_rect = ui_manager.unit_queue_panel_rect
        unit_queue = city.recruitment_queue if city else []
        pygame.draw.rect(screen, C_DARK_GRAY, unit_queue_rect, border_radius=8)
        screen.blit(self.font_s.render(f"Unit Queue ({len(unit_queue)})", True, C_WHITE), (unit_queue_rect.x + 20, unit_queue_rect.y + 10))

        # Scroll button logic would go here if implemented

        # Draw visible items
        start_index = ui_manager.unit_queue_scroll_offset
        end_index = start_index + ui_manager.unit_queue_visible_items
        visible_items = unit_queue[start_index:end_index]

        y_offset = unit_queue_rect.y + 40
        for i, item in enumerate(visible_items):
            from nightfall.core.common.game_data import UNIT_DATA
            time_per_unit = UNIT_DATA[item.unit_type]['base_recruit_time']
            progress_pct = 0
            if time_per_unit > 0:
                progress_pct = (item.progress % time_per_unit) / time_per_unit * 100
            
            text = f"{item.quantity}x {item.unit_type.name.replace('_', ' ').title()} ({progress_pct:.0f}%)"
            screen.blit(self.font_s.render(text, True, C_WHITE), (unit_queue_rect.x + 20, y_offset + i * 25))

        # 'More items' indicator
        can_scroll_down = ui_manager.unit_queue_scroll_offset + ui_manager.unit_queue_visible_items < len(unit_queue)
        if can_scroll_down:
            last_item_y = y_offset + (len(visible_items) -1) * 25
            if unit_queue_rect.bottom - last_item_y > 35:
                screen.blit(self.font_s.render("...", True, C_WHITE), (unit_queue_rect.x + 20, last_item_y + 20))