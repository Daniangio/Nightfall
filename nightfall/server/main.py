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
TURN_INTERVAL_SECONDS = 1 # Each "turn" simulates 1 second of game time.

class GameSession:
    """Manages the state and logic for a single game session."""
    def __init__(self, session_id: str, initial_state: GameState):
        self.session_id = session_id
        self.state = initial_state
        self.simulator = Simulator()
        self.lock = threading.Lock()
        self.is_running = True
        self.simulation_thread = threading.Thread(target=self.game_loop, daemon=True)
        
        # Player management for this session
        self.clients = {}  # player_id -> handler
        self.players_in_session = set() # Tracks all players who have ever joined.
        print(f"GameSession '{session_id}' created.")

    def handle_new_player(self, player_id, handler):
        with self.lock:
            # If player is rejoining, just update their handler. Otherwise, initialize them.
            self.clients[player_id] = handler
            if player_id not in self.players_in_session:
                self.players_in_session.add(player_id)
                print(f"Player '{player_id}' joined session '{self.session_id}' for the first time.")
            else:
                print(f"Player '{player_id}' reconnected to session '{self.session_id}'.")

            # Start the simulation loop when the first player joins
            if not self.simulation_thread.is_alive():
                self.simulation_thread.start()

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
            # The player's action queue is now a temporary holding place for new commands
            # that will be processed by the simulator.
            new_actions = [Action.from_dict(data, GameState.ACTION_CLASS_MAP) for data in actions_data]
            player.action_queue.extend(new_actions)
            print(f"Received orders from player '{player_id}' in session '{self.session_id}'.")
            return {"status": "success", "message": "Orders received."}

    def handle_cancel_order(self, player_id, payload):
        with self.lock:
            city_id = payload.get("city_id")
            index = payload.get("index")
            city = self.state.cities.get(city_id)

            if not city or city.player_id != player_id:
                return {"status": "error", "message": "Invalid city or not owner."}
            
            if index is None or not (0 <= index < len(city.build_queue)):
                return {"status": "error", "message": "Invalid action index."}

            # Remove the action and refund the cost
            action_to_cancel = city.build_queue.pop(index)
            cost = self.simulator._get_build_cost(action_to_cancel, game_state=self.state)
            if cost:
                city.resources += cost
                print(f"Player '{player_id}' canceled action '{action_to_cancel}'. Refunded {cost}.")
            
            self.broadcast_state() # Notify clients of the change
            return {"status": "success", "message": "Action canceled."}

    def handle_reorder_order(self, player_id, payload):
        with self.lock:
            city_id = payload.get("city_id")
            index = payload.get("index")
            direction = payload.get("direction")
            city = self.state.cities.get(city_id)

            if not city or city.player_id != player_id:
                return {"status": "error", "message": "Invalid city or not owner."}

            queue_len = len(city.build_queue)
            if not (0 <= index < queue_len):
                return {"status": "error", "message": "Invalid action index."}

            # Apply reordering rules
            if direction == "up" and index > 1:
                city.build_queue.insert(index - 1, city.build_queue.pop(index))
            elif direction == "down" and 0 < index < queue_len - 1:
                city.build_queue.insert(index + 1, city.build_queue.pop(index))
            else:
                return {"status": "error", "message": "Invalid move."}

            print(f"Player '{player_id}' reordered queue. Item at {index} moved {direction}.")
            self.broadcast_state()
            return {"status": "success", "message": "Queue reordered."}

    def game_loop(self):
        """The main simulation loop for the game session."""
        print(f"[{self.session_id}] Game loop started.")
        while self.is_running:
            start_time = time.time()

            with self.lock:
                # The action queues are on the player objects in the game state.
                # The simulator will process them and update the state.
                state_was_updated = self.simulator.simulate_time_slice(self.state, TURN_INTERVAL_SECONDS)

                if state_was_updated:
                    print(f"--- [{time.strftime('%H:%M:%S')}] State updated. Broadcasting to session clients. ---")
                    self.broadcast_state()

            # Wait for the next tick
            time_to_sleep = TURN_INTERVAL_SECONDS - (time.time() - start_time)
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

    def broadcast_state(self):
        # The state object is the single source of truth. Just serialize and send.
        payload = self.state.to_dict()
        for handler in list(self.clients.values()):
            try:
                handler.send_response("state_update", payload)
            except OSError as e:
                print(f"Error broadcasting to a client: {e}")

    def stop(self):
        """Stops the game session simulation."""
        self.is_running = False
        print(f"[{self.session_id}] Game loop stopped.")

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

    def shutdown_all_sessions(self):
        with self.lock:
            print("Shutting down all active game sessions...")
            for session in self.sessions.values():
                session.stop()
            self.sessions.clear()
    
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
            elif command == "reorder_order":
                response_data = self.session.handle_reorder_order(player_id, payload)
            elif command == "cancel_order":
                response_data = self.session.handle_cancel_order(player_id, payload)
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
            master_server.shutdown_all_sessions()

if __name__ == "__main__":
    main()