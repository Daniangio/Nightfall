from client.game_client import GameClient

if __name__ == "__main__":
    STATE_FILE_PATH = "data/initial_state.json"
    MAP_FILE_PATH = "data/map.txt"
    
    client = GameClient(STATE_FILE_PATH, MAP_FILE_PATH)
    client.run()
