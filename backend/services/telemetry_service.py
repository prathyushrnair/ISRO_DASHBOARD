import time
import math
import logging
from typing import Dict, Any, List, Optional
import threading

from backend.models.telemetry import VehicleState
from backend.services.health_monitor import HealthMonitorService

logger = logging.getLogger("TelemetryService")

# ArduPilot Copter Mode Mapping (Standard)
MODE_MAP = {
    0: "STABILIZE",
    1: "ACRO",
    2: "ALT_HOLD",
    3: "AUTO",
    4: "GUIDED",
    5: "LOITER",
    6: "RTL",
    7: "CIRCLE",
    9: "LAND",
    11: "DRIFT",
    16: "POSHOLD",
    17: "BRAKE",
}

class TelemetryService:
    def __init__(self, health_monitor: HealthMonitorService):
        self.health_monitor = health_monitor
        self.state = VehicleState()
        self.lock = threading.Lock()
        
        self.last_packet_time = 0.0
        self.home_set = False
        self.home_lat = 0.0
        self.home_lon = 0.0
        
        # Buffer for raw MAVLink messages (sliding window of 100 entries)
        self.raw_messages: List[Dict[str, Any]] = []
        self.raw_messages_lock = threading.Lock()
        
        # Callback to broadcast websocket messages
        self.broadcast_callback = None

    def set_broadcast_callback(self, callback):
        self.broadcast_callback = callback

    def register_mavlink_manager(self, manager):
        manager.add_message_callback(self.handle_mavlink_message)
        manager.add_connection_callback(self.handle_connection_change)

    def handle_connection_change(self, connected: bool):
        with self.lock:
            self.state.connected = connected
            if not connected:
                # Reset some volatile states, keep others as stale
                self.state.armed = False
                self.state.mode = "UNKNOWN"
            else:
                self.last_packet_time = time.time()
        
        # Trigger immediate connection update to websocket
        if self.broadcast_callback:
            self.broadcast_callback("connection_update", {"connected": connected})

    def handle_mavlink_message(self, msg):
        msg_type = msg.get_type()
        now = time.time()
        self.last_packet_time = now
        
        # 1. Update raw messages history
        payload = {}
        try:
            payload = msg.get_payload()
        except Exception:
            # Fallback if get_payload doesn't exist
            payload = {k: v for k, v in msg.__dict__.items() if not k.startswith('_')}
            
        # Create summary
        payload_summary = ", ".join([f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in list(payload.items())[:4]])
        
        raw_msg_data = {
            "type": msg_type,
            "timestamp": now,
            "payload_summary": payload_summary
        }
        
        with self.raw_messages_lock:
            self.raw_messages.append(raw_msg_data)
            if len(self.raw_messages) > 100:
                self.raw_messages.pop(0)

        # Trigger message notification if callback is registered
        if self.broadcast_callback:
            # We don't want to flood with 100Hz raw messages, so we only broadcast specific raw message events
            if msg_type in ["HEARTBEAT", "ATTITUDE", "GLOBAL_POSITION_INT", "SYS_STATUS", "BATTERY_STATUS"]:
                self.broadcast_callback("sensor_update", raw_msg_data)

        # 2. Parse specific MAVLink messages
        with self.lock:
            self.state.connected = True
            self.state.last_update_timestamp = now
            
            if msg_type == 'HEARTBEAT':
                # Armed state: MAV_MODE_FLAG_SAFETY_ARMED = 128
                self.state.armed = bool(msg.base_mode & 128)
                # Mode
                mode_id = msg.custom_mode
                self.state.mode = MODE_MAP.get(mode_id, f"MODE_{mode_id}")
                
            elif msg_type == 'ATTITUDE':
                self.state.roll = math.degrees(msg.roll)
                self.state.pitch = math.degrees(msg.pitch)
                self.state.yaw = math.degrees(msg.yaw)
                if self.state.yaw < 0:
                    self.state.yaw += 360.0
                self.state.heading = self.state.yaw
                
            elif msg_type == 'GLOBAL_POSITION_INT':
                self.state.latitude = msg.lat / 1e7
                self.state.longitude = msg.lon / 1e7
                self.state.altitude = msg.alt / 1000.0 # to meters
                self.state.relative_altitude = msg.relative_alt / 1000.0 # to meters
                self.state.heading = msg.hdg / 100.0 # to degrees
                
                # GPS velocity
                vx = msg.vx / 100.0 # m/s
                vy = msg.vy / 100.0 # m/s
                self.state.ground_speed = math.sqrt(vx**2 + vy**2)
                self.state.vertical_speed = msg.vz / 100.0 # m/s (climb rate)
                
                # Distance from home
                if not self.home_set:
                    self.home_lat = self.state.latitude
                    self.home_lon = self.state.longitude
                    self.home_set = True
                
                self.state.distance_from_home = self._calculate_distance(
                    self.state.latitude, self.state.longitude, self.home_lat, self.home_lon
                )
                
            elif msg_type == 'SYS_STATUS':
                self.state.battery_voltage = msg.voltage_battery / 1000.0 # to V
                self.state.battery_current = msg.current_battery / 100.0 # to A
                self.state.battery_remaining = float(msg.battery_remaining)
                
            elif msg_type == 'VFR_HUD':
                self.state.ground_speed = msg.groundspeed
                self.state.heading = float(msg.heading)
                self.state.altitude = msg.alt
                self.state.vertical_speed = msg.climb
                
            elif msg_type == 'RADIO_STATUS':
                # Map RSSI (0-254) to percentage
                self.state.radio_signal_quality = int(msg.rssi * 100 / 254)
                # Remrssi represents remote signal quality
                # Errors
                self.state.radio_packet_loss = float(msg.rxerrors)

            elif msg_type == 'SCALED_PRESSURE':
                self.state.baro_pressure = msg.press_abs
                self.state.baro_temp = msg.temperature / 100.0 if msg.temperature > 100 else msg.temperature # temp might be in 0.01 degC
                
            elif msg_type == 'OPTICAL_FLOW' or msg_type == 'OPTICAL_FLOW_RAD':
                # OPTICAL_FLOW fields: flow_x, flow_y, quality
                if hasattr(msg, 'quality'):
                    self.state.optical_flow_quality = msg.quality
                if hasattr(msg, 'flow_comp_m_x'):
                    self.state.optical_flow_x = msg.flow_comp_m_x
                    self.state.optical_flow_y = msg.flow_comp_m_y
                
            elif msg_type == 'RANGEFINDER':
                # RANGEFINDER fields: distance, voltage
                self.state.rangefinder_distance = msg.distance
                
            elif msg_type == 'GPS_RAW_INT':
                self.state.gps_fix = msg.fix_type
                self.state.satellite_count = msg.satellites_visible
                
            elif msg_type == 'HEARTBEAT' and hasattr(msg, 'type') and msg.type == 2: # Quadrotor specific
                # Sometimes GPS fix comes through heartbeat status mapping or others, but GPS_RAW_INT is standard.
                pass

    def get_latest_state(self) -> VehicleState:
        with self.lock:
            # Update health status
            updated_state = self.health_monitor.evaluate_health(self.state, self.last_packet_time)
            return updated_state

    def get_raw_messages(self) -> List[Dict[str, Any]]:
        with self.raw_messages_lock:
            return list(self.raw_messages)

    def _calculate_distance(self, lat1, lon1, lat2, lon2) -> float:
        """Calculates distance in meters between two lat/lon coordinates using Haversine formula."""
        if abs(lat1 - lat2) < 1e-7 and abs(lon1 - lon2) < 1e-7:
            return 0.0
        R = 6371000.0 # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2.0)**2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c
