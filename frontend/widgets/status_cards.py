from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, OptionProperty, ColorProperty
from kivy.graphics import Color, Ellipse

# Define visual color constants matching high-tech aesthetic
COLOR_GREEN = (0.1, 0.8, 0.3, 1.0)
COLOR_YELLOW = (1.0, 0.75, 0.0, 1.0)
COLOR_RED = (0.9, 0.2, 0.2, 1.0)
COLOR_GRAY = (0.5, 0.5, 0.5, 1.0)

class HealthIndicatorItem(MDBoxLayout):
    sensor_name = StringProperty("")
    status = OptionProperty("Red", options=["Green", "Yellow", "Red", "Gray"])
    status_text = StringProperty("Critical")

    def __init__(self, **kwargs):
        super(HealthIndicatorItem, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "36dp"
        
        # Name label
        self.lbl_name = MDLabel(
            text=self.sensor_name,
            theme_text_color="Primary",
            font_style="Body2",
            size_hint_x=0.5
        )
        
        # Status text label
        self.lbl_status = MDLabel(
            text=self.status_text,
            theme_text_color="Secondary",
            font_style="Caption",
            halign="right",
            size_hint_x=0.3
        )
        
        # Dot indicator container
        self.dot_container = BoxLayout(
            size_hint_x=0.2,
            size_hint_y=None,
            height="16dp",
            pos_hint={"center_y": 0.5}
        )
        self.dot_container.bind(pos=self._draw_dot, size=self._draw_dot)
        
        self.add_widget(self.lbl_name)
        self.add_widget(self.lbl_status)
        self.add_widget(self.dot_container)
        
        self.bind(sensor_name=self._update_name, status=self._update_status)
        self.update_ui()

    def _update_name(self, instance, val):
        self.lbl_name.text = val

    def _update_status(self, instance, val):
        self.update_ui()

    def update_ui(self):
        if self.status == "Green":
            self.status_text = "Healthy"
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = COLOR_GREEN
        elif self.status == "Yellow":
            self.status_text = "Warning"
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = COLOR_YELLOW
        elif self.status == "Red":
            self.status_text = "Critical"
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = COLOR_RED
        else:
            self.status_text = "Stale"
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = COLOR_GRAY
            
        self.lbl_status.text = self.status_text
        self._draw_dot()

    def _draw_dot(self, *args):
        self.dot_container.canvas.clear()
        
        # Determine dot position and size
        width = self.dot_container.width
        height = self.dot_container.height
        side = min(width, height, 12.0)
        
        cx = self.dot_container.x + width - side - 8
        cy = self.dot_container.y + (height - side) / 2.0
        
        if self.status == "Green":
            color = COLOR_GREEN
        elif self.status == "Yellow":
            color = COLOR_YELLOW
        elif self.status == "Red":
            color = COLOR_RED
        else:
            color = COLOR_GRAY
            
        with self.dot_container.canvas:
            Color(*color)
            Ellipse(pos=(cx, cy), size=(side, side))

class SystemStatusCard(MDCard):
    def __init__(self, **kwargs):
        super(SystemStatusCard, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = "16dp"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "160dp"
        
        # Styled background matching darker palette
        self.md_bg_color = (0.15, 0.15, 0.2, 0.95)
        self.line_color = (0.2, 0.8, 0.7, 0.3)
        self.line_width = 1.0
        self.radius = [8, 8, 8, 8]
        
        # Title
        self.add_widget(MDLabel(
            text="SYSTEM CONTROL OVERVIEW",
            theme_text_color="Hint",
            font_style="Overline"
        ))
        
        # Connection Row
        row_conn = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="24dp")
        row_conn.add_widget(MDLabel(text="Telemetry Link:", font_style="Subtitle2"))
        self.lbl_conn = MDLabel(text="DISCONNECTED", font_style="Subtitle2", halign="right")
        self.lbl_conn.theme_text_color = "Custom"
        self.lbl_conn.text_color = COLOR_RED
        row_conn.add_widget(self.lbl_conn)
        self.add_widget(row_conn)
        
        # Armed Row
        row_arm = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="24dp")
        row_arm.add_widget(MDLabel(text="Vehicle Arm State:", font_style="Subtitle2"))
        self.lbl_arm = MDLabel(text="DISARMED", font_style="Subtitle2", halign="right")
        self.lbl_arm.theme_text_color = "Custom"
        self.lbl_arm.text_color = COLOR_GRAY
        row_arm.add_widget(self.lbl_arm)
        self.add_widget(row_arm)
        
        # Flight Mode Row
        row_mode = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="24dp")
        row_mode.add_widget(MDLabel(text="Active Flight Mode:", font_style="Subtitle2"))
        self.lbl_mode = MDLabel(text="UNKNOWN", font_style="Subtitle2", halign="right")
        self.lbl_mode.theme_text_color = "Custom"
        self.lbl_mode.text_color = COLOR_YELLOW
        row_mode.add_widget(self.lbl_mode)
        self.add_widget(row_mode)

    def update_state(self, connected: bool, armed: bool, mode: str, is_stale: bool = False):
        if is_stale:
            self.lbl_conn.text = "CONNECTION LOST"
            self.lbl_conn.text_color = COLOR_YELLOW
            self.lbl_arm.text_color = COLOR_GRAY
            self.lbl_mode.text_color = COLOR_GRAY
            return
            
        if connected:
            self.lbl_conn.text = "CONNECTED"
            self.lbl_conn.text_color = COLOR_GREEN
        else:
            self.lbl_conn.text = "DISCONNECTED"
            self.lbl_conn.text_color = COLOR_RED
            
        if armed:
            self.lbl_arm.text = "ARMED"
            self.lbl_arm.text_color = COLOR_RED
        else:
            self.lbl_arm.text = "DISARMED"
            self.lbl_arm.text_color = COLOR_GREEN
            
        self.lbl_mode.text = mode
        self.lbl_mode.text_color = (0.2, 0.8, 0.9, 1.0) # Cyan for modes
