from client.pygame_client import PygameClient

if __name__ == "__main__":
    # Define paths to our data files
    STATE_FILE_PATH = "data/initial_state.json"
    MAP_FILE_PATH = "data/map.txt"
    
    # Instantiate and run the client
    client = PygameClient(STATE_FILE_PATH, MAP_FILE_PATH)
    client.run()
