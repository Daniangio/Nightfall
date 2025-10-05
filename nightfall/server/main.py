import socketserver
import threading
import json
import time
from typing import Optional
import uuid
from nightfall.core.state.game_state import GameState
from nightfall.core.engine.simulator import Simulator
from nightfall.core.actions.action import Action
from nightfall.config import PROJECT_ROOT

# --- Server Configuration ---
HOST, PORT = "localhost", 9999
WORLD_FILE = PROJECT_ROOT / "nightfall/server/data/world.json"

class GameSession:
    """Manages the state and logic for a single game session."""
    def __init__(self, session_id: str, initial_state: GameState):
        self.session_id = session_id
        self.state = initial_state
        self.simulator = Simulator()
        self.lock = threading.Lock()
        
        # Player management for this session
        self.clients = {}  # player_id -> handler
        self.player_ready_status = {pid: False for pid in self.state.players}
        print(f"GameSession '{session_id}' created.")

    def handle_new_player(self, player_id, handler):
        with self.lock:
            # If player is rejoining, just update their handler. Otherwise, initialize them.
            self.clients[player_id] = handler
            if player_id not in self.player_ready_status:
                # This case is for dynamically adding players to a running game, not currently used.
                self.player_ready_status[player_id] = False
                print(f"Player '{player_id}' joined session '{self.session_id}' for the first time.")
            else:
                print(f"Player '{player_id}' reconnected to session '{self.session_id}'.")

    def remove_player(self, player_id):
        with self.lock:
            # Only remove the active client handler, keep the player's data.
            self.clients.pop(player_id, None)
            print(f"Player '{player_id}' disconnected from session '{self.session_id}'. Their data is preserved.")

    def handle_set_orders(self, player_id, actions_data):
        with self.lock:
            player = self.state.players.get(player_id)
            if not player:
                return {"status": "error", "message": f"Player '{player_id}' not in this session."}
            # When new orders are set, the player is no longer ready.
            action_class_map = GameState.ACTION_CLASS_MAP
            player.action_queue = [Action.from_dict(data, action_class_map) for data in actions_data]
            self.player_ready_status[player_id] = False # Un-ready the player
            print(f"Received orders from player '{player_id}' in session '{self.session_id}'.")
            return {"status": "success", "message": "Orders received."}

    def handle_ready(self, player_id):
        with self.lock:
            if player_id in self.player_ready_status:
                self.player_ready_status[player_id] = True
                print(f"Player '{player_id}' is ready in session '{self.session_id}'.")
                self.check_for_turn_simulation()
            return {"status": "success", "message": "Ready status updated."}

    def check_for_turn_simulation(self):
        if not self.player_ready_status or not self.clients:
            return
        
        # Only check against players currently connected to this session
        all_ready = self.clients and all(self.player_ready_status.get(pid, False) for pid in self.clients)

        if all_ready:
            print(f"\n--- All players ready in session '{self.session_id}'! Simulating turn. ---")
            # The action queues are already on the player objects in the game state.
            self.simulator.simulate_full_turn(self.state)
            
            for pid in self.player_ready_status:
                if pid in self.clients: # Only un-ready active players
                    self.player_ready_status[pid] = False
            
            # In a real game, each session would have its own save file
            # self.state.save_to_file(f"data/{self.session_id}.json")
            
            print(f"--- Turn {self.state.turn} simulated. Broadcasting new state to session clients. ---\n")
            self.broadcast_state()
    def broadcast_state(self):
        # The state object is the single source of truth. Just serialize and send.
        payload = self.state.to_dict()
        for handler in list(self.clients.values()):
            try:
                handler.send_response("state_update", payload)
            except OSError as e:
                print(f"Error broadcasting to a client: {e}")

class MasterServer:
    """Manages all active game sessions and new connections."""
    def __init__(self):
        self.sessions = {} # session_id -> GameSession
        self.lock = threading.Lock()

    def create_session(self) -> GameSession:
        """Factory method to create a new, properly initialized game session."""
        with self.lock:
            session_id = str(uuid.uuid4())[:8] # Create a unique session ID
            
            # Create a fresh GameState for the new session
            initial_state = GameState.from_world_file(WORLD_FILE)
            
            session = GameSession(session_id, initial_state)
            self.sessions[session_id] = session
            return session
    
    def list_sessions(self):
        with self.lock:
            # Return a list of session IDs and their player counts
            return {sid: len(s.clients) for sid, s in self.sessions.items()}

    def get_session(self, session_id) -> Optional[GameSession]:
        with self.lock:
            return self.sessions.get(session_id)
    
master_server = MasterServer()

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.player_id = None
        self.session = None

    def handle(self):
        print(f"Connection from {self.client_address}")
        try:
            f = self.request.makefile('r')
            while True:
                line = f.readline()
                if not line: break
                
                data = json.loads(line)
                self.process_command(data)
        except (ConnectionResetError, BrokenPipeError):
            print(f"Client {self.client_address} ({self.player_id}) disconnected abruptly.")
        finally:
            self.cleanup_connection()

    def cleanup_connection(self):
        print(f"Client {self.client_address} ({self.player_id}) disconnected.")
        if self.session and self.player_id:
            self.session.remove_player(self.player_id)

    def process_command(self, data):
        command = data.get("command")
        
        if not self.session: # Initial commands before being in a session
            if command == "list_sessions":
                sessions_info = master_server.list_sessions()
                self.send_response("session_list", sessions_info)
                return

            elif command == "create_session":
                self.player_id = data.get("player_id", "player1")
                self.session = master_server.create_session()
                self.session.handle_new_player(self.player_id, self)
                
                self.send_response("state_update", self.session.state.to_dict())
                # Also send an ack for session creation
                self.send_response("ack", {"message": f"Created and joined session {self.session.session_id}"})

            elif command == "join_session":
                payload = data.get("payload", {})
                session_id = payload.get("session_id")
                self.player_id = payload.get("player_id", f"player{int(time.time()) % 1000}")
                session = master_server.get_session(session_id)
                if session:
                    self.session = session
                    self.session.handle_new_player(self.player_id, self)
                    # On join/rejoin, send the current state, which includes all players' action queues.
                    self.send_response("state_update", self.session.state.to_dict())
                    self.send_response("ack", {"message": f"Joined session {session_id}"})
                else:
                    self.send_response("error", {"message": f"Session '{session_id}' not found."})
            return
        else: # In-game commands, delegate to the session
            player_id = data.get("player_id")
            payload = data.get("payload")
            response_data = {}

            if command == "set_orders":
                response_data = self.session.handle_set_orders(player_id, payload)
            elif command == "ready":
                response_data = self.session.handle_ready(player_id)
            elif command == "leave_session":
                self.session.remove_player(player_id)
                self.session = None # Detach handler from session
                # No need to send ack, client handles state change locally
                return
            elif command == "join_session": # Player is already in a session, cannot join another
                response_data = {"status": "error", "message": "Already in a session."}
            else:
                response_data = {"status": "error", "message": f"Unknown command '{command}'"}
            
            # Format the response to what the client expects (ack/error)
            response_type = "ack" if response_data.get("status") == "success" else "error"
            self.send_response(response_type, {"message": response_data.get("message")})

    def send_response(self, msg_type: str, payload: dict):
        message = json.dumps({"type": msg_type, "payload": payload})
        self.request.sendall(message.encode('utf-8') + b'\n')

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def main():
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    print(f"Master Server starting up on {HOST}:{PORT}")
    with server:
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down server.")
            server.shutdown()

if __name__ == "__main__":
    main()