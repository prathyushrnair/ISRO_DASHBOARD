import os
import time
import asyncio
import threading
import logging
from typing import Dict, List, Optional, Callable
import math

try:
    from pymavlink import mavutil
    import serial.tools.list_ports
except ImportError:
    mavutil = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAVLinkManager")

class MockMAVLinkMessage:
    def __init__(self, msg_type: str, fields: dict):
        self._type = msg_type
        self._fields = fields
        # Expose fields as attributes
        for k, v in fields.items():
            setattr(self, k, v)

    def get_type(self) -> str:
        return self._type

    def get_payload(self) -> dict:
        return self._fields

    def get_msgId(self) -> int:
        return hash(self._type) & 0xFFFF

class MAVLinkManager:
    def __init__(self):
        self.connection = None
        self.device = None
        self.baud = 57600
        
        self.is_connected = False
        self.is_simulating = False
        self.last_heartbeat_time = 0.0
        self.running = False
        
        self.message_callbacks: List[Callable] = []
        self.connection_callbacks: List[Callable] = []
        self.log_callbacks: List[Callable] = []
        
        # Thread handles
        self.read_thread: Optional[threading.Thread] = None
        self.sim_thread: Optional[threading.Thread] = None
        
        # Simulator state variables
        self.sim_state = {
            "armed": False,
            "mode": "STABILIZE",
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "heading": 0.0,
            "lat": 13.0827,       # Initial location (e.g. ISRO/Chennai)
            "lon": 80.2707,
            "alt": 0.0,
            "relative_alt": 0.0,
            "ground_speed": 0.0,
            "vertical_speed": 0.0,
            "battery_volt": 12.6, # 3S fully charged
            "battery_curr": 0.0,
            "battery_remaining": 100,
            "time_in_air": 0.0,
            "sat_count": 12,
            "gps_fix": 3, # 3D Fix
            "home_lat": 13.0827,
            "home_lon": 80.2707,
            "home_alt": 10.0,
            "optical_flow_x": 0.0,
            "optical_flow_y": 0.0,
            "optical_flow_qual": 255,
            "rangefinder_dist": 0.0,
            "ekf_variance": 0.1,
            "rssi": 200,
        }
        
    def add_message_callback(self, callback: Callable):
        self.message_callbacks.append(callback)
        
    def add_connection_callback(self, callback: Callable):
        self.connection_callbacks.append(callback)
        
    def add_log_callback(self, callback: Callable):
        self.log_callbacks.append(callback)

    def log_event(self, level: str, message: str):
        # Notify logging service
        timestamp = time.time()
        for cb in self.log_callbacks:
            try:
                cb(level, message, timestamp)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")

    def notify_connection_state(self, connected: bool):
        self.is_connected = connected
        for cb in self.connection_callbacks:
            try:
                cb(connected)
            except Exception as e:
                logger.error(f"Error in connection callback: {e}")

    def get_available_ports(self) -> List[str]:
        ports = ["SIMULATOR"]
        try:
            com_ports = serial.tools.list_ports.comports()
            for port in com_ports:
                ports.append(port.device)
        except Exception as e:
            logger.error(f"Error listing serial ports: {e}")
        return ports

    def connect(self, device: str, baud: int = 57600) -> bool:
        if self.is_connected:
            self.disconnect()
            
        self.device = device
        self.baud = baud
        self.running = True
        
        if device == "SIMULATOR":
            self.is_simulating = True
            self.last_heartbeat_time = time.time()
            self.notify_connection_state(True)
            self.log_event("INFO", f"Connected to virtual MAVLink vehicle on {device}")
            
            # Start simulation thread
            self.sim_thread = threading.Thread(target=self._run_simulation, daemon=True)
            self.sim_thread.start()
            return True
        else:
            if mavutil is None:
                self.log_event("ERROR", "PyMAVLink is not installed. Fallback to SIMULATOR is recommended.")
                return False
            
            try:
                self.log_event("INFO", f"Opening serial port {device} at {baud}...")
                self.connection = mavutil.mavlink_connection(device, baud=baud)
                self.is_simulating = False
                
                # Start read thread
                self.read_thread = threading.Thread(target=self._run_serial_reader, daemon=True)
                self.read_thread.start()
                return True
            except Exception as e:
                self.log_event("ERROR", f"Failed to connect to {device}: {str(e)}")
                self.notify_connection_state(False)
                return False

    def disconnect(self):
        self.running = False
        self.is_simulating = False
        
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Error closing serial: {e}")
            self.connection = None
            
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
            
        if self.sim_thread and self.sim_thread.is_alive():
            self.sim_thread.join(timeout=1.0)
            
        self.notify_connection_state(False)
        self.log_event("INFO", f"Disconnected from MAVLink link")

    def set_mode(self, mode_name: str) -> bool:
        if self.is_simulating:
            if mode_name in ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "AUTO", "RTL", "LAND"]:
                self.sim_state["mode"] = mode_name
                self.log_event("INFO", f"Changed flight mode to {mode_name}")
                return True
            return False
        
        if not self.is_connected or not self.connection:
            return False
        
        try:
            # ArduPilot specific mode change
            mode_id = self.connection.mode_mapping().get(mode_name)
            if mode_id is None:
                self.log_event("WARNING", f"Mode {mode_name} not supported by vehicle")
                return False
                
            self.connection.set_mode(mode_id)
            self.log_event("INFO", f"Commanded mode change to {mode_name}")
            return True
        except Exception as e:
            self.log_event("ERROR", f"Failed to set mode: {e}")
            return False

    def arm_disarm(self, arm: bool) -> bool:
        if self.is_simulating:
            self.sim_state["armed"] = arm
            state_str = "ARMED" if arm else "DISARMED"
            self.log_event("INFO", f"Vehicle {state_str}")
            if arm:
                self.sim_state["battery_curr"] = 5.0
            else:
                self.sim_state["battery_curr"] = 0.5
            return True
            
        if not self.is_connected or not self.connection:
            return False
            
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1 if arm else 0, # parameter 1: 1 to arm, 0 to disarm
                0, 0, 0, 0, 0, 0
            )
            state_str = "ARM" if arm else "DISARM"
            self.log_event("INFO", f"Sent command {state_str} to vehicle")
            return True
        except Exception as e:
            self.log_event("ERROR", f"Failed to send ARM/DISARM: {e}")
            return False

    def send_command(self, cmd_id: int, p1=0.0, p2=0.0, p3=0.0, p4=0.0, p5=0.0, p6=0.0, p7=0.0) -> bool:
        if self.is_simulating:
            # Handle simulation commands
            if cmd_id == 21: # MAV_CMD_NAV_LAND
                self.sim_state["mode"] = "LAND"
                self.log_event("INFO", "Commanded LAND (simulated)")
            elif cmd_id == 20: # MAV_CMD_NAV_RETURN_TO_LAUNCH
                self.sim_state["mode"] = "RTL"
                self.log_event("INFO", "Commanded RTL (simulated)")
            return True
            
        if not self.is_connected or not self.connection:
            return False
            
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                cmd_id,
                0, p1, p2, p3, p4, p5, p6, p7
            )
            return True
        except Exception as e:
            self.log_event("ERROR", f"Failed to send MAVLink command {cmd_id}: {e}")
            return False

    def _run_serial_reader(self):
        self.last_heartbeat_time = time.time()
        self.notify_connection_state(True)
        
        # Configure data streams
        try:
            # Request all streams at 10Hz
            self.connection.mav.request_data_stream_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                10, # 10 Hz
                1
            )
        except Exception as e:
            logger.error(f"Error requesting data streams: {e}")

        while self.running and self.connection:
            try:
                msg = self.connection.recv_match(blocking=True, timeout=0.1)
                if msg is None:
                    # Check heartbeat timeout (if no heartbeat for 5.0 seconds)
                    if time.time() - self.last_heartbeat_time > 5.0 and self.is_connected:
                        self.log_event("WARNING", "MAVLink heartbeat timeout! Connection lost.")
                        self.notify_connection_state(False)
                        # Start reconnection loop in background
                        self._trigger_reconnect()
                        break
                    continue
                
                # Check for heartbeat to keep link active
                if msg.get_type() == 'HEARTBEAT':
                    self.last_heartbeat_time = time.time()
                    if not self.is_connected:
                        self.log_event("INFO", "MAVLink connection recovered")
                        self.notify_connection_state(True)
                
                # Deliver message to listeners
                for callback in self.message_callbacks:
                    try:
                        callback(msg)
                    except Exception as ex:
                        logger.error(f"Error in msg callback: {ex}")
                        
            except Exception as e:
                logger.error(f"Error in serial reader: {e}")
                self.log_event("ERROR", f"Serial communication error: {str(e)}")
                self.notify_connection_state(False)
                self._trigger_reconnect()
                break

    def _trigger_reconnect(self):
        if not self.running:
            return
        logger.info("Triggering automatic reconnection...")
        threading.Thread(target=self._reconnect_loop, daemon=True).start()

    def _reconnect_loop(self):
        while self.running and not self.is_connected:
            self.log_event("INFO", f"Attempting automatic reconnect to {self.device}...")
            if self.connect(self.device, self.baud):
                break
            time.sleep(3.0) # Wait before retry

    def _run_simulation(self):
        """Generates realistic vehicle states and MAVLink messages at 10 Hz."""
        tick = 0
        while self.running and self.is_simulating:
            start_time = time.time()
            tick += 1
            
            # 1. Physics update based on Flight Mode
            self._update_sim_physics()
            
            # 2. Package and emit Mock Messages to represent real stream
            messages = self._generate_sim_messages(tick)
            
            # Send to telemetry service callbacks
            for msg in messages:
                for callback in self.message_callbacks:
                    try:
                        callback(msg)
                    except Exception as e:
                        logger.error(f"Error in callback parsing simulated message {msg.get_type()}: {e}")
            
            # Delay to maintain 10 Hz telemetry loop (100ms)
            elapsed = time.time() - start_time
            sleep_time = max(0.01, 0.1 - elapsed)
            time.sleep(sleep_time)

    def _update_sim_physics(self):
        """Simulates drone dynamics for altitude, attitude, and battery discharge."""
        mode = self.sim_state["mode"]
        armed = self.sim_state["armed"]
        
        # Battery drain simulation
        if self.sim_state["battery_remaining"] > 0:
            drain = (0.005 if armed else 0.0005)
            self.sim_state["battery_remaining"] = max(0, self.sim_state["battery_remaining"] - drain)
            # 12.6V down to 9.9V
            self.sim_state["battery_volt"] = 9.9 + (2.7 * (self.sim_state["battery_remaining"] / 100.0))
            if armed:
                # Oscillate current depending on movement
                self.sim_state["battery_curr"] = 10.0 + 5.0 * math.sin(time.time())
            else:
                self.sim_state["battery_curr"] = 0.5
        else:
            self.sim_state["battery_remaining"] = 0
            self.sim_state["battery_volt"] = 9.5
            self.sim_state["battery_curr"] = 0.0
            if armed:
                self.sim_state["armed"] = False
                self.sim_state["mode"] = "LAND"
                self.log_event("CRITICAL", "Battery depleted! Vehicle DISARMED automatically.")

        # Pitch & Roll noise simulation
        self.sim_state["roll"] = 2.0 * math.sin(time.time() * 2.0)
        self.sim_state["pitch"] = 1.5 * math.cos(time.time() * 1.5)
        
        # Flight mode behavior
        if armed:
            if mode == "STABILIZE":
                self.sim_state["vertical_speed"] = 0.0
                self.sim_state["ground_speed"] = 0.0
                # Slightly hover near ground
                if self.sim_state["relative_alt"] < 0.2:
                    self.sim_state["relative_alt"] += 0.02
            
            elif mode in ["ALT_HOLD", "LOITER", "GUIDED"]:
                # Target alt: climb to 15m
                target_alt = 15.0
                diff = target_alt - self.sim_state["relative_alt"]
                self.sim_state["vertical_speed"] = clip(diff * 0.5, -2.0, 2.0)
                self.sim_state["relative_alt"] += self.sim_state["vertical_speed"] * 0.1
                
                # Ground speed drift
                self.sim_state["ground_speed"] = 0.2 + abs(0.3 * math.sin(time.time()))
                self.sim_state["heading"] = (self.sim_state["heading"] + 0.1) % 360
                
            elif mode == "RTL":
                # Go home and land
                # First climb to 20m RTL Alt
                rtl_alt = 20.0
                if self.sim_state["relative_alt"] < (rtl_alt - 0.5):
                    self.sim_state["vertical_speed"] = 1.5
                    self.sim_state["relative_alt"] += 0.15
                    self.sim_state["ground_speed"] = 0.5
                else:
                    # Fly back home (simulate position converging to home)
                    self.sim_state["vertical_speed"] = 0.0
                    dist = self.sim_state["relative_alt"] # Simplification
                    lat_diff = self.sim_state["home_lat"] - self.sim_state["lat"]
                    lon_diff = self.sim_state["home_lon"] - self.sim_state["lon"]
                    dist_to_home = math.sqrt(lat_diff**2 + lon_diff**2)
                    
                    if dist_to_home > 0.00001:
                        self.sim_state["lat"] += (lat_diff * 0.05)
                        self.sim_state["lon"] += (lon_diff * 0.05)
                        self.sim_state["ground_speed"] = 4.5
                        self.sim_state["heading"] = math.degrees(math.atan2(lon_diff, lat_diff)) % 360
                    else:
                        # Arrived Home! Switch to LAND
                        self.sim_state["mode"] = "LAND"
                        self.log_event("INFO", "RTL: Arrived Home, switching to LAND")
                        
            elif mode == "LAND":
                # Descend at 0.7 m/s
                self.sim_state["vertical_speed"] = -0.7
                self.sim_state["relative_alt"] = max(0.0, self.sim_state["relative_alt"] - 0.07)
                self.sim_state["ground_speed"] = max(0.0, self.sim_state["ground_speed"] - 0.2)
                
                if self.sim_state["relative_alt"] <= 0.01:
                    self.sim_state["relative_alt"] = 0.0
                    self.sim_state["armed"] = False
                    self.sim_state["vertical_speed"] = 0.0
                    self.sim_state["mode"] = "STABILIZE"
                    self.log_event("INFO", "Landed successfully. Disarming vehicle.")
                    
            elif mode == "AUTO":
                # Climb and circle home
                if self.sim_state["relative_alt"] < 30.0:
                    self.sim_state["relative_alt"] += 0.2
                    self.sim_state["vertical_speed"] = 2.0
                else:
                    self.sim_state["vertical_speed"] = 0.0
                self.sim_state["ground_speed"] = 6.0
                self.sim_state["heading"] = (self.sim_state["heading"] + 2.0) % 360
                # Move drone in circle
                rad = math.radians(self.sim_state["heading"])
                self.sim_state["lat"] = self.sim_state["home_lat"] + 0.0005 * math.cos(rad)
                self.sim_state["lon"] = self.sim_state["home_lon"] + 0.0005 * math.sin(rad)
                
        else:
            # Idle on ground
            self.sim_state["vertical_speed"] = 0.0
            self.sim_state["ground_speed"] = 0.0
            if self.sim_state["relative_alt"] > 0.0:
                # Fall down to ground
                self.sim_state["relative_alt"] = max(0.0, self.sim_state["relative_alt"] - 0.1)
        
        # Update absolute altitude
        self.sim_state["alt"] = self.sim_state["home_alt"] + self.sim_state["relative_alt"]
        self.sim_state["yaw"] = self.sim_state["heading"]
        
        # Optical Flow simulation (proportional to ground speed)
        if self.sim_state["relative_alt"] > 0.1:
            self.sim_state["optical_flow_x"] = 0.5 * self.sim_state["ground_speed"] * math.cos(math.radians(self.sim_state["yaw"]))
            self.sim_state["optical_flow_y"] = 0.5 * self.sim_state["ground_speed"] * math.sin(math.radians(self.sim_state["yaw"]))
            self.sim_state["optical_flow_qual"] = 230
            self.sim_state["rangefinder_dist"] = self.sim_state["relative_alt"]
        else:
            self.sim_state["optical_flow_x"] = 0.0
            self.sim_state["optical_flow_y"] = 0.0
            self.sim_state["optical_flow_qual"] = 255
            self.sim_state["rangefinder_dist"] = 0.0
            
        # Sim radio signal noise
        self.sim_state["rssi"] = max(100, min(254, int(200 + 5.0 * math.sin(time.time() * 0.5))))

    def _generate_sim_messages(self, tick: int) -> List[MockMAVLinkMessage]:
        messages = []
        
        # 1. HEARTBEAT (every 1.0s or tick % 10 == 0)
        if tick % 10 == 0:
            base_mode = 0
            if self.sim_state["armed"]:
                base_mode |= 128 # MAV_MODE_FLAG_SAFETY_ARMED
            
            # Map custom flight mode to index (ArduPilot Copter)
            mode_mapping = {"STABILIZE": 0, "ALT_HOLD": 2, "LOITER": 5, "GUIDED": 4, "AUTO": 3, "RTL": 6, "LAND": 9}
            custom_mode = mode_mapping.get(self.sim_state["mode"], 0)
            
            messages.append(MockMAVLinkMessage("HEARTBEAT", {
                "type": 2,          # MAV_TYPE_QUADROTOR
                "autopilot": 3,     # MAV_AUTOPILOT_ARDUPILOTMEGA
                "base_mode": base_mode,
                "custom_mode": custom_mode,
                "system_status": 4, # MAV_STATE_ACTIVE
                "mavlink_version": 3
            }))
            
        # 2. ATTITUDE (every 100ms)
        messages.append(MockMAVLinkMessage("ATTITUDE", {
            "time_boot_ms": tick * 100,
            "roll": math.radians(self.sim_state["roll"]),
            "pitch": math.radians(self.sim_state["pitch"]),
            "yaw": math.radians(self.sim_state["yaw"]),
            "rollspeed": 0.01,
            "pitchspeed": 0.01,
            "yawspeed": 0.02
        }))
        
        # 3. GLOBAL_POSITION_INT (every 100ms)
        messages.append(MockMAVLinkMessage("GLOBAL_POSITION_INT", {
            "time_boot_ms": tick * 100,
            "lat": int(self.sim_state["lat"] * 1e7),
            "lon": int(self.sim_state["lon"] * 1e7),
            "alt": int(self.sim_state["alt"] * 1000), # mm
            "relative_alt": int(self.sim_state["relative_alt"] * 1000), # mm
            "vx": int(self.sim_state["ground_speed"] * math.cos(math.radians(self.sim_state["yaw"])) * 100),
            "vy": int(self.sim_state["ground_speed"] * math.sin(math.radians(self.sim_state["yaw"])) * 100),
            "vz": int(self.sim_state["vertical_speed"] * 100),
            "hdg": int(self.sim_state["heading"] * 100) # cdeg
        }))
        
        # 4. SYS_STATUS (every 200ms)
        if tick % 2 == 0:
            messages.append(MockMAVLinkMessage("SYS_STATUS", {
                "onboard_control_sensors_present": 0xFFFFFFFF,
                "onboard_control_sensors_enabled": 0xFFFFFFFF,
                "onboard_control_sensors_health": 0xFFFFFFFF,
                "load": 120, # 12% CPU load
                "voltage_battery": int(self.sim_state["battery_volt"] * 1000), # mV
                "current_battery": int(self.sim_state["battery_curr"] * 100), # cA
                "battery_remaining": int(self.sim_state["battery_remaining"]), # %
                "drop_rate_comm": 0,
                "errors_comm": 0,
                "errors_count1": 0,
                "errors_count2": 0,
                "errors_count3": 0,
                "errors_count4": 0,
            }))
            
        # 5. VFR_HUD (every 100ms)
        messages.append(MockMAVLinkMessage("VFR_HUD", {
            "airspeed": self.sim_state["ground_speed"],
            "groundspeed": self.sim_state["ground_speed"],
            "heading": int(self.sim_state["heading"]),
            "throttle": 50 if self.sim_state["armed"] else 0,
            "alt": self.sim_state["alt"],
            "climb": self.sim_state["vertical_speed"]
        }))
        
        # 6. EKF_STATUS_REPORT (every 500ms)
        if tick % 5 == 0:
            messages.append(MockMAVLinkMessage("EKF_STATUS_REPORT", {
                "flags": 0x03FF, # EKF healthy flags
                "velocity_variance": self.sim_state["ekf_variance"],
                "pos_horizontal_variance": self.sim_state["ekf_variance"],
                "pos_vertical_variance": self.sim_state["ekf_variance"],
                "compass_variance": 0.05,
                "terrain_alt_variance": 0.0,
                "airspeed_variance": 0.0
            }))

        # 7. RADIO_STATUS (every 1.0s)
        if tick % 10 == 0:
            messages.append(MockMAVLinkMessage("RADIO_STATUS", {
                "rssi": self.sim_state["rssi"],
                "remrssi": self.sim_state["rssi"] - 5,
                "txbuf": 100,
                "noise": 30,
                "remnoise": 25,
                "rxerrors": 0,
                "fixed": 0
            }))

        # 8. RAW_IMU (every 100ms)
        messages.append(MockMAVLinkMessage("RAW_IMU", {
            "time_usec": tick * 100000,
            "xacc": int(10 * math.sin(time.time())),
            "yacc": int(15 * math.cos(time.time())),
            "zacc": -980 + int(5 * math.sin(time.time())),
            "xgyro": 0,
            "ygyro": 0,
            "zgyro": 0,
            "xmag": 200,
            "ymag": 100,
            "zmag": 50
        }))
        
        # 9. SCALED_PRESSURE (every 200ms)
        if tick % 2 == 0:
            messages.append(MockMAVLinkMessage("SCALED_PRESSURE", {
                "time_boot_ms": tick * 100,
                "press_abs": 1013.25 - (self.sim_state["relative_alt"] * 0.12), # simple baro model
                "press_diff": 0.0,
                "temperature": 25 + int(self.sim_state["relative_alt"] * -0.006)
            }))
            
        return messages

def clip(val, min_val, max_val):
    return max(min_val, min(val, max_val))
