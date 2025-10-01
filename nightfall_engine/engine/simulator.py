from nightfall_engine.state.game_state import GameState
from nightfall_engine.common.datatypes import Resources
from nightfall_engine.common.game_data import BUILDING_DATA

class Simulator:
    """Handles the turn resolution logic."""
    
    def simulate_turn(self, game_state: GameState):
        """
        Processes a single turn by executing queued actions and running simulations.
        """
        print(f"\n--- Simulating Turn {game_state.turn} -> {game_state.turn + 1} ---")
        
        # 1. Process ALL build queue actions for each city
        print("1. Processing build queues...")
        for city in game_state.cities.values():
            queue_to_process = list(city.build_queue)
            city.build_queue.clear()
            
            for action in queue_to_process:
                print(f"  - Executing for {city.name}: {action}")
                if not action.execute(game_state):
                    print(f"  - WARNING: Action {action} failed server-side validation.")
            
        # 2. Generate resources with adjacency bonus
        print("2. Generating resources...")
        for city in game_state.cities.values():
            total_production = Resources()
            
            # Get 8 adjacent tiles from world map
            adjacent_world_tiles = []
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx == 0 and dy == 0: continue
                    tile = game_state.game_map.get_tile(city.position.x + dx, city.position.y + dy)
                    if tile:
                        adjacent_world_tiles.append(tile)

            # Calculate production for each building inside the city
            for row in city.city_map.tiles:
                for tile in row:
                    if not tile.building: continue
                    
                    b_type = tile.building.type
                    b_level = tile.building.level
                    b_data = BUILDING_DATA.get(b_type, {})

                    if 'production' in b_data:
                        base_prod = b_data['production'].get(b_level, Resources())
                        
                        # Calculate adjacency bonus
                        total_bonus_pct = 0.0
                        if 'adjacency_bonus' in b_data:
                            for world_tile in adjacent_world_tiles:
                                bonus = b_data['adjacency_bonus'].get(world_tile.terrain, 0.0)
                                total_bonus_pct += bonus
                        
                        final_prod = Resources(
                            food=int(base_prod.food * (1 + total_bonus_pct)),
                            wood=int(base_prod.wood * (1 + total_bonus_pct)),
                            iron=int(base_prod.iron * (1 + total_bonus_pct)),
                        )
                        total_production += final_prod
            
            city.resources += total_production
            print(f"  - {city.name} generated: Food +{total_production.food}, Wood +{total_production.wood}, Iron +{total_production.iron}")

        game_state.turn += 1
        print("--- Turn simulation complete. ---")
