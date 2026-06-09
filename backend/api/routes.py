from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging

from backend.models.telemetry import VehicleState
from backend.services.mavlink_manager import MAVLinkManager
from backend.services.telemetry_service import TelemetryService
from backend.services.websocket_service import WebSocketService
from backend.services.command_service import CommandService

logger = logging.getLogger("APIRoutes")

router = APIRouter()

# Global dependency references initialized in main.py
mavlink_manager: Optional[MAVLinkManager] = None
telemetry_service: Optional[TelemetryService] = None
websocket_service: Optional[WebSocketService] = None
command_service: Optional[CommandService] = None

class ConnectRequest(BaseModel):
    port: str
    baud: int

class ModeChangeRequest(BaseModel):
    mode: str

# Read-only parameters mapping
READONLY_PARAMS = [
    {"name": "RTL_ALT", "value": 2000.0, "type": "Float (cm)", "desc": "Return-to-Launch altitude above takeoff point (20m)"},
    {"name": "BATT_LOW_VOLT", "value": 10.8, "type": "Float (V)", "desc": "Threshold voltage for low battery warning alert (10.8V)"},
    {"name": "FS_THR_ENABLE", "value": 1.0, "type": "Int (bool)", "desc": "Enables throttle fail-safe action if RC link is lost"},
    {"name": "ARMING_CHECK", "value": 1.0, "type": "Int (bitmask)", "desc": "Pre-arm sanity checks requirement bitmask (1=Enabled)"},
    {"name": "GPS_TYPE", "value": 1.0, "type": "Int (enum)", "desc": "First GPS sensor protocol type configured (1=Auto/U-Blox)"}
]

@router.get("/api/ports")
def get_ports():
    if not mavlink_manager:
        return []
    return mavlink_manager.get_available_ports()

@router.post("/api/connect")
def connect_device(req: ConnectRequest):
    if not mavlink_manager:
        raise HTTPException(status_code=500, detail="MAVLink Manager not initialized")
    
    success = mavlink_manager.connect(req.port, req.baud)
    if success:
        return {"status": "connected", "device": req.port}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to open connection on {req.port}")

@router.post("/api/disconnect")
def disconnect_device():
    if not mavlink_manager:
        raise HTTPException(status_code=500, detail="MAVLink Manager not initialized")
    
    mavlink_manager.disconnect()
    return {"status": "disconnected"}

@router.get("/api/status", response_model=VehicleState)
def get_status():
    if not telemetry_service:
        raise HTTPException(status_code=500, detail="Telemetry Service not initialized")
    return telemetry_service.get_latest_state()

@router.post("/api/command/arm")
def arm():
    if not command_service:
        raise HTTPException(status_code=500, detail="Command Service not initialized")
    success = command_service.arm_vehicle()
    return {"success": success}

@router.post("/api/command/disarm")
def disarm():
    if not command_service:
        raise HTTPException(status_code=500, detail="Command Service not initialized")
    success = command_service.disarm_vehicle()
    return {"success": success}

@router.post("/api/command/rtl")
def set_rtl():
    if not command_service:
        raise HTTPException(status_code=500, detail="Command Service not initialized")
    success = command_service.rtl()
    return {"success": success}

@router.post("/api/command/land")
def set_land():
    if not command_service:
        raise HTTPException(status_code=500, detail="Command Service not initialized")
    success = command_service.land()
    return {"success": success}

@router.post("/api/command/kill")
def emergency_kill():
    if not command_service:
        raise HTTPException(status_code=500, detail="Command Service not initialized")
    success = command_service.trigger_emergency_kill()
    return {"success": success}

@router.post("/api/command/mode")
def change_mode(req: ModeChangeRequest):
    if not command_service:
        raise HTTPException(status_code=500, detail="Command Service not initialized")
    success = command_service.set_mode(req.mode)
    return {"success": success}

@router.get("/api/parameters")
def get_parameters():
    return READONLY_PARAMS

@router.get("/api/logs/raw")
def get_raw_logs():
    if not telemetry_service:
        return []
    return telemetry_service.get_raw_messages()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not websocket_service:
        return
        
    await websocket_service.connect(websocket)
    try:
        while True:
            # We keep connection open and listen for optional ping/inputs
            data = await websocket.receive_text()
            # Echo or simple reply if needed
            await websocket.send_json({"event": "pong", "data": data})
    except WebSocketDisconnect:
        websocket_service.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket exception: {e}")
        websocket_service.disconnect(websocket)
