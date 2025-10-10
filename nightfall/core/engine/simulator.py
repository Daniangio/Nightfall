from nightfall.core.state.game_state import GameState
from nightfall.core.common.game_data import BUILDING_DATA, DEMOLISH_COST_BUILDING, DEMOLISH_COST_RESOURCE
from nightfall.core.components.city import City, CityMap, Building
from nightfall.core.common.datatypes import Resources, Position
from nightfall.core.common.enums import BuildingType, CityTerrainType
from nightfall.core.actions.city_actions import BuildBuildingAction, UpgradeBuildingAction, DemolishAction

class Simulator:
    """
    Handles the core game logic for simulating turns and predicting outcomes.
    This class is stateless and operates on a given GameState object.
    """
    def simulate_time_slice(self, game_state: GameState, time_delta: float) -> bool:
        """
        Simulates a slice of time for the entire game state.
        This modifies the game_state object in place.
        
        Args:
            game_state: The current state of the game.
            time_delta: The amount of time in seconds that has passed.
        
        Returns:
            True if the state was changed in a way that clients need to be notified, False otherwise.
        """
        state_changed = False

        # 1. Process incoming player actions and add them to city build queues
        for player in game_state.players.values():
            actions_to_process = list(player.action_queue)
            player.action_queue.clear() # Clear the original queue

            for action in actions_to_process:
                if action.execute(game_state):
                    print(f"Successfully executed action: {action}")
                    state_changed = True # The queue has changed, client needs update
                else:
                    print(f"Failed to execute action: {action}. It has been removed from the queue.")
        
        # 2. Process city build queues
        for city in game_state.cities.values():
            if city.build_queue:
                # Add progress to the first item in the queue
                first_item = city.build_queue[0]
                first_item.progress += time_delta

                # Check if it's finished
                build_time = self._get_build_time(first_item, game_state)
                if first_item.progress >= build_time:
                    # Action is complete!
                    completed_action = city.build_queue.pop(0)
                    self._apply_completed_action(completed_action, game_state)
                    city.update_stats() # Update stats in case a stat-providing building was finished
                    state_changed = True

        # 3. Calculate and add resource production (prorated for the time slice)
        for city in game_state.cities.values():
            # Production values are per hour (3600 seconds).
            production_per_hour = self.calculate_resource_production(game_state, city)
            time_fraction_of_hour = time_delta / 3600.0
            prorated_production = Resources(
                food=production_per_hour.food * time_fraction_of_hour,
                wood=production_per_hour.wood * time_fraction_of_hour,
                iron=production_per_hour.iron * time_fraction_of_hour,
            )
            new_resources = city.resources + prorated_production
            # Cap resources at the city's max storage
            city.resources.food = min(new_resources.food, city.max_resources.food)
            city.resources.wood = min(new_resources.wood, city.max_resources.wood)
            city.resources.iron = min(new_resources.iron, city.max_resources.iron)

        # 4. Process unit recruitment (would also be time-based)

        # 5. Increment turn counter (now represents a time tick)
        return state_changed

    def _get_build_time(self, action, game_state: GameState) -> float:
        """Gets the total time required for an action, adjusted for city bonuses."""
        base_time = 30.0 # Default fallback
        if isinstance(action, BuildBuildingAction):
            build_data = BUILDING_DATA.get(action.building_type, {}).get('build', {})
            base_time = build_data.get('time', 30.0)
        elif isinstance(action, UpgradeBuildingAction):
            city = game_state.cities.get(action.city_id)
            tile = city.city_map.get_tile(action.position.x, action.position.y) if city else None
            if tile and tile.building:
                next_level = tile.building.level + 1
                upgrade_data = BUILDING_DATA.get(tile.building.type, {}).get('upgrade', {}).get(next_level, {})
                base_time = upgrade_data.get('time', 60.0)
        elif isinstance(action, DemolishAction):
            city = game_state.cities.get(action.city_id)
            tile = city.city_map.get_tile(action.position.x, action.position.y) if city else None
            if tile:
                if tile.building:
                    return DEMOLISH_COST_BUILDING.get('time', 15.0)
                elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                    base_time = DEMOLISH_COST_RESOURCE.get('time', 20.0)

        # Apply construction speed modifier from the city
        city = game_state.cities.get(action.city_id)
        if city and city.construction_speed_modifier > 0:
            return base_time / city.construction_speed_modifier
        
        return base_time

    def _get_build_cost(self, action, game_state: GameState) -> Resources | None:
        """Gets the resource cost for a build/upgrade/demolish action."""
        if isinstance(action, BuildBuildingAction):
            build_data = BUILDING_DATA.get(action.building_type, {}).get('build', {})
            return build_data.get('cost') # Returns a Resources object or None
        elif isinstance(action, UpgradeBuildingAction):
            city = game_state.cities.get(action.city_id)
            tile = city.city_map.get_tile(action.position.x, action.position.y) if city else None
            if tile and tile.building:
                # The action was queued to go from the current level to the next.
                next_level = tile.building.level + 1
                upgrade_data = BUILDING_DATA.get(tile.building.type, {}).get('upgrade', {}).get(next_level, {})
                return upgrade_data.get('cost')
        elif isinstance(action, DemolishAction):
            city = game_state.cities.get(action.city_id)
            tile = city.city_map.get_tile(action.position.x, action.position.y) if city else None
            if tile:
                if tile.building:
                    return DEMOLISH_COST_BUILDING.get('cost')
                elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                    return DEMOLISH_COST_RESOURCE.get('cost')
        return None

    def _apply_completed_action(self, action, game_state: GameState):
        """Applies the effects of a completed construction action to the game state."""
        city = game_state.cities.get(action.city_id)
        if not city: return
        tile = city.city_map.get_tile(action.position.x, action.position.y)
        if not tile: return

        if isinstance(action, BuildBuildingAction):
            tile.building = Building(action.building_type, 1)
            print(f"[SIM] Completed: Build {action.building_type.value} at {action.position}.")
        elif isinstance(action, UpgradeBuildingAction) and tile.building:
            tile.building.level += 1
            print(f"[SIM] Completed: Upgrade {tile.building.type.value} at {action.position} to level {tile.building.level}.")
        elif isinstance(action, DemolishAction):
            if tile.building:
                tile.building = None
                print(f"[SIM] Completed: Demolish building at {action.position}.")
            elif tile.terrain in [CityTerrainType.FOREST_PLOT, CityTerrainType.IRON_DEPOSIT]:
                tile.terrain = CityTerrainType.GRASS
                print(f"[SIM] Completed: Clear plot at {action.position}.")

    def predict_outcome(self, base_state: GameState, action_queue: list, player_id: str, progress_map: dict = None) -> GameState:
        """
        Creates a deep copy of the game state and simulates the provided action
        queue to show a predicted outcome to the client.
        """
        predicted_state = base_state.deep_copy() # Start from the last authoritative state
        player = predicted_state.players.get(player_id)
        if not player:
            return predicted_state # Should not happen

        # On the client, "adding to the queue" is now a prediction of what happens
        # when the server accepts the action. The action is immediately added to the
        # city's build queue for prediction purposes.
        # We need to find the right city to add the actions to.
        for action in action_queue:
            action.execute(predicted_state) # This modifies the predicted_state

        # After adding new actions, restore the progress of existing actions
        if progress_map:
            for city in predicted_state.cities.values():
                if city.player_id == player_id:
                    for action in city.build_queue:
                        key = (action.__class__.__name__, getattr(action, 'position', None))
                        if key in progress_map:
                            action.progress = progress_map[key]


        return predicted_state

    def calculate_building_production(self, building: Building, position: Position, city_map: CityMap) -> Resources:
        """
        Calculates the resource production for a single building,
        including its adjacency bonuses.
        """
        building_data = BUILDING_DATA.get(building.type)
        if not building_data or 'production' not in building_data:
            return Resources()

        base_prod = building_data['production'].get(building.level, Resources())
        adjacency_bonus_multiplier = 1.0

        if 'adjacency_bonus' in building_data:
            for neighbor_pos in city_map.get_neighbors(position.x, position.y):
                neighbor_tile = city_map.get_tile(neighbor_pos.x, neighbor_pos.y)
                if neighbor_tile and neighbor_tile.terrain.name in building_data['adjacency_bonus']:
                    adjacency_bonus_multiplier += building_data['adjacency_bonus'][neighbor_tile.terrain.name]

        return Resources(
            food=round(base_prod.food * adjacency_bonus_multiplier),
            wood=round(base_prod.wood * adjacency_bonus_multiplier),
            iron=round(base_prod.iron * adjacency_bonus_multiplier)
        )

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

                building_production = self.calculate_building_production(tile.building, tile.position, city_map)
                total_production += building_production

        return total_production