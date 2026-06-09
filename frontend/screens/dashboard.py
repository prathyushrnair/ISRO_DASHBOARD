import requests
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDRectangleFlatButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivy.metrics import dp
from kivy.clock import Clock

from frontend.widgets.status_cards import SystemStatusCard, HealthIndicatorItem
from frontend.widgets.telemetry_cards import TelemetryCard

import logging
logger = logging.getLogger("DashboardScreen")

class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super(DashboardScreen, self).__init__(**kwargs)
        self.name = "dashboard"
        self.dialog = None
        
        # Main Layout (Padding around the page)
        main_layout = MDBoxLayout(orientation="vertical", padding="16dp", spacing="16dp")
        
        # Page Title Row
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="36dp")
        title_row.add_widget(MDLabel(
            text="OPERATIONAL OVERVIEW",
            font_style="Button",
            theme_text_color="Hint"
        ))
        main_layout.add_widget(title_row)
        
        # Core Content Grid: Left Column (Status & Arm Checks) | Right Column (Telemetry Cards & Actions)
        grid = MDGridLayout(cols=2, spacing="16dp", size_hint_y=1.0)
        
        # --- LEFT COLUMN (Status cards) ---
        left_col = MDBoxLayout(orientation="vertical", spacing="16dp", size_hint_x=0.45)
        
        # 1. System Control Card
        self.status_card = SystemStatusCard()
        left_col.add_widget(self.status_card)
        
        # 2. Ready-to-Arm Indicators Card
        self.checks_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="8dp",
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_y=1.0 # occupy remaining height
        )
        self.checks_card.add_widget(MDLabel(
            text="READY-TO-ARM SENSOR INTEGRITY",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        self.health_items = {
            "gps": HealthIndicatorItem(sensor_name="GPS Navigation Link"),
            "ekf": HealthIndicatorItem(sensor_name="Extended Kalman Filter"),
            "imu": HealthIndicatorItem(sensor_name="Inertial Measurement Unit"),
            "flow": HealthIndicatorItem(sensor_name="Optical Flow Sensor"),
            "range": HealthIndicatorItem(sensor_name="Sonar Rangefinder"),
            "telemetry": HealthIndicatorItem(sensor_name="SiK Radio Link Quality"),
            "battery": HealthIndicatorItem(sensor_name="Smart Power Monitor")
        }
        
        for item in self.health_items.values():
            self.checks_card.add_widget(item)
            
        left_col.add_widget(self.checks_card)
        grid.add_widget(left_col)
        
        # --- RIGHT COLUMN (Telemetry & Action Panels) ---
        right_col = MDBoxLayout(orientation="vertical", spacing="16dp", size_hint_x=0.55)
        
        # 1. Mini-Grid of Telemetry Readouts (Battery and GPS status summaries)
        telemetry_grid = MDGridLayout(cols=2, spacing="12dp", size_hint_y=None, height="220dp")
        
        self.card_volt = TelemetryCard(title="Battery Voltage", unit="V")
        self.card_curr = TelemetryCard(title="Battery Current", unit="A")
        self.card_remaining = TelemetryCard(title="Remaining Capacity", unit="%")
        self.card_sats = TelemetryCard(title="Satellites Visible", unit="Sats")
        
        telemetry_grid.add_widget(self.card_volt)
        telemetry_grid.add_widget(self.card_curr)
        telemetry_grid.add_widget(self.card_remaining)
        telemetry_grid.add_widget(self.card_sats)
        
        right_col.add_widget(telemetry_grid)
        
        # 2. GPS Location Card
        self.card_gps = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="8dp",
            md_bg_color=(0.13, 0.13, 0.17, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[6, 6, 6, 6],
            size_hint_y=None,
            height="100dp"
        )
        self.card_gps.add_widget(MDLabel(
            text="NAVIGATION VECTOR STATUS",
            font_style="Overline",
            theme_text_color="Hint"
        ))
        
        self.lbl_gps_details = MDLabel(
            text="GPS Fix: NO FIX  |  Distance From Home: 0.0 m",
            font_style="Body2"
        )
        self.card_gps.add_widget(self.lbl_gps_details)
        right_col.add_widget(self.card_gps)
        
        # 3. Action Buttons Section
        actions_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="12dp",
            md_bg_color=(0.14, 0.12, 0.14, 0.95), # Reddish hue
            line_color=(0.9, 0.3, 0.3, 0.2),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_y=1.0
        )
        actions_card.add_widget(MDLabel(
            text="FLIGHT CONTROL QUICK ACTIONS",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Commands Buttons Layout
        btn_box = MDGridLayout(cols=2, spacing="12dp", size_hint_y=1.0)
        
        btn_arm = MDRaisedButton(
            text="ARM VEHICLE",
            md_bg_color=(0.9, 0.25, 0.25, 1.0),
            size_hint=(1.0, 1.0)
        )
        btn_arm.bind(on_release=self.confirm_arm)
        
        btn_disarm = MDRaisedButton(
            text="DISARM",
            md_bg_color=(0.1, 0.7, 0.3, 1.0),
            size_hint=(1.0, 1.0)
        )
        btn_disarm.bind(on_release=lambda x: self.send_command("disarm"))
        
        btn_rtl = MDRectangleFlatButton(
            text="RETURN TO LAUNCH (RTL)",
            theme_text_color="Custom",
            text_color=(0.2, 0.8, 0.7, 1.0),
            line_color=(0.2, 0.8, 0.7, 0.5),
            size_hint=(1.0, 1.0)
        )
        btn_rtl.bind(on_release=lambda x: self.send_command("rtl"))
        
        btn_land = MDRectangleFlatButton(
            text="LAND",
            theme_text_color="Custom",
            text_color=(0.9, 0.75, 0.1, 1.0),
            line_color=(0.9, 0.75, 0.1, 0.5),
            size_hint=(1.0, 1.0)
        )
        btn_land.bind(on_release=lambda x: self.send_command("land"))
        
        btn_box.add_widget(btn_arm)
        btn_box.add_widget(btn_disarm)
        btn_box.add_widget(btn_rtl)
        btn_box.add_widget(btn_land)
        
        actions_card.add_widget(btn_box)
        
        # Emergency Smart Kill Row
        btn_kill = MDRaisedButton(
            text="EMERGENCY SMART KILL",
            md_bg_color=(0.9, 0.1, 0.1, 1.0),
            size_hint_x=1.0,
            size_hint_y=None,
            height="44dp"
        )
        btn_kill.bind(on_release=self.confirm_kill)
        actions_card.add_widget(btn_kill)
        
        right_col.add_widget(actions_card)
        grid.add_widget(right_col)
        
        main_layout.add_widget(grid)
        self.add_widget(main_layout)

    def update_telemetry(self, state: dict, is_stale: bool = False):
        # 1. Update Status Card
        self.status_card.update_state(
            connected=state.get("connected", False),
            armed=state.get("armed", False),
            mode=state.get("mode", "UNKNOWN"),
            is_stale=is_stale
        )
        
        # 2. Update Health Dots
        self.health_items["gps"].status = state.get("gps_status", "Red") if not is_stale else "Gray"
        self.health_items["ekf"].status = state.get("ekf_status", "Red") if not is_stale else "Gray"
        self.health_items["imu"].status = state.get("imu_status", "Red") if not is_stale else "Gray"
        self.health_items["flow"].status = state.get("optical_flow_status", "Red") if not is_stale else "Gray"
        self.health_items["range"].status = state.get("rangefinder_status", "Red") if not is_stale else "Gray"
        self.health_items["telemetry"].status = state.get("telemetry_status", "Red") if not is_stale else "Gray"
        self.health_items["battery"].status = state.get("battery_status", "Red") if not is_stale else "Gray"
        
        for item in self.health_items.values():
            item.update_ui()
            
        # 3. Update Numeric Telemetry Cards
        self.card_volt.is_stale = is_stale
        self.card_curr.is_stale = is_stale
        self.card_remaining.is_stale = is_stale
        self.card_sats.is_stale = is_stale
        
        self.card_volt.value = f"{state.get('battery_voltage', 0.0):.2f}"
        self.card_curr.value = f"{state.get('battery_current', 0.0):.1f}"
        self.card_remaining.value = f"{state.get('battery_remaining', 0.0):.0f}"
        self.card_sats.value = f"{state.get('satellite_count', 0)}"
        
        # GPS summary text
        gps_fix_map = {0: "NO FIX", 1: "NO FIX", 2: "2D FIX", 3: "3D FIX", 4: "DGPS", 5: "RTK FLOAT", 6: "RTK FIX"}
        fix_val = state.get("gps_fix", 0)
        fix_str = gps_fix_map.get(fix_val, f"FIX_{fix_val}")
        
        if is_stale:
            self.lbl_gps_details.text = "GPS Fix: STALE  |  Distance From Home: STALE"
            self.lbl_gps_details.theme_text_color = "Custom"
            self.lbl_gps_details.text_color = (0.8, 0.7, 0.2, 0.8)
        else:
            self.lbl_gps_details.text = f"GPS Fix: {fix_str}  |  Distance From Home: {state.get('distance_from_home', 0.0):.1f} m"
            self.lbl_gps_details.theme_text_color = "Primary"

    def confirm_arm(self, instance):
        self.dialog = MDDialog(
            title="CONFIRM MOTOR ARMING",
            text="WARNING: This will command the autopilot to engage and spin up motors. Make sure area is clear of personnel and props before proceeding.",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self.dismiss_dialog
                ),
                MDRaisedButton(
                    text="ARM MOTORS",
                    md_bg_color=(0.9, 0.25, 0.25, 1.0),
                    on_release=lambda x: self.send_command_confirmed("arm")
                )
            ]
        )
        self.dialog.open()

    def confirm_kill(self, instance):
        self.dialog = MDDialog(
            title="EMERGENCY SMART KILL CONFIRMATION",
            text="CRITICAL WARNING: This commands the drone to Hover (LOITER), initiate an emergency descent LAND, and DISARM instantly upon touching down. Do you want to initiate emergency smart recovery?",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self.dismiss_dialog
                ),
                MDRaisedButton(
                    text="KILL VEHICLE",
                    md_bg_color=(0.9, 0.1, 0.1, 1.0),
                    on_release=lambda x: self.send_command_confirmed("kill")
                )
            ]
        )
        self.dialog.open()

    def dismiss_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def send_command(self, cmd_path):
        # Single click commands disarm, rtl, land directly
        try:
            res = requests.post(f"http://127.0.0.1:8000/api/command/{cmd_path}", timeout=2.0)
            if res.status_code != 200:
                logger.error(f"Command {cmd_path} failed: {res.text}")
        except Exception as e:
            logger.error(f"Connection exception on command {cmd_path}: {e}")

    def send_command_confirmed(self, cmd_path):
        self.dismiss_dialog()
        self.send_command(cmd_path)
