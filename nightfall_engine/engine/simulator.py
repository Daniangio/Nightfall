from nightfall_engine.state.game_state import GameState
from nightfall_engine.common.enums import BuildingType

class Simulator:
    """Handles the turn resolution logic."""
    
    def simulate_turn(self, game_state: GameState):
        """
        Processes a single turn by executing queued actions and running simulations.
        """
        print(f"\n--- Simulating Turn {game_state.turn} -> {game_state.turn + 1} ---")
        
        # 1. Process build queues (one per city)
        print("1. Processing build queues...")
        for city in game_state.cities.values():
            if city.build_queue:
                action_to_execute = city.build_queue.pop(0) # Get and remove first action
                print(f"  - Executing for {city.name}: {action_to_execute}")
                action_to_execute.execute(game_state)
            
        # 2. Generate resources
        print("2. Generating resources...")
        for city in game_state.cities.values():
            building_levels = city.get_total_building_levels()
            farm_level = building_levels.get(BuildingType.FARM, 0)
            
            food_gen = farm_level * 5
            # Add other resource generation here
            
            city.resources.food += food_gen
            if food_gen > 0:
                print(f"  - {city.name} generated: Food +{food_gen}")

        # ... other simulation steps ...

        game_state.turn += 1
        print("--- Turn simulation complete. ---")
