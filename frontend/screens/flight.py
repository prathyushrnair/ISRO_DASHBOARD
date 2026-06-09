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

from frontend.widgets.artificial_horizon import ArtificialHorizon
from frontend.widgets.compass import Compass
from frontend.widgets.telemetry_cards import TelemetryCard

import logging
logger = logging.getLogger("FlightScreen")

class FlightScreen(Screen):
    def __init__(self, **kwargs):
        super(FlightScreen, self).__init__(**kwargs)
        self.name = "flight"
        self.dialog = None
        self.pending_mode = ""
        
        # Main Layout
        main_layout = MDBoxLayout(orientation="vertical", padding="16dp", spacing="16dp")
        
        # Page Title Row
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="36dp")
        title_row.add_widget(MDLabel(
            text="FLIGHT DECK PANEL",
            font_style="Button",
            theme_text_color="Hint"
        ))
        main_layout.add_widget(title_row)
        
        # Grid layout: Left is Primary Flight Instrumentation | Right is Telemetry Data and Mode Controller
        grid = MDGridLayout(cols=2, spacing="16dp", size_hint_y=1.0)
        
        # --- LEFT PANEL: Primary Instruments ---
        inst_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="16dp",
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_x=0.55
        )
        inst_card.add_widget(MDLabel(
            text="PRIMARY FLIGHT DISPLAY (PFD)",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Box containing horizon and compass side-by-side
        gauges_box = MDBoxLayout(orientation="horizontal", spacing="16dp", size_hint_y=1.0)
        
        # Artificial Horizon Panel
        horizon_wrapper = MDBoxLayout(orientation="vertical", spacing="8dp")
        self.horizon_widget = ArtificialHorizon(size_hint=(1.0, 1.0))
        horizon_wrapper.add_widget(self.horizon_widget)
        horizon_wrapper.add_widget(MDLabel(text="Attitude Indicator", halign="center", font_style="Caption", theme_text_color="Secondary", size_hint_y=None, height="20dp"))
        
        # Compass Panel
        compass_wrapper = MDBoxLayout(orientation="vertical", spacing="8dp")
        self.compass_widget = Compass(size_hint=(1.0, 1.0))
        compass_wrapper.add_widget(self.compass_widget)
        compass_wrapper.add_widget(MDLabel(text="Compass Rose", halign="center", font_style="Caption", theme_text_color="Secondary", size_hint_y=None, height="20dp"))
        
        gauges_box.add_widget(horizon_wrapper)
        gauges_box.add_widget(compass_wrapper)
        inst_card.add_widget(gauges_box)
        grid.add_widget(inst_card)
        
        # --- RIGHT PANEL: Telemetry Display & Mode Select ---
        right_panel = MDBoxLayout(orientation="vertical", spacing="16dp", size_hint_x=0.45)
        
        # 1. Telemetry Panels
        telemetry_grid = MDGridLayout(cols=2, spacing="12dp", size_hint_y=None, height="280dp")
        self.card_rel_alt = TelemetryCard(title="Relative Altitude", unit="m")
        self.card_abs_alt = TelemetryCard(title="Absolute Altitude", unit="m")
        self.card_speed = TelemetryCard(title="Ground Speed", unit="m/s")
        self.card_climb = TelemetryCard(title="Vertical Speed", unit="m/s")
        self.card_dist = TelemetryCard(title="Distance Home", unit="m")
        self.card_mode = TelemetryCard(title="Active Mode", value="STABILIZE", unit="")
        
        telemetry_grid.add_widget(self.card_rel_alt)
        telemetry_grid.add_widget(self.card_abs_alt)
        telemetry_grid.add_widget(self.card_speed)
        telemetry_grid.add_widget(self.card_climb)
        telemetry_grid.add_widget(self.card_dist)
        telemetry_grid.add_widget(self.card_mode)
        right_panel.add_widget(telemetry_grid)
        
        # 2. Flight Mode Selector Card
        mode_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="10dp",
            md_bg_color=(0.13, 0.13, 0.17, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_y=1.0
        )
        mode_card.add_widget(MDLabel(
            text="CHANGE AUTOPILOT FLIGHT MODE",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Mode Selection Grid (7 Modes)
        mode_grid = MDGridLayout(cols=3, spacing="8dp", size_hint_y=1.0)
        
        self.mode_buttons = {}
        supported_modes = ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "AUTO", "RTL", "LAND"]
        
        for mode in supported_modes:
            # Map button standard text
            btn = MDRectangleFlatButton(
                text=mode.replace("_", " "),
                theme_text_color="Custom",
                text_color=(0.2, 0.8, 0.7, 1.0),
                line_color=(0.2, 0.8, 0.7, 0.4),
                size_hint=(1.0, 1.0)
            )
            # Bind using custom mode variable
            btn.bind(on_release=lambda x, m=mode: self.confirm_mode_change(m))
            self.mode_buttons[mode] = btn
            mode_grid.add_widget(btn)
            
        mode_card.add_widget(mode_grid)
        right_panel.add_widget(mode_card)
        grid.add_widget(right_panel)
        
        main_layout.add_widget(grid)
        self.add_widget(main_layout)

    def update_telemetry(self, state: dict, is_stale: bool = False):
        # Update custom attitude gauges
        if is_stale:
            # Keep values, just make them look static or don't animate updates
            self.card_rel_alt.is_stale = True
            self.card_abs_alt.is_stale = True
            self.card_speed.is_stale = True
            self.card_climb.is_stale = True
            self.card_dist.is_stale = True
            self.card_mode.is_stale = True
        else:
            self.horizon_widget.roll = state.get("roll", 0.0)
            self.horizon_widget.pitch = state.get("pitch", 0.0)
            self.compass_widget.heading = state.get("heading", 0.0)
            
            # Update telemetry cards
            self.card_rel_alt.is_stale = False
            self.card_abs_alt.is_stale = False
            self.card_speed.is_stale = False
            self.card_climb.is_stale = False
            self.card_dist.is_stale = False
            self.card_mode.is_stale = False
            
            self.card_rel_alt.value = f"{state.get('relative_altitude', 0.0):.2f}"
            self.card_abs_alt.value = f"{state.get('altitude', 0.0):.2f}"
            self.card_speed.value = f"{state.get('ground_speed', 0.0):.2f}"
            self.card_climb.value = f"{state.get('vertical_speed', 0.0):.2f}"
            self.card_dist.value = f"{state.get('distance_from_home', 0.0):.1f}"
            
            active_mode = state.get("mode", "UNKNOWN")
            self.card_mode.value = active_mode
            
            # Highlight active mode button and dim others
            for mode, btn in self.mode_buttons.items():
                if mode == active_mode:
                    btn.md_bg_color = (0.2, 0.8, 0.7, 0.15)
                    btn.line_color = (0.2, 0.8, 0.7, 0.8)
                else:
                    btn.md_bg_color = (0, 0, 0, 0)
                    btn.line_color = (0.2, 0.8, 0.7, 0.3)

    def confirm_mode_change(self, target_mode):
        self.pending_mode = target_mode
        self.dialog = MDDialog(
            title="CONFIRM FLIGHT MODE CHANGE",
            text=f"Are you sure you want to command the Pixhawk autopilot to switch to {target_mode} mode?",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self.dismiss_dialog
                ),
                MDRaisedButton(
                    text="CHANGE MODE",
                    md_bg_color=(0.2, 0.8, 0.7, 1.0),
                    theme_text_color="Custom",
                    text_color=(0.08, 0.08, 0.12, 1.0),
                    on_release=self.change_mode_confirmed
                )
            ]
        )
        self.dialog.open()

    def change_mode_confirmed(self, *args):
        self.dismiss_dialog()
        try:
            payload = {"mode": self.pending_mode}
            res = requests.post("http://127.0.0.1:8000/api/command/mode", json=payload, timeout=2.0)
            if res.status_code != 200:
                logger.error(f"Mode change to {self.pending_mode} failed: {res.text}")
        except Exception as e:
            logger.error(f"Connection error requesting mode change: {e}")

    def dismiss_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
