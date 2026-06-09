import asyncio
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("WebSocketService")

class WebSocketService:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        logger.info("WebSocketService: Event loop registered for thread-safe broadcasts")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_async(self, event_type: str, data: Any):
        """Asynchronous broadcast to all connected WebSocket clients."""
        if not self.active_connections:
            return
            
        message = {
            "event": event_type,
            "data": data
        }
        
        # Gather all send operations to execute concurrently
        tasks = []
        for connection in self.active_connections:
            try:
                tasks.append(connection.send_json(message))
            except Exception as e:
                logger.error(f"Error preparing send to client: {e}")
                self.disconnect(connection)
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, conn in zip(results, self.active_connections):
                if isinstance(res, Exception):
                    logger.error(f"Failed to send to client: {res}")
                    self.disconnect(conn)

    def broadcast(self, event_type: str, data: Any):
        """Thread-safe broadcast that can be safely invoked from background threads."""
        if not self.active_connections:
            return

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_async(event_type, data), 
                self.loop
            )
        else:
            # Fallback if loop is not running or registered yet
            logger.warning("WebSocketService: Cannot broadcast, event loop not running")
