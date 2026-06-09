import time
import asyncio
import logging
from typing import Callable

from backend.services.mavlink_manager import MAVLinkManager
from backend.services.telemetry_service import TelemetryService
from backend.services.websocket_service import WebSocketService

logger = logging.getLogger("CommandService")

class CommandService:
    def __init__(
        self, 
        mavlink_manager: MAVLinkManager, 
        telemetry_service: TelemetryService,
        websocket_service: WebSocketService
    ):
        self.mavlink_manager = mavlink_manager
        self.telemetry_service = telemetry_service
        self.websocket_service = websocket_service
        self.kill_task = None

    def arm_vehicle(self) -> bool:
        self.log_to_gcs("INFO", "GCS: Arming command requested")
        return self.mavlink_manager.arm_disarm(True)

    def disarm_vehicle(self) -> bool:
        self.log_to_gcs("INFO", "GCS: Disarming command requested")
        return self.mavlink_manager.arm_disarm(False)

    def set_mode(self, mode_name: str) -> bool:
        self.log_to_gcs("INFO", f"GCS: Flight Mode change requested: {mode_name}")
        return self.mavlink_manager.set_mode(mode_name)

    def rtl(self) -> bool:
        self.log_to_gcs("INFO", "GCS: RTL command requested")
        return self.mavlink_manager.set_mode("RTL")

    def land(self) -> bool:
        self.log_to_gcs("INFO", "GCS: Land command requested")
        return self.mavlink_manager.set_mode("LAND")

    def trigger_emergency_kill(self) -> bool:
        """Starts the asynchronous emergency smart kill sequence."""
        self.log_to_gcs("CRITICAL", "EMERGENCY SMART KILL ACTIVATED!")
        
        # If there's an ongoing task, cancel it
        if self.kill_task and not self.kill_task.done():
            self.kill_task.cancel()
            
        loop = self.websocket_service.loop
        if loop and loop.is_running():
            self.kill_task = asyncio.run_coroutine_threadsafe(
                self._run_smart_kill_sequence(), 
                loop
            )
            return True
        else:
            # Fallback if async loop is not available, run in thread
            import threading
            threading.Thread(target=self._run_smart_kill_sequence_sync, daemon=True).start()
            return True

    async def _run_smart_kill_sequence(self):
        """Asynchronous execution steps of the Emergency Smart Kill sequence."""
        try:
            state = self.telemetry_service.get_latest_state()
            
            # Step 1: Command Hover (LOITER) if possible and vehicle is airborne
            if state.armed and state.relative_altitude > 0.5:
                self.log_to_gcs("WARNING", "Smart Kill: Step 1/4 - Commanding hover mode (LOITER)")
                self.mavlink_manager.set_mode("LOITER")
                await asyncio.sleep(1.5)
            else:
                self.log_to_gcs("INFO", "Smart Kill: Vehicle not airborne. Skipping hover stage.")

            # Step 2: Command LAND
            self.log_to_gcs("WARNING", "Smart Kill: Step 2/4 - Commanding LAND")
            self.mavlink_manager.set_mode("LAND")
            
            # Step 3: Wait for landing confirmation
            self.log_to_gcs("WARNING", "Smart Kill: Step 3/4 - Monitoring altitude sensor for touchdown")
            
            timeout = 30 # 30 seconds max landing wait
            start_time = time.time()
            landed = False
            
            while time.time() - start_time < timeout:
                await asyncio.sleep(0.5)
                state = self.telemetry_service.get_latest_state()
                
                # If vehicle was disarmed manually or automatically during land
                if not state.armed:
                    self.log_to_gcs("INFO", "Smart Kill: Vehicle disarmed. Landing confirmed.")
                    landed = True
                    break
                    
                # If sensor readings confirm relative altitude is near ground
                if state.relative_altitude <= 0.15:
                    self.log_to_gcs("INFO", f"Smart Kill: Touchdown detected (Alt: {state.relative_altitude:.2f}m).")
                    landed = True
                    break
                
                self.log_to_gcs("INFO", f"Smart Kill: Landing in progress... Altitude: {state.relative_altitude:.1f}m")
            
            if not landed:
                self.log_to_gcs("ERROR", "Smart Kill: Landing timeout exceeded. Proceeding to force disarm.")

            # Step 4: Disarm Vehicle
            self.log_to_gcs("CRITICAL", "Smart Kill: Step 4/4 - Sending final DISARM command")
            self.mavlink_manager.arm_disarm(False)
            await asyncio.sleep(1.0)
            
            # Verify final status
            state = self.telemetry_service.get_latest_state()
            if not state.armed:
                self.log_to_gcs("INFO", "Smart Kill sequence completed. Vehicle safe.")
            else:
                self.log_to_gcs("CRITICAL", "Smart Kill Warning: Final DISARM command check failed!")
                
        except asyncio.CancelledError:
            self.log_to_gcs("WARNING", "Smart Kill sequence cancelled by user/override.")
        except Exception as e:
            logger.error(f"Error in smart kill: {e}")
            self.log_to_gcs("ERROR", f"Smart Kill error: {str(e)}")

    def _run_smart_kill_sequence_sync(self):
        """Synchronous version in case async loop is not yet online."""
        state = self.telemetry_service.get_latest_state()
        if state.armed and state.relative_altitude > 0.5:
            self.log_to_gcs("WARNING", "Smart Kill Sync: Step 1/4 - Commanding hover mode (LOITER)")
            self.mavlink_manager.set_mode("LOITER")
            time.sleep(1.5)
            
        self.log_to_gcs("WARNING", "Smart Kill Sync: Step 2/4 - Commanding LAND")
        self.mavlink_manager.set_mode("LAND")
        time.sleep(5.0) # wait arbitrary time in sync fallback
        
        self.log_to_gcs("CRITICAL", "Smart Kill Sync: Step 4/4 - Sending final DISARM command")
        self.mavlink_manager.arm_disarm(False)

    def log_to_gcs(self, level: str, message: str):
        """Pushes events to both local python logs and WebSocket clients."""
        logger.info(f"{level} - {message}")
        # Send raw log broadcast over websocket
        now = time.time()
        self.websocket_service.broadcast("log_update", {
            "level": level,
            "message": message,
            "timestamp": now
        })
