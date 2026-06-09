import json
import time
import threading
import logging
from typing import Callable
import websocket

# Kivy import to schedule updates on the main UI thread
from kivy.clock import Clock

logger = logging.getLogger("WebSocketClient")

class WebSocketClient:
    def __init__(self, uri: str, on_message_cb: Callable[[str, dict], None]):
        self.uri = uri
        self.on_message_cb = on_message_cb
        self.ws = None
        self.running = False
        self.thread = None
        self.connected = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("WebSocket client background thread started")

    def stop(self):
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("WebSocket client background thread stopped")

    def send(self, data: dict):
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to send data: {e}")

    def _run(self):
        while self.running:
            try:
                logger.info(f"Connecting to WebSocket: {self.uri}")
                # Enable trace for debugging if needed
                # websocket.enableTrace(True)
                self.ws = websocket.WebSocketApp(
                    self.uri,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever(ping_interval=5, ping_timeout=2)
            except Exception as e:
                logger.error(f"WebSocket execution error: {e}")
                
            # If still running, wait before attempting reconnect
            if self.running:
                logger.info("Retrying WebSocket connection in 2 seconds...")
                time.sleep(2.0)

    def _on_open(self, ws):
        self.connected = True
        logger.info("WebSocket connection established")
        # Notify the app
        Clock.schedule_once(lambda dt: self.on_message_cb("connection_update", {"connected": True}))

    def _on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        logger.info(f"WebSocket connection closed (code: {close_status_code}, msg: {close_msg})")
        # Notify the app
        Clock.schedule_once(lambda dt: self.on_message_cb("connection_update", {"connected": False}))

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error occurred: {error}")

    def _on_message(self, ws, message_str):
        try:
            message = json.loads(message_str)
            event_type = message.get("event")
            data = message.get("data")
            
            # Use Clock.schedule_once to dispatch to the Kivy main thread
            Clock.schedule_once(lambda dt: self.on_message_cb(event_type, data))
        except Exception as e:
            logger.error(f"Error decoding WebSocket message: {e}")
            logger.debug(f"Message payload was: {message_str}")
