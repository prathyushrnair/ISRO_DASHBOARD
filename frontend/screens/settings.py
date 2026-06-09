from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.slider import MDSlider
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivy.metrics import dp
from kivy.app import App

import logging
logger = logging.getLogger("SettingsScreen")

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.name = "settings"
        
        # Main Layout
        main_layout = MDBoxLayout(orientation="vertical", padding="16dp", spacing="16dp")
        
        # Header Row
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="36dp")
        title_row.add_widget(MDLabel(
            text="APPLICATION & COMMUNICATION SETTINGS",
            font_style="Button",
            theme_text_color="Hint"
        ))
        main_layout.add_widget(title_row)
        
        # Grid Layout (Split Left & Right)
        grid = MDGridLayout(cols=2, spacing="16dp", size_hint_y=1.0)
        
        # --- LEFT PANEL: Comms & MAVLink Settings ---
        comms_card = MDCard(
            orientation="vertical",
            padding="20dp",
            spacing="16dp",
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_y=1.0
        )
        comms_card.add_widget(MDLabel(
            text="LINK CONFIGURATION",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Active Link Label
        self.lbl_active_link = MDLabel(
            text="Active COM Port: SIMULATOR (57600 baud)",
            font_style="Body2",
            theme_text_color="Secondary",
            size_hint_y=None,
            height="30dp"
        )
        comms_card.add_widget(self.lbl_active_link)
        
        # Toggle Heartbeat Monitoring
        hb_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="44dp")
        hb_row.add_widget(MDLabel(
            text="Heartbeat Watchdog Monitoring",
            font_style="Subtitle2"
        ))
        self.switch_hb = MDSwitch(
            pos_hint={"center_y": 0.5}
        )
        self.switch_hb.bind(active=self.on_hb_toggle)
        hb_row.add_widget(self.switch_hb)
        comms_card.add_widget(hb_row)
        
        # Stream Rate slider (1 Hz to 50 Hz)
        rate_box = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="80dp")
        rate_header = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="24dp")
        rate_header.add_widget(MDLabel(text="Telemetry Stream Rate", font_style="Subtitle2"))
        self.lbl_rate_val = MDLabel(text="10 Hz", font_style="Subtitle2", halign="right", theme_text_color="Custom", text_color=(0.2, 0.8, 0.7, 1.0))
        rate_header.add_widget(self.lbl_rate_val)
        rate_box.add_widget(rate_header)
        
        self.slider_rate = MDSlider(
            min=1,
            max=50,
            value=10,
            step=1,
            hint=True,
            color=(0.2, 0.8, 0.7, 1.0)
        )
        self.slider_rate.bind(value=self.on_rate_slider_change)
        rate_box.add_widget(self.slider_rate)
        comms_card.add_widget(rate_box)
        
        grid.add_widget(comms_card)
        
        # --- RIGHT PANEL: App & Theme Settings ---
        app_card = MDCard(
            orientation="vertical",
            padding="20dp",
            spacing="16dp",
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_y=1.0
        )
        app_card.add_widget(MDLabel(
            text="GCS GUI CONFIGURATION",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Theme Switch Row (Dark Theme)
        theme_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="44dp")
        theme_row.add_widget(MDLabel(
            text="Premium Dark Dashboard UI",
            font_style="Subtitle2"
        ))
        self.switch_theme = MDSwitch(
            pos_hint={"center_y": 0.5}
        )
        self.switch_theme.bind(active=self.on_theme_toggle)
        theme_row.add_widget(self.switch_theme)
        app_card.add_widget(theme_row)
        
        # Logging Preferences Row
        log_pref_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="44dp")
        log_pref_row.add_widget(MDLabel(
            text="Write Local Log Backup Files",
            font_style="Subtitle2"
        ))
        self.switch_logging = MDSwitch(
            pos_hint={"center_y": 0.5}
        )
        self.switch_logging.bind(active=self.on_logging_toggle)
        log_pref_row.add_widget(self.switch_logging)
        app_card.add_widget(log_pref_row)
        
        # Metadata / Version summary info
        meta_card = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="4dp",
            md_bg_color=(0.09, 0.09, 0.13, 0.9),
            radius=[4, 4, 4, 4],
            size_hint_y=None,
            height="100dp"
        )
        meta_card.add_widget(MDLabel(text="GROUND CONTROL TERMINAL SUMMARY", font_style="Overline", theme_text_color="Hint"))
        meta_card.add_widget(MDLabel(text="Firmware Compatibility: ArduCopter v4.x / MAVLink v2.0", font_style="Caption"))
        meta_card.add_widget(MDLabel(text="Software Version: PMGCS-1.0.0 Stable (Win64)", font_style="Caption"))
        meta_card.add_widget(MDLabel(text="FastAPI Backend Target: http://127.0.0.1:8000", font_style="Caption"))
        app_card.add_widget(meta_card)
        
        grid.add_widget(app_card)
        main_layout.add_widget(grid)
        self.add_widget(main_layout)

    def on_pre_enter(self):
        # Update link settings details from global state
        app = App.get_running_app()
        # Find connection screen selection parameters
        conn_screen = app.root.ids.screen_manager.get_screen("connection")
        self.lbl_active_link.text = f"Active COM Port: {conn_screen.selected_port} ({conn_screen.selected_baud} baud)"
        
        # Set switch states safely after widget rendering
        self.switch_hb.active = True
        self.switch_theme.active = True
        self.switch_logging.active = True

    def on_hb_toggle(self, instance, active):
        logger.info(f"Heartbeat monitoring set to: {active}")

    def on_rate_slider_change(self, instance, val):
        self.lbl_rate_val.text = f"{int(val)} Hz"
        logger.info(f"Requested telemetry stream rate: {int(val)} Hz")

    def on_theme_toggle(self, instance, active):
        app = App.get_running_app()
        if active:
            app.theme_cls.theme_style = "Dark"
        else:
            app.theme_cls.theme_style = "Light"
        logger.info(f"GUI theme preference style set to dark: {active}")

    def on_logging_toggle(self, instance, active):
        logger.info(f"Local backup log files generation set to: {active}")
