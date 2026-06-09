import os
import sys

# Add project root to path to run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.services.mavlink_manager import MAVLinkManager
from backend.services.health_monitor import HealthMonitorService
from backend.services.telemetry_service import TelemetryService
from backend.services.websocket_service import WebSocketService
from backend.services.command_service import CommandService
from backend.api import routes

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("BackendMain")

# Global Service Instances
mavlink_manager = MAVLinkManager()
health_monitor = HealthMonitorService()
telemetry_service = TelemetryService(health_monitor=health_monitor)
websocket_service = WebSocketService()
command_service = CommandService(
    mavlink_manager=mavlink_manager,
    telemetry_service=telemetry_service,
    websocket_service=websocket_service
)

# Bridge MAVLink Manager to Telemetry Service
telemetry_service.register_mavlink_manager(mavlink_manager)
# Bridge Telemetry Service to WebSocket broadcaster
telemetry_service.set_broadcast_callback(websocket_service.broadcast)

# Register logger callbacks to broadcast log updates to frontend
def on_mavlink_log(level: str, message: str, timestamp: float):
    websocket_service.broadcast("log_update", {
        "level": level,
        "message": message,
        "timestamp": timestamp
    })

mavlink_manager.add_log_callback(on_mavlink_log)

# Periodic telemetry broadcasting task (10 Hz)
async def telemetry_broadcast_loop():
    logger.info("Starting 10 Hz telemetry broadcast task...")
    while True:
        try:
            start_time = time.time()
            
            # Read state only if connected
            if mavlink_manager.is_connected:
                state = telemetry_service.get_latest_state()
                # Broadcast telemetry to websockets
                websocket_service.broadcast("telemetry_update", state.dict())
            
            # Check elapsed time and sleep to maintain 10 Hz (100ms)
            elapsed = time.time() - start_time
            sleep_time = max(0.01, 0.1 - elapsed)
            await asyncio.sleep(sleep_time)
            
        except asyncio.CancelledError:
            logger.info("Telemetry broadcast task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in telemetry broadcast loop: {e}")
            await asyncio.sleep(1.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    loop = asyncio.get_running_loop()
    websocket_service.set_event_loop(loop)
    
    # Register globals to routes module
    routes.mavlink_manager = mavlink_manager
    routes.telemetry_service = telemetry_service
    routes.websocket_service = websocket_service
    routes.command_service = command_service
    
    # Start the 10 Hz telemetry loop
    broadcast_task = asyncio.create_task(telemetry_broadcast_loop())
    
    yield
    
    # Shutdown actions
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    
    # Disconnect MAVLink manager
    mavlink_manager.disconnect()
    logger.info("Backend GCS services shut down successfully.")

# Initialize FastAPI App
app = FastAPI(
    title="Pixhawk Ground Control Station Backend",
    description="Backend services for telemetry and flight commanding.",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(routes.router)

if __name__ == "__main__":
    logger.info("Starting FastAPI GCS Backend on localhost:8000...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
