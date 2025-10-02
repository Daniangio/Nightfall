import socket
import json
import threading
import queue

class NetworkClient:
    """Handles threaded, non-blocking communication with the server."""
    def __init__(self):
        self.sock = None
        self.incoming_queue = queue.Queue()
        self.is_connected = False

    def connect(self, host="localhost", port=9999):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.is_connected = True
            
            # Start a daemon thread to listen for messages from the server
            self.listen_thread = threading.Thread(target=self._listen_for_messages, daemon=True)
            self.listen_thread.start()
            print("Successfully connected to the server.")
        except ConnectionRefusedError:
            print("Connection failed. Is the server running?")
            self.is_connected = False

    def _listen_for_messages(self):
        """Worker thread function to read data from the server."""
        f = self.sock.makefile('r')
        while self.is_connected and self.sock:
            try:
                line = f.readline()
                if not line:
                    break  # Server closed connection
                data = json.loads(line)
                self.incoming_queue.put(data)
            except (OSError, json.JSONDecodeError):
                if self.is_connected: break # Only break if we weren't expecting to close
        self.is_connected = False
        print("Disconnected from server.")

    def receive_data(self):
        """Non-blocking method to get the next message from the server."""
        try:
            return self.incoming_queue.get_nowait()
        except queue.Empty:
            return None

    def send_message(self, data: dict):
        """Sends a JSON-encoded message to the server."""
        if self.is_connected:
            try:
                message = json.dumps(data)
                self.sock.sendall(message.encode('utf-8') + b'\n')
            except OSError:
                self.is_connected = False

    def close(self):
        self.is_connected = False
        if self.sock:
            self.sock.close()
            self.sock = None
