from nightfall.client.game_client import GameClient

def main():
    """
    This is the main entry point for the client application.
    It creates an instance of the GameClient and starts the game.
    """
    client = GameClient(host='localhost', port=9999)
    client.run()

if __name__ == "__main__":
    main()