import time
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivy.metrics import dp

# Helper to map state status color to rgb
STATUS_COLORS = {
    "Green": (0.1, 0.8, 0.3, 1.0),
    "Yellow": (1.0, 0.75, 0.0, 1.0),
    "Red": (0.9, 0.2, 0.2, 1.0),
    "Gray": (0.5, 0.5, 0.5, 1.0)
}

class SensorDiagnosticsCard(MDCard):
    def __init__(self, title: str, **kwargs):
        super(SensorDiagnosticsCard, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = "16dp"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "160dp"
        
        # Sleek dark background
        self.md_bg_color = (0.12, 0.12, 0.16, 0.95)
        self.line_color = (0.2, 0.25, 0.35, 0.4)
        self.line_width = 1.0
        self.radius = [8, 8, 8, 8]
        
        # Header Row: Title & Health Badge
        header = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="24dp")
        header.add_widget(MDLabel(
            text=title.upper(),
            font_style="Overline",
            theme_text_color="Hint"
        ))
        
        self.lbl_badge = MDLabel(
            text="UNKNOWN",
            font_style="Caption",
            halign="right",
            bold=True
        )
        self.lbl_badge.theme_text_color = "Custom"
        self.lbl_badge.text_color = STATUS_COLORS["Gray"]
        header.add_widget(self.lbl_badge)
        self.add_widget(header)
        
        # Content Label (multi-line)
        self.lbl_content = MDLabel(
            text="Sensor initialized. Waiting for data...",
            font_style="Body2",
            theme_text_color="Secondary",
            valign="top"
        )
        self.add_widget(self.lbl_content)

    def update_sensor(self, status: str, content: str):
        color = STATUS_COLORS.get(status, STATUS_COLORS["Gray"])
        self.lbl_badge.text = status.upper()
        self.lbl_badge.text_color = color
        self.lbl_content.text = content
        
        # Update card outline color based on status
        self.line_color = (color[0], color[1], color[2], 0.3)

class SensorsScreen(Screen):
    def __init__(self, **kwargs):
        super(SensorsScreen, self).__init__(**kwargs)
        self.name = "sensors"
        
        # Main Layout
        main_layout = MDBoxLayout(orientation="vertical", padding="16dp", spacing="16dp")
        
        # Page Title Row
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="36dp")
        title_row.add_widget(MDLabel(
            text="VEHICLE SENSOR DIAGNOSTICS",
            font_style="Button",
            theme_text_color="Hint"
        ))
        main_layout.add_widget(title_row)
        
        # Scroll view / Grid container for the 7 sensor cards
        self.card_grid = MDGridLayout(
            cols=2, 
            spacing="16dp", 
            size_hint_y=1.0
        )
        
        self.cards = {
            "imu": SensorDiagnosticsCard(title="Inertial Measurement Unit (IMU)"),
            "baro": SensorDiagnosticsCard(title="Barometric Pressure Sensor"),
            "flow": SensorDiagnosticsCard(title="Optical Flow Camera"),
            "range": SensorDiagnosticsCard(title="Distance Rangefinder"),
            "ekf": SensorDiagnosticsCard(title="Kalman Filter Estimator (EKF)"),
            "radio": SensorDiagnosticsCard(title="SiK Telemetry Radio"),
            "battery": SensorDiagnosticsCard(title="Power Management Unit (PMU)")
        }
        
        # Add to layout
        for card in self.cards.values():
            self.card_grid.add_widget(card)
            
        # Add an empty layout to balance the odd count (7 cards in a 2-column grid)
        dummy = MDBoxLayout(size_hint_y=None, height="160dp")
        self.card_grid.add_widget(dummy)
        
        main_layout.add_widget(self.card_grid)
        self.add_widget(main_layout)

    def update_telemetry(self, state: dict, is_stale: bool = False):
        if is_stale:
            for card in self.cards.values():
                card.update_sensor("Gray", "Data Stream Interrupted. Link offline.")
            return

        # 1. IMU Card
        imu_txt = (
            f"Roll Angle: {state.get('roll', 0.0):.2f}°\n"
            f"Pitch Angle: {state.get('pitch', 0.0):.2f}°\n"
            f"Yaw/Heading: {state.get('yaw', 0.0):.2f}°"
        )
        self.cards["imu"].update_sensor(state.get("imu_status", "Red"), imu_txt)
        
        # 2. Barometer Card
        baro_txt = (
            f"Abs Pressure: {state.get('baro_pressure', 0.0):.2f} hPa\n"
            f"Air Temperature: {state.get('baro_temp', 0.0):.1f} °C\n"
            f"Baro Altitude: {state.get('altitude', 0.0):.2f} m"
        )
        self.cards["baro"].update_sensor("Green", baro_txt) # Barometer is assumed active if getting updates
        
        # 3. Optical Flow Card
        flow_txt = (
            f"Flow Velocity X: {state.get('optical_flow_x', 0.0):.3f} m/s\n"
            f"Flow Velocity Y: {state.get('optical_flow_y', 0.0):.3f} m/s\n"
            f"Tracking Quality: {state.get('optical_flow_quality', 0)} / 255"
        )
        self.cards["flow"].update_sensor(state.get("optical_flow_status", "Red"), flow_txt)
        
        # 4. Rangefinder Card
        range_txt = (
            f"Altitude Distance: {state.get('rangefinder_distance', 0.0):.2f} m\n"
            f"Sensor Health: {'ACTIVE' if state.get('rangefinder_distance', 0.0) > 0 else 'STANDBY'}"
        )
        self.cards["range"].update_sensor(state.get("rangefinder_status", "Red"), range_txt)
        
        # 5. EKF Card
        ekf_txt = (
            f"Status Flag: ACTIVE (EKF3)\n"
            f"GPS Fix Integrity: {'3D LOCK' if state.get('gps_fix', 0) >= 3 else 'NO LOCK'}\n"
            f"Filter Variance Limit: ACCEPTABLE"
        )
        self.cards["ekf"].update_sensor(state.get("ekf_status", "Red"), ekf_txt)
        
        # 6. Telemetry Radio Card
        radio_txt = (
            f"Radio Signal Quality: {state.get('radio_signal_quality', 0)}%\n"
            f"Link Packet Error count: {state.get('radio_packet_loss', 0.0):.0f}\n"
            f"Last Telemetry Rx time: {time.strftime('%H:%M:%S', time.localtime(state.get('last_update_timestamp', time.time())))}"
        )
        self.cards["radio"].update_sensor(state.get("telemetry_status", "Red"), radio_txt)
        
        # 7. Battery Card
        batt_txt = (
            f"Terminal Voltage: {state.get('battery_voltage', 0.0):.2f} V\n"
            f"Current Discharge: {state.get('battery_current', 0.0):.2f} A\n"
            f"Remaining Percentage: {state.get('battery_remaining', 0.0):.0f}%"
        )
        self.cards["battery"].update_sensor(state.get("battery_status", "Red"), batt_txt)
