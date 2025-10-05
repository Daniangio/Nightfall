from nightfall.core.state.game_state import GameState
from nightfall.core.components.city import City, CityMap
from nightfall.core.common.game_data import BUILDING_DATA
from nightfall.core.common.datatypes import Resources, Position
from nightfall.core.common.enums import BuildingType

class Simulator:
    """
    Handles the core game logic for simulating turns and predicting outcomes.
    This class is stateless and operates on a given GameState object.
    """

    def simulate_full_turn(self, game_state: GameState):
        """
        Simulates a full turn for all players.
        This modifies the game_state object in place.
        """
        # 1. Replenish Action Points for all cities
        for city in game_state.cities.values():
            # This is the corrected logic. We SET the action points to the max, not add to them.
            city.action_points = city.max_action_points

        # 2. Process build queues for all players
        for player in game_state.players.values():
            # Create a copy of the queue to iterate over, as actions might be removed
            actions_to_process = list(player.action_queue)
            player.action_queue.clear() # Clear the original queue

            for action in actions_to_process:
                # In a real scenario, you might check if the player still owns the city
                if action.execute(game_state):
                    print(f"Successfully executed action: {action}")
                else:
                    # If an action fails, it's simply discarded.
                    # A more complex system might refund resources.
                    print(f"Failed to execute action: {action}. It has been removed from the queue.")

        # 3. Calculate and add resource production
        for city in game_state.cities.values():
            production = self.calculate_resource_production(game_state, city)
            city.resources += production

        # 4. Process unit recruitment
        # (This logic would go here)

        # 5. Increment turn counter
        game_state.turn += 1

    def predict_outcome(self, base_state: GameState, action_queue: list, player_id: str) -> GameState:
        """
        Creates a deep copy of the game state and simulates the provided action
        queue to show a predicted outcome to the client.
        """
        predicted_state = base_state.deep_copy()
        player = predicted_state.players.get(player_id)
        if not player:
            return predicted_state # Should not happen

        # Temporarily assign the new action queue for prediction
        player.action_queue = action_queue

        # Simulate execution of the queue
        for action in player.action_queue:
            action.execute(predicted_state) # This modifies the predicted_state

        return predicted_state

    def _get_neighbors(self, city_map: CityMap, x: int, y: int) -> list[Position]:
        """
        Helper function to get valid neighbor positions for a tile in a city map.
        This was missing from the CityMap class, so it's implemented here.
        """
        neighbors = []
        for dx, dy in [
            (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]: # 8-directional neighbors
            nx, ny = x + dx, y + dy
            # Check if the neighbor is within the map boundaries
            if 0 <= nx < city_map.width and 0 <= ny < city_map.height:
                neighbors.append(Position(nx, ny))
        return neighbors

    def calculate_resource_production(self, game_state: GameState, city: City) -> Resources:
        """
        Calculates the total resource production for a single city,
        including adjacency bonuses.
        """
        total_production = Resources()
        city_map = city.city_map

        for y in range(city_map.height):
            for x in range(city_map.width):
                tile = city_map.get_tile(x, y)
                if not tile or not tile.building:
                    continue

                building = tile.building
                building_data = BUILDING_DATA.get(building.type)
                if not building_data or 'production' not in building_data:
                    continue

                base_prod = building_data['production'].get(building.level, Resources())
                adjacency_bonus_multiplier = 1.0

                if 'adjacency_bonus' in building_data:
                    for neighbor_pos in self._get_neighbors(city_map, x, y):
                        neighbor_tile = city_map.get_tile(neighbor_pos.x, neighbor_pos.y)
                        if neighbor_tile and neighbor_tile.terrain.name in building_data['adjacency_bonus']:
                            adjacency_bonus_multiplier += building_data['adjacency_bonus'][neighbor_tile.terrain.name]

                total_production.food += round(base_prod.food * adjacency_bonus_multiplier)
                total_production.wood += round(base_prod.wood * adjacency_bonus_multiplier)
                total_production.iron += round(base_prod.iron * adjacency_bonus_multiplier)

        return total_production