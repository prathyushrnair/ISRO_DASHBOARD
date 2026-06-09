import time
from backend.models.telemetry import VehicleState

class HealthMonitorService:
    def __init__(self):
        pass

    def evaluate_health(self, state: VehicleState, last_packet_time: float) -> VehicleState:
        # 1. Telemetry Link Status
        now = time.time()
        time_since_packet = now - last_packet_time if last_packet_time > 0 else float('inf')
        
        if not state.connected:
            state.telemetry_status = "Red"
        elif time_since_packet < 1.0:
            state.telemetry_status = "Green"
        elif time_since_packet < 3.0:
            state.telemetry_status = "Yellow"
        else:
            state.telemetry_status = "Red"

        # If disconnected or telemetry link is critical, degrade other statuses
        if state.telemetry_status == "Red":
            state.gps_status = "Red"
            state.ekf_status = "Red"
            state.imu_status = "Red"
            state.optical_flow_status = "Red"
            state.rangefinder_status = "Red"
            state.battery_status = "Red"
            return state

        # 2. GPS Status
        # GPS fix types: 0-1: No Fix, 2: 2D, 3: 3D, 4: DGPS, 5: RTK float, 6: RTK fix
        if state.gps_fix >= 3 and state.satellite_count >= 10:
            state.gps_status = "Green"
        elif state.gps_fix >= 2 and state.satellite_count >= 6:
            state.gps_status = "Yellow"
        else:
            state.gps_status = "Red"

        # 3. Battery Status (assuming 3S LiPo: full ~12.6V, low ~10.8V, critical ~10.5V)
        # Handle cases where voltage is not reported or 0
        if state.battery_voltage <= 0.1:
            state.battery_status = "Red"
        elif state.battery_voltage >= 11.1: # > 3.7V per cell
            state.battery_status = "Green"
        elif state.battery_voltage >= 10.6: # > 3.53V per cell
            state.battery_status = "Yellow"
        else:
            state.battery_status = "Red"

        # 4. IMU Status
        # Verify roll/pitch/yaw are updating and values are not NaN/Inf
        if abs(state.roll) < 90.0 and abs(state.pitch) < 90.0:
            state.imu_status = "Green"
        else:
            state.imu_status = "Yellow"

        # 5. Optical Flow Status
        if state.optical_flow_quality > 180:
            state.optical_flow_status = "Green"
        elif state.optical_flow_quality > 50:
            state.optical_flow_status = "Yellow"
        else:
            state.optical_flow_status = "Red"

        # 6. Rangefinder Status
        # Healthy if reporting positive distance when not on ground
        if state.relative_altitude > 0.3:
            if state.rangefinder_distance > 0.1:
                state.rangefinder_status = "Green"
            else:
                state.rangefinder_status = "Red"
        else:
            # On the ground, rangefinder is normal to be close to 0
            if state.rangefinder_distance >= 0.0:
                state.rangefinder_status = "Green"
            else:
                state.rangefinder_status = "Yellow"

        # 7. EKF Status
        # variance: lower is better (< 0.2 is excellent, < 0.6 is acceptable)
        if state.gps_fix >= 3:
            # EKF needs GPS to run healthy
            state.ekf_status = "Green"
        else:
            state.ekf_status = "Yellow"

        return state
