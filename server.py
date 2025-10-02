import socketserver
import threading
import json
import time
from typing import Optional
import uuid
from nightfall_engine.state.game_state import GameState
from nightfall_engine.engine.simulator import Simulator
from nightfall_engine.actions.action import Action

# --- Server Configuration ---
HOST, PORT = "localhost", 9999
INITIAL_STATE_FILE = "data/initial_state.json"

class GameSession:
    """Manages the state and logic for a single game session."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = GameState.load_from_file(INITIAL_STATE_FILE)
        self.simulator = Simulator()
        self.lock = threading.Lock()
        
        # Player management for this session
        self.clients = {}  # player_id -> handler
        self.player_orders = {}
        self.player_ready_status = {}
        print(f"GameSession '{session_id}' created.")

    def handle_new_player(self, player_id, handler):
        with self.lock:
            # If player is rejoining, just update their handler. Otherwise, initialize them.
            self.clients[player_id] = handler
            if player_id not in self.player_ready_status:
                self.player_ready_status[player_id] = False
                self.player_orders[player_id] = []
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
            # When new orders are set, the player is no longer ready.
            action_class_map = GameState.ACTION_CLASS_MAP
            self.player_orders[player_id] = [Action.from_dict(data, action_class_map) for data in actions_data]
            self.player_ready_status[player_id] = False
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
            for player_id, orders in self.player_orders.items():
                if player_id in self.state.players:
                    self.state.players[player_id].action_queue = orders

            self.simulator.simulate_full_turn(self.state)
            
            for pid in self.player_ready_status:
                if pid in self.clients: # Only un-ready active players
                    self.player_ready_status[pid] = False
            self.player_orders.clear()
            
            # In a real game, each session would have its own save file
            # self.state.save_to_file(f"data/{self.session_id}.json")
            
            print(f"--- Turn {self.state.turn} simulated. Broadcasting new state to session clients. ---\n")
            self.broadcast_state()

    def broadcast_state(self):
        state_json_str = self.state.to_json_string()
        payload = json.loads(state_json_str)
        # Ensure player action queues are included in the broadcast
        for pid, orders in self.player_orders.items():
            if pid in payload['players']:
                payload['players'][pid]['action_queue'] = [o.to_dict() for o in orders]
        message = json.dumps({"type": "state_update", "payload": payload})
        for handler in list(self.clients.values()):
            try:
                handler.send_message(message)
            except OSError as e:
                print(f"Error broadcasting to a client: {e}")

class MasterServer:
    """Manages all active game sessions and new connections."""
    def __init__(self):
        self.sessions = {} # session_id -> GameSession
        self.lock = threading.Lock()

    def create_session(self, player_id, handler) -> GameSession:
        with self.lock:
            session_id = str(uuid.uuid4())[:8] # Create a unique session ID
            session = GameSession(session_id)
            self.sessions[session_id] = session
            return session
    
    def list_sessions(self):
        with self.lock:
            # Return a list of session IDs and their player counts
            return {sid: len(s.clients) for sid, s in self.sessions.items()}

    def join_session(self, session_id, player_id, handler) -> Optional[GameSession]:
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
                response = {"type": "session_list", "payload": sessions_info}
                self.send_message(json.dumps(response))
                return

            elif command == "create_session":
                self.player_id = data.get("player_id", "player1")
                self.session = master_server.create_session(self.player_id, self)
                self.session.handle_new_player(self.player_id, self)
                
                # The client expects an 'initial_state' message type
                payload = self.session.state.to_dict()
                # On creation, the action queue is empty
                for p_data in payload['players'].values():
                    p_data['action_queue'] = []

                response = {"type": "initial_state", "payload": payload}
                self.send_message(json.dumps(response))
                # Also send an ack for session creation
                ack_msg = {"type": "ack", "payload": {"message": f"Created and joined session {self.session.session_id}"}}
                self.send_message(json.dumps(ack_msg))

            elif command == "join_session":
                payload = data.get("payload", {})
                session_id = payload.get("session_id")
                self.player_id = payload.get("player_id", f"player{int(time.time()) % 1000}")
                session = master_server.join_session(session_id, self.player_id, self)
                if session:
                    self.session = session
                    self.session.handle_new_player(self.player_id, self)
                    # On join/rejoin, send the state including any persisted orders for that player
                    payload = self.session.state.to_dict()
                    for pid, orders in self.session.player_orders.items():
                        if pid in payload['players']:
                            payload['players'][pid]['action_queue'] = [o.to_dict() for o in orders]

                    response = {"type": "initial_state", "payload": payload}
                    self.send_message(json.dumps(response))
                    ack_msg = {"type": "ack", "payload": {"message": f"Joined session {session_id}"}}
                    self.send_message(json.dumps(ack_msg))
                else:
                    err_msg = {"type": "error", "payload": {"message": f"Session '{session_id}' not found."}}
                    self.send_message(json.dumps(err_msg))
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
                response_data = {"status": "success", "message": "Exited to lobby."}
                # No need to send ack, client handles state change locally
                return
            elif command == "join_session": # Player is already in a session, cannot join another
                response_data = {"status": "error", "message": "Already in a session."}
            else:
                response_data = {"status": "error", "message": "Unknown command"}
            
            # Format the response to what the client expects (ack/error)
            response_type = "ack" if response_data.get("status") == "success" else "error"
            self.send_message(json.dumps({"type": response_type, "payload": {"message": response_data.get("message")}}))

    def send_message(self, message: str):
        self.request.sendall(message.encode('utf-8') + b'\n')

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
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
