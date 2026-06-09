import requests
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivy.metrics import dp
from kivy.clock import Clock

import logging
logger = logging.getLogger("ParametersScreen")

class ParameterRowCard(MDCard):
    """Component for displaying an individual ArduPilot parameter."""
    def __init__(self, name: str, value: str, data_type: str, description: str, **kwargs):
        super(ParameterRowCard, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.padding = "16dp"
        self.spacing = "16dp"
        self.size_hint_y = None
        self.height = "76dp"
        
        # Styles
        self.md_bg_color = (0.12, 0.12, 0.16, 0.95)
        self.line_color = (0.2, 0.25, 0.35, 0.4)
        self.line_width = 1.0
        self.radius = [6, 6, 6, 6]
        
        # Left Block: Name & Type
        left_box = MDBoxLayout(orientation="vertical", spacing="2dp", size_hint_x=0.3)
        self.lbl_name = MDLabel(text=name, font_style="Subtitle1", bold=True, theme_text_color="Primary")
        self.lbl_type = MDLabel(text=f"Type: {data_type}", font_style="Caption", theme_text_color="Hint")
        left_box.add_widget(self.lbl_name)
        left_box.add_widget(self.lbl_type)
        self.add_widget(left_box)
        
        # Middle Block: Description
        self.lbl_desc = MDLabel(
            text=description, 
            font_style="Body2", 
            theme_text_color="Secondary",
            size_hint_x=0.5,
            valign="center"
        )
        self.add_widget(self.lbl_desc)
        
        # Right Block: Value Display Badge
        val_box = MDBoxLayout(
            orientation="vertical", 
            size_hint_x=0.2,
            md_bg_color=(0.2, 0.8, 0.7, 0.1),
            line_color=(0.2, 0.8, 0.7, 0.4),
            line_width=1.0,
            radius=[4, 4, 4, 4],
            padding=["8dp", "4dp"]
        )
        self.lbl_value = MDLabel(
            text=value, 
            font_style="H6", 
            bold=True, 
            halign="center",
            valign="center",
            theme_text_color="Custom",
            text_color=(0.2, 0.8, 0.7, 1.0)
        )
        val_box.add_widget(self.lbl_value)
        self.add_widget(val_box)

class ParametersScreen(Screen):
    def __init__(self, **kwargs):
        super(ParametersScreen, self).__init__(**kwargs)
        self.name = "parameters"
        
        # Main layout
        main_layout = MDBoxLayout(orientation="vertical", padding="16dp", spacing="16dp")
        
        # Header Row
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="36dp")
        title_row.add_widget(MDLabel(
            text="VEHICLE CONFIGURATION PARAMETERS (READ-ONLY)",
            font_style="Button",
            theme_text_color="Hint"
        ))
        main_layout.add_widget(title_row)
        
        # Info notice
        notice = MDCard(
            orientation="horizontal",
            padding="12dp",
            md_bg_color=(0.11, 0.14, 0.17, 0.95),
            line_color=(0.2, 0.4, 0.6, 0.3),
            line_width=1.0,
            radius=[4, 4, 4, 4],
            size_hint_y=None,
            height="48dp"
        )
        notice.add_widget(MDLabel(
            text="Note: Parameter settings below are fetched directly from the Pixhawk non-volatile EEPROM and cannot be edited over telemetry links.",
            font_style="Caption",
            theme_text_color="Secondary",
            valign="center"
        ))
        main_layout.add_widget(notice)
        
        # Scroll area for parameter rows
        scroll = ScrollView(size_hint_y=1.0)
        self.list_layout = BoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)
        
        # Fetch data on entry
        self.bind(on_pre_enter=self.fetch_parameters)

    def fetch_parameters(self, *args):
        self.list_layout.clear_widgets()
        # Loading notice
        self.list_layout.add_widget(MDLabel(text="Fetching configuration parameters from backend...", font_style="Body2", halign="center"))
        
        # Run actual get request on a clock tick so GUI loads pre_enter
        Clock.schedule_once(self._do_fetch, 0.1)

    def _do_fetch(self, dt):
        try:
            res = requests.get("http://127.0.0.1:8000/api/parameters", timeout=2.0)
            if res.status_code == 200:
                self.list_layout.clear_widgets()
                params = res.json()
                for p in params:
                    row = ParameterRowCard(
                        name=p["name"],
                        value=str(p["value"]),
                        data_type=p["type"],
                        description=p["desc"]
                    )
                    self.list_layout.add_widget(row)
            else:
                self.show_error("Failed to fetch parameters from REST endpoint.")
        except Exception as e:
            logger.error(f"Error fetching parameters: {e}")
            self.show_error("Backend Offline. Cannot load parameters.")

    def show_error(self, message):
        self.list_layout.clear_widgets()
        self.list_layout.add_widget(MDLabel(
            text=message, 
            font_style="Body2", 
            halign="center", 
            theme_text_color="Custom",
            text_color=(0.9, 0.3, 0.3, 1.0)
        ))
