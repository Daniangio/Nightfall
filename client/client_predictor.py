from copy import deepcopy
from nightfall_engine.state.game_state import GameState
from nightfall_engine.engine.simulator import Simulator
from nightfall_engine.common.datatypes import Resources

class ClientPredictor:
    """
    Handles client-side prediction by running a lightweight simulation
    of the current action queue.
    """
    def __init__(self, base_game_state: GameState):
        self.base_state = base_game_state
        self.predicted_state: GameState = deepcopy(self.base_state)
        self.predicted_production: Resources = Resources()
        self.client_simulator = Simulator() # Re-use the engine's simulator!

    def reset(self, new_base_state: GameState):
        """Resets the predictor with the new authoritative state from the server."""
        self.base_state = new_base_state
        self.predict_turn([])

    def predict_turn(self, action_queue: list):
        """
        Takes the base state and an action queue, and simulates the outcome
        to generate a predicted state and production estimate.
        """
        # 1. Start with a fresh copy of the authoritative state
        temp_state = deepcopy(self.base_state)
        
        # 2. Manually execute the actions in the queue on this temporary state.
        #    We do this because the simulator's `simulate_turn` also advances the turn
        #    and generates resources, which we want to do separately for prediction.
        city = temp_state.cities.get("city1") # Assuming single city for now
        if city:
            for action in action_queue:
                # We don't care about the return value, just the state modification
                action.execute(temp_state)

        # 3. Now, calculate the resource production based on the *resulting* state
        self.predicted_production = self.calculate_production(temp_state)
        
        # 4. The final predicted state is the one with the actions applied
        self.predicted_state = temp_state

    def calculate_production(self, game_state: GameState) -> Resources:
        """
        A client-side copy of the production calculation from the simulator.
        This avoids running the full `simulate_turn` which has other side effects.
        """
        # This logic is extracted from the simulator for prediction purposes.
        # It's a prime example of where code can be shared between client and server.
        city = game_state.cities.get("city1")
        if not city: return Resources()
        
        # This is a simplified version of the simulator's production logic
        # In a real scenario, this logic would be shared in a common module.
        # For now, we replicate it here.
        from nightfall_engine.common.game_data import BUILDING_DATA
        
        total_production = Resources()
        adjacent_world_tiles = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0: continue
                tile = game_state.game_map.get_tile(city.position.x + dx, city.position.y + dy)
                if tile: adjacent_world_tiles.append(tile)

        for row in city.city_map.tiles:
            for tile in row:
                if not tile.building: continue
                b_data = BUILDING_DATA.get(tile.building.type, {})
                if 'production' in b_data:
                    base_prod = b_data['production'].get(tile.building.level, Resources())
                    bonus_data = b_data.get('adjacency_bonus', {})
                    total_bonus_pct = sum(bonus_data.get(wt.terrain, 0.0) for wt in adjacent_world_tiles)
                    final_prod = Resources(
                        food=int(base_prod.food * (1 + total_bonus_pct)),
                        wood=int(base_prod.wood * (1 + total_bonus_pct)),
                        iron=int(base_prod.iron * (1 + total_bonus_pct))
                    )
                    total_production += final_prod
        
        return total_production
