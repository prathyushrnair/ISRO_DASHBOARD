import os
import sys

# Add project root to path to run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import requests
from typing import List

# 1. Configure Kivy Desktop Window Size before loading other modules
from kivy.config import Config
Config.set('graphics', 'width', '1200')
Config.set('graphics', 'height', '750')
Config.set('graphics', 'minimum_width', '1000')
Config.set('graphics', 'minimum_height', '600')

# Enable cursor support for desktop
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.core.window import Window
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDRectangleFlatIconButton, MDTextButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivy.metrics import dp
from kivy.clock import Clock

# Import Screens & Services
from frontend.screens.connection import ConnectionScreen
from frontend.screens.dashboard import DashboardScreen
from frontend.screens.flight import FlightScreen
from frontend.screens.sensors import SensorsScreen
from frontend.screens.logs import LogsScreen
from frontend.screens.parameters import ParametersScreen
from frontend.screens.settings import SettingsScreen
from frontend.services.websocket_client import WebSocketClient

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GCSFrontend")

class GCSApp(MDApp):
    def __init__(self, **kwargs):
        super(GCSApp, self).__init__(**kwargs)
        # GCS State
        self.connected = False
        self.is_stale = False
        self.last_packet_time = 0.0
        self.vehicle_state = {}
        
        # Navigation History Stack
        self.history: List[str] = []
        self.history_idx = -1
        self.is_navigating_history = False
        
        # WS Client
        self.ws_client = None
        
    def build(self):
        # Configure App Theme
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Orange"
        
        # Base Screen layout: Left Sidebar + Right Panel (Top Bar + ScreenManager)
        self.root_layout = MDBoxLayout(orientation="horizontal", md_bg_color=(0.08, 0.08, 0.1, 1.0))
        
        # --- LEFT SIDEBAR (Hidden on Connection Screen) ---
        self.sidebar = MDCard(
            orientation="vertical",
            size_hint=(None, 1.0),
            width=dp(200),
            md_bg_color=(0.11, 0.11, 0.15, 0.98),
            radius=[0, 0, 0, 0],
            line_color=(0.2, 0.25, 0.35, 0.2),
            line_width=1.0,
            spacing="8dp",
            padding=["8dp", "16dp"]
        )
        
        # Sidebar Logo Header
        sidebar_logo = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="48dp", spacing="8dp", padding=["8dp", 0])
        sidebar_logo.add_widget(MDIconButton(
            icon="radar", theme_icon_color="Custom", icon_color=(0.2, 0.8, 0.7, 1.0), size_hint_x=None, width="36dp"
        ))
        sidebar_logo.add_widget(MDLabel(
            text="GCS LINK", font_style="Subtitle1", bold=True, theme_text_color="Primary"
        ))
        self.sidebar.add_widget(sidebar_logo)
        
        # Sidebar Separator
        self.sidebar.add_widget(MDCard(size_hint_y=None, height="1dp", md_bg_color=(0.2, 0.25, 0.35, 0.3)))
        
        # Navigation Buttons (Dashboard, Flight, Sensors, Logs, Parameters, Settings)
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "view-dashboard", "Dashboard"),
            ("flight", "axis-arrow", "Flight Deck"),
            ("sensors", "sine-wave", "Sensors"),
            ("logs", "console", "Logs / Tracer"),
            ("parameters", "tune", "Parameters"),
            ("settings", "cog", "Settings"),
        ]
        
        for name, icon, label in nav_items:
            btn = MDRectangleFlatIconButton(
                icon=icon,
                text=label,
                theme_text_color="Custom",
                text_color=(0.8, 0.8, 0.8, 0.9),
                line_color=(0, 0, 0, 0),
                theme_icon_color="Custom",
                icon_color=(0.2, 0.8, 0.7, 0.8),
                size_hint_x=1.0,
                halign="left",
                height="44dp"
            )
            # Bind screen navigation
            btn.bind(on_release=lambda x, n=name: self.navigate_to(n))
            self.nav_buttons[name] = btn
            self.sidebar.add_widget(btn)
            
        # Push items to top, add a spacer
        self.sidebar.add_widget(MDBoxLayout(size_hint_y=1.0))
        
        # Disconnect/Link status at bottom
        self.sidebar.add_widget(MDCard(size_hint_y=None, height="1dp", md_bg_color=(0.2, 0.25, 0.35, 0.3)))
        self.btn_disconnect = MDRectangleFlatIconButton(
            icon="link-off",
            text="Disconnect",
            theme_text_color="Custom",
            text_color=(0.9, 0.3, 0.3, 0.9),
            line_color=(0, 0, 0, 0),
            theme_icon_color="Custom",
            icon_color=(0.9, 0.3, 0.3, 0.9),
            size_hint_x=1.0,
            height="44dp"
        )
        self.btn_disconnect.bind(on_release=self.disconnect_link)
        self.sidebar.add_widget(self.btn_disconnect)
        
        self.root_layout.add_widget(self.sidebar)
        
        # --- RIGHT CONTENT PANEL ---
        right_panel = MDBoxLayout(orientation="vertical", size_hint=(1.0, 1.0))
        
        # Top Navigation & Status Bar (Hidden on Connection Screen)
        self.top_bar = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height="56dp",
            md_bg_color=(0.11, 0.11, 0.15, 0.98),
            radius=[0, 0, 0, 0],
            line_color=(0.2, 0.25, 0.35, 0.2),
            line_width=1.0,
            padding=["16dp", 0],
            spacing="12dp"
        )
        
        # Back/Forward history buttons
        self.btn_back = MDIconButton(icon="arrow-left", theme_icon_color="Custom", icon_color=(0.7, 0.7, 0.7, 1.0), pos_hint={"center_y": 0.5})
        self.btn_back.bind(on_release=lambda x: self.go_back())
        
        self.btn_forward = MDIconButton(icon="arrow-right", theme_icon_color="Custom", icon_color=(0.7, 0.7, 0.7, 1.0), pos_hint={"center_y": 0.5})
        self.btn_forward.bind(on_release=lambda x: self.go_forward())
        
        self.top_bar.add_widget(self.btn_back)
        self.top_bar.add_widget(self.btn_forward)
        
        # Screen title
        self.lbl_screen_title = MDLabel(
            text="OPERATIONAL PANEL",
            font_style="Subtitle1",
            bold=True,
            pos_hint={"center_y": 0.5}
        )
        self.top_bar.add_widget(self.lbl_screen_title)
        
        # Link state notification indicator
        self.lbl_link_state = MDLabel(
            text="DISCONNECTED",
            font_style="Caption",
            halign="right",
            bold=True,
            pos_hint={"center_y": 0.5}
        )
        self.lbl_link_state.theme_text_color = "Custom"
        self.lbl_link_state.text_color = (0.9, 0.2, 0.2, 1.0)
        self.top_bar.add_widget(self.lbl_link_state)
        
        right_panel.add_widget(self.top_bar)
        
        # ScreenManager containing GCS screens
        self.screen_manager = ScreenManager(transition=NoTransition())
        self.screen_manager.add_widget(ConnectionScreen())
        self.screen_manager.add_widget(DashboardScreen())
        self.screen_manager.add_widget(FlightScreen())
        self.screen_manager.add_widget(SensorsScreen())
        self.screen_manager.add_widget(LogsScreen())
        self.screen_manager.add_widget(ParametersScreen())
        self.screen_manager.add_widget(SettingsScreen())
        
        # Bind screen manager change
        self.screen_manager.bind(current=self.on_screen_change)
        
        right_panel.add_widget(self.screen_manager)
        self.root_layout.add_widget(right_panel)
        
        # Hide layout elements on setup screen
        self.sidebar.size_hint_x = None
        self.sidebar.width = 0
        self.top_bar.size_hint_y = None
        self.top_bar.height = 0
        
        # Setup telemetry check loop
        Clock.schedule_interval(self.check_telemetry_staleness, 0.5)
        
        return self.root_layout

    def start_websocket(self):
        """Starts backend WS client link."""
        if self.ws_client:
            self.ws_client.stop()
            
        self.ws_client = WebSocketClient(
            uri="ws://127.0.0.1:8000/ws",
            on_message_cb=self.handle_websocket_event
        )
        self.ws_client.start()

    def handle_websocket_event(self, event_type: str, data: dict):
        if event_type == "connection_update":
            self.connected = data.get("connected", False)
            if not self.connected:
                self.is_stale = True
                self.lbl_link_state.text = "BACKEND DISCONNECTED"
                self.lbl_link_state.text_color = (0.9, 0.2, 0.2, 1.0)
                # Propagate stale states to screens
                self.propagate_telemetry_state(self.vehicle_state, is_stale=True)
            else:
                self.is_stale = False
                self.last_packet_time = time.time()
                self.lbl_link_state.text = "BACKEND CONNECTED"
                self.lbl_link_state.text_color = (0.2, 0.8, 0.3, 1.0)
                
        elif event_type == "telemetry_update":
            self.connected = True
            self.is_stale = False
            self.last_packet_time = time.time()
            self.vehicle_state = data
            
            # Show link telemetry refresh indicators
            self.lbl_link_state.text = "LINK HEALTHY | 10 Hz"
            self.lbl_link_state.text_color = (0.2, 0.8, 0.3, 1.0)
            
            # Send state updates to screens
            self.propagate_telemetry_state(data, is_stale=False)
            
        elif event_type == "log_update":
            # Propagate logs to logs screen
            logs_screen = self.screen_manager.get_screen("logs")
            logs_screen.add_log_item(
                level=data.get("level", "INFO"),
                message=data.get("message", ""),
                timestamp=data.get("timestamp", time.time())
            )
            
        elif event_type == "sensor_update":
            # Raw MAVLink packet tracing
            logs_screen = self.screen_manager.get_screen("logs")
            logs_screen.add_mavlink_packet(
                msg_type=data.get("type", "UNKNOWN"),
                payload_summary=data.get("payload_summary", ""),
                timestamp=data.get("timestamp", time.time())
            )

    def check_telemetry_staleness(self, dt):
        """Called every 500ms to monitor signal dropouts."""
        if not self.connected or self.last_packet_time <= 0:
            return
            
        elapsed = time.time() - self.last_packet_time
        if elapsed > 3.0:
            if not self.is_stale:
                self.is_stale = True
                # Log warning to front screen logs
                logs_screen = self.screen_manager.get_screen("logs")
                logs_screen.add_log_item("WARNING", f"Telemetry connection lost. Stream inactive for {elapsed:.1f} seconds.", time.time())
                
            # Update Link Status Label
            self.lbl_link_state.text = f"CONNECTION LOST ({int(elapsed)}s ago)"
            self.lbl_link_state.text_color = (0.9, 0.5, 0.1, 1.0) # Amber Warning
            
            # Feed stale trigger to screens
            self.propagate_telemetry_state(self.vehicle_state, is_stale=True)

    def propagate_telemetry_state(self, state: dict, is_stale: bool):
        for screen_name in ["dashboard", "flight", "sensors"]:
            screen = self.screen_manager.get_screen(screen_name)
            if hasattr(screen, "update_telemetry"):
                screen.update_telemetry(state, is_stale)

    def navigate_to(self, screen_name: str, keep_history: bool = True):
        # Prevent double navigation actions to same screen
        if self.screen_manager.current == screen_name:
            return
            
        # Handle Screen Manager switch
        self.screen_manager.current = screen_name
        
        # Manage stack
        if keep_history:
            # Drop forward history if we start a new path branch
            if self.history_idx < len(self.history) - 1:
                self.history = self.history[:self.history_idx + 1]
            self.history.append(screen_name)
            self.history_idx = len(self.history) - 1
            
        self.update_nav_buttons_ui()

    def go_back(self):
        if self.history_idx > 0:
            self.history_idx -= 1
            screen = self.history[self.history_idx]
            self.navigate_to(screen, keep_history=False)

    def go_forward(self):
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            screen = self.history[self.history_idx]
            self.navigate_to(screen, keep_history=False)

    def update_nav_buttons_ui(self):
        # Update Back & Forward visual limits
        self.btn_back.disabled = (self.history_idx <= 0)
        self.btn_forward.disabled = (self.history_idx >= len(self.history) - 1)
        
        # Highlight active navigation tab on sidebar
        curr = self.screen_manager.current
        for name, btn in self.nav_buttons.items():
            if name == curr:
                btn.text_color = (0.2, 0.8, 0.7, 1.0)
                btn.line_color = (0.2, 0.8, 0.7, 0.15)
                btn.icon_color = (0.2, 0.8, 0.7, 1.0)
            else:
                btn.text_color = (0.8, 0.8, 0.8, 0.9)
                btn.line_color = (0, 0, 0, 0)
                btn.icon_color = (0.2, 0.8, 0.7, 0.5)

    def on_screen_change(self, instance, screen_name):
        # Set top-bar title text
        title_map = {
            "connection": "CONNECTION SETTINGS",
            "dashboard": "OPERATIONAL FLIGHT DASHBOARD",
            "flight": "PRIMARY INSTRUMENT DECK",
            "sensors": "SENSOR INTEGRITY & FAULT ESTIMATION",
            "logs": "GCS EVENT CONSOLE & TRACER",
            "parameters": "AUTOPILOT EEPROM CALIBRATION",
            "settings": "STATION HARDWARE SETTINGS"
        }
        self.lbl_screen_title.text = title_map.get(screen_name, "CONTROL STATION")
        
        # Toggle sidebar & navbar visibility if we return to login
        if screen_name == "connection":
            self.sidebar.width = 0
            self.top_bar.height = 0
        else:
            self.sidebar.width = dp(200)
            self.top_bar.height = dp(56)

    def disconnect_link(self, *args):
        # Command backend to release port
        try:
            requests.post("http://127.0.0.1:8000/api/disconnect", timeout=2.0)
        except Exception:
            pass
            
        # Terminate WebSockets client
        if self.ws_client:
            self.ws_client.stop()
            self.ws_client = None
            
        # Reset state and switch to login
        self.connected = False
        self.is_stale = False
        self.last_packet_time = 0.0
        self.history = []
        self.history_idx = -1
        self.lbl_link_state.text = "DISCONNECTED"
        self.lbl_link_state.text_color = (0.9, 0.2, 0.2, 1.0)
        
        self.navigate_to("connection")

    def on_stop(self):
        # Cleanup on window close
        if self.ws_client:
            self.ws_client.stop()
        try:
            requests.post("http://127.0.0.1:8000/api/disconnect", timeout=1.0)
        except Exception:
            pass
        logger.info("Application shut down successfully.")

if __name__ == "__main__":
    GCSApp().run()
