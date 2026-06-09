from pydantic import BaseModel
from typing import Optional

class VehicleState(BaseModel):
    # Connection / Armed / Mode
    connected: bool = False
    armed: bool = False
    mode: str = "UNKNOWN"
    
    # Battery summary
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    battery_remaining: float = 0.0
    
    # Attitude
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    heading: float = 0.0
    
    # Altitude and Speed
    altitude: float = 0.0
    relative_altitude: float = 0.0
    ground_speed: float = 0.0
    vertical_speed: float = 0.0
    
    # GPS summary
    gps_fix: int = 0  # 0-1: No Fix, 2: 2D, 3: 3D, etc.
    satellite_count: int = 0
    distance_from_home: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    
    # Sensor values
    baro_pressure: float = 1013.25
    baro_temp: float = 25.0
    optical_flow_x: float = 0.0
    optical_flow_y: float = 0.0
    optical_flow_quality: int = 0
    rangefinder_distance: float = 0.0
    
    # Telemetry Radio
    radio_signal_quality: int = 100
    radio_packet_loss: float = 0.0
    
    # Health Indicators (Green / Yellow / Red)
    gps_status: str = "Red"
    ekf_status: str = "Red"
    imu_status: str = "Red"
    optical_flow_status: str = "Red"
    rangefinder_status: str = "Red"
    telemetry_status: str = "Red"
    battery_status: str = "Red"
    
    # Timestamps
    last_update_timestamp: float = 0.0
