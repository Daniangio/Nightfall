import pygame
from client.config import PLAYER_ID, CITY_ID

class InputHandler:
    """Handles all user input and translates it into game actions."""
    def __init__(self, game_client):
        self.client = game_client
        self.ui_manager = game_client.ui_manager

    def handle_events(self):
        """Processes the pygame event queue."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.client.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.client.end_turn()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                # UI elements get click priority
                if self.handle_context_menu_click(mouse_pos): continue
                if self.handle_queue_click(mouse_pos): continue
                self.handle_city_tile_click(mouse_pos)

    def handle_city_tile_click(self, mouse_pos):
        city_map = self.client.player_city.city_map
        for y in range(city_map.height):
            for x in range(city_map.width):
                rect = self.ui_manager.get_city_tile_rect(x, y)
                if rect.collidepoint(mouse_pos):
                    from nightfall_engine.common.datatypes import Position
                    self.ui_manager.selected_city_tile = Position(x, y)
                    return
        self.ui_manager.selected_city_tile = None

    def handle_context_menu_click(self, mouse_pos) -> bool:
        if not self.ui_manager.selected_city_tile: return False

        # Prevent queuing multiple actions on the same tile
        pos = self.ui_manager.selected_city_tile
        if any(hasattr(a, 'position') and a.position == pos for a in self.client.action_queue):
            return False

        tile = self.client.player_city.city_map.get_tile(pos.x, pos.y)
        if not tile: return False

        options = self.ui_manager.get_context_menu_options(tile)
        for i, (text, action_lambda) in enumerate(options):
            menu_rect = self.ui_manager.get_context_menu_item_rect(i)
            if menu_rect and menu_rect.collidepoint(mouse_pos):
                action = action_lambda()
                cost = action.get_cost()
                
                # Check against the *predicted* resources, not the base ones
                predicted_city = self.client.predictor.predicted_state.cities[CITY_ID]
                if predicted_city.resources.food >= cost.food and \
                   predicted_city.resources.wood >= cost.wood and \
                   predicted_city.resources.iron >= cost.iron:
                    
                    self.client.add_action_to_queue(action)
                    self.ui_manager.selected_city_tile = None
                else:
                    print("Client Prediction: Not enough resources!")
                return True
        return False

    def handle_queue_click(self, mouse_pos) -> bool:
        for i in range(len(self.client.action_queue)):
            x_button_rect = self.ui_manager.get_queue_item_remove_rect(i)
            if x_button_rect.collidepoint(mouse_pos):
                self.client.remove_action_from_queue(i)
                return True
        return False
