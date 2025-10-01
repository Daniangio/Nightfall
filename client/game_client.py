import pygame
from client.renderer import Renderer
from client.input_handler import InputHandler
from client.ui_manager import UIManager
from client.client_predictor import ClientPredictor
from nightfall_engine.state.game_state import GameState
from nightfall_engine.engine.simulator import Simulator
from nightfall_engine.common.datatypes import Resources
from client.config import PLAYER_ID, CITY_ID


class GameClient:
    """
    Main client class. Owns the game loop and all major components.
    """
    def __init__(self, state_path: str, map_path: str):
        self.state_path = state_path
        self.map_path = map_path

        # Core game and simulation objects
        self.authoritative_state = GameState.load_from_json(state_path, map_path)
        self.server_simulator = Simulator() # The "real" simulator

        # Client-side components
        self.predictor = ClientPredictor(self.authoritative_state)
        self.player_city = self.authoritative_state.cities[CITY_ID]
        self.action_queue = self.player_city.build_queue # Direct reference for now
        
        # Initialize pygame and client components
        pygame.init()
        screen = pygame.display.set_mode((1200, 800))
        
        self.ui_manager = UIManager()
        self.renderer = Renderer(screen)
        self.input_handler = InputHandler(self)

        self.running = True

    def run(self):
        """The main game loop."""
        self.predictor.predict_turn(self.action_queue) # Initial prediction
        while self.running:
            self.input_handler.handle_events()
            self.renderer.draw(self.predictor.predicted_state, self.ui_manager, self.predictor.predicted_production)
            pygame.display.flip()
        pygame.quit()

    def add_action_to_queue(self, action):
        """Adds an action and updates the prediction."""
        self.action_queue.append(action)
        self.predictor.predict_turn(self.action_queue)

    def remove_action_from_queue(self, index):
        """Removes an action and updates the prediction."""
        if 0 <= index < len(self.action_queue):
            self.action_queue.pop(index)
            self.predictor.predict_turn(self.action_queue)

    def end_turn(self):
        """Sends the queue to the server and gets the new authoritative state."""
        print("\n>>> Client ending turn. Sending queue to server.")
        self.player_city.build_queue = self.action_queue # Ensure the state has the latest queue
        self.server_simulator.simulate_turn(self.authoritative_state)
        self.authoritative_state.save_to_json(self.state_path)
        
        # Reset for the new turn
        self.action_queue.clear()
        self.predictor.reset(self.authoritative_state)
        self.ui_manager.selected_city_tile = None
        print(">>> New turn started. Client state synchronized.")
