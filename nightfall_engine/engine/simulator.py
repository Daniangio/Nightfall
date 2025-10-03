from nightfall_engine.state.game_state import GameState
from nightfall_engine.common.datatypes import Resources
from nightfall_engine.common.game_data import BUILDING_DATA, UNIT_DATA
from nightfall_engine.common.enums import BuildingType

class Simulator:
    """
    Handles simulation logic for both client-side prediction and
    authoritative server-side turn resolution.
    """

    def predict_outcome(self, base_state: GameState, action_queue: list, player_id: str) -> GameState:
        """
        CLIENT-SIDE USE: Takes a base state, an action queue for a specific player,
        and that player's ID. It returns a new predicted state.
        This method is purely for prediction and does not modify the original state.
        """
        # A single deep copy is all that's needed.
        predicted_state = base_state.deep_copy()
        
        # Sequentially execute each action in the queue on the copied state.
        # The Action.execute() method is responsible for checking and subtracting
        # resources from the state it is given.
        for action in action_queue:
            # The action's execute method should return True on success, False on failure.
            # This allows the prediction to stop if a player queues an impossible action.
            if not action.execute(predicted_state):
                # If an action is invalid (e.g., not enough resources),
                # we stop processing further actions in the queue for this prediction.
                print(f"[PREDICTION] Action failed and broke the queue: {action}")
                break
            
            # After a successful predicted action, update the city's stats
            city = predicted_state.cities.get(action.city_id)
            if city:
                city.update_stats_from_citadel()
                
        return predicted_state

    def simulate_full_turn(self, game_state: GameState):
        """
        SERVER-SIDE USE: Processes a single turn by executing queued actions
        from the live game state, generating resources, and advancing the turn.
        Modifies the state in-place.
        """
        print(f"\n--- Simulating Turn {game_state.turn} -> {game_state.turn + 1} ---")

        # 1. Replenish Action Points for all cities
        print("1. Replenishing Action Points...")
        for city in game_state.cities.values():
            city.update_stats_from_citadel() # Ensure max AP is up-to-date
            city.action_points = city.max_action_points
            print(f"  - {city.name} now has {city.action_points}/{city.max_action_points} AP.")
        
        # 2. Process build queues for each player/city
        print("2. Processing build queues...")
        # We iterate through players to ensure actions are executed in a defined order
        # (though for this game, the order between players doesn't matter yet).
        for player in game_state.players.values():
            # The player's action_queue is set by the server from their received orders.
            for action in player.action_queue:
                print(f"  - Executing for {player.name}: {action}")
                if action.execute(game_state): # Execute on the authoritative state
                    # After a successful action, update city stats (e.g., if Citadel was upgraded)
                    city = game_state.cities.get(action.city_id)
                    if city:
                        city.update_stats_from_citadel()
            player.action_queue.clear() # Clear queue after processing

        # 3. Process recruitment queues
        print("3. Processing recruitment...")
        for city in game_state.cities.values():
            if not city.recruitment_queue:
                continue

            # Calculate total city-wide recruitment speed
            recruitment_speed_bonus = 0
            for row in city.city_map.tiles:
                for tile in row:
                    if tile.building and tile.building.type == BuildingType.BARRACKS:
                        bonus = BUILDING_DATA[BuildingType.BARRACKS]['recruitment_speed_bonus'].get(tile.building.level, 0)
                        recruitment_speed_bonus += bonus
            
            # This is the total recruitment "points" this city generates this turn
            total_recruitment_points = 1.0 * (1 + recruitment_speed_bonus)
            print(f"  - {city.name} has {total_recruitment_points:.2f} recruitment points this turn.")

            # Process the first item in the queue
            queue_item = city.recruitment_queue[0]
            queue_item.progress += total_recruitment_points

            unit_data = UNIT_DATA[queue_item.unit_type]
            time_per_unit = unit_data['base_recruit_time']
            
            # Check how many units are completed
            units_completed = int(queue_item.progress // time_per_unit)
            if units_completed > 0:
                city.garrison[queue_item.unit_type] = city.garrison.get(queue_item.unit_type, 0) + units_completed
                queue_item.quantity -= units_completed
                queue_item.progress -= units_completed * time_per_unit
                print(f"  - {city.name} recruited {units_completed} {queue_item.unit_type.name.title()}.")

            if queue_item.quantity <= 0:
                city.recruitment_queue.pop(0)

        # 4. Generate resources for all cities
        print("4. Generating resources...")
        for city in game_state.cities.values():
            production = self.calculate_resource_production(game_state, city)
            city.resources += production
            print(f"  - {city.name} generated: {production}")

        game_state.turn += 1
        print("--- Turn simulation complete. ---")

    def calculate_resource_production(self, game_state: GameState, city) -> Resources:
        """
        Calculates the total resource production for a single city based on its
        buildings and adjacency bonuses from its internal city grid.
        """
        if not city: return Resources()
        
        total_production = Resources()

        # Iterate through all tiles in the city's internal map
        for row in city.city_map.tiles:
            for tile in row:
                if not tile.building: continue
                
                # Find adjacent tiles *within the city* for this specific building
                adjacent_city_tiles = []
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if dx == 0 and dy == 0: continue
                        adj_tile = city.city_map.get_tile(tile.position.x + dx, tile.position.y + dy)
                        if adj_tile: adjacent_city_tiles.append(adj_tile)

                b_data = BUILDING_DATA.get(tile.building.type, {})
                if 'production' in b_data:
                    base_prod = b_data['production'].get(tile.building.level, Resources())
                    bonus_data = b_data.get('adjacency_bonus', {})
                    
                    # Calculate total bonus percentage from adjacent city tiles
                    total_bonus_pct = sum(bonus_data.get(adj_tile.terrain.name, 0.0) for adj_tile in adjacent_city_tiles)
                    
                    # Apply bonus to base production
                    final_prod = Resources(
                        food=int(base_prod.food * (1 + total_bonus_pct)),
                        wood=int(base_prod.wood * (1 + total_bonus_pct)),
                        iron=int(base_prod.iron * (1 + total_bonus_pct))
                    )
                    total_production += final_prod
        
        return total_production
