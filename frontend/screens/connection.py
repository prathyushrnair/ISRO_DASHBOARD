import requests
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDRoundFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu import MDDropdownMenu
from kivy.metrics import dp
from kivy.clock import Clock
import logging

logger = logging.getLogger("ConnectionScreen")

class ConnectionScreen(Screen):
    def __init__(self, **kwargs):
        super(ConnectionScreen, self).__init__(**kwargs)
        self.name = "connection"
        self.ports = ["SIMULATOR"]
        self.selected_port = "SIMULATOR"
        self.selected_baud = "57600"
        
        # Build UI layout
        main_layout = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="20dp",
            md_bg_color=(0.08, 0.08, 0.12, 1.0) # Sleek Dark Space color
        )
        
        # Center card container
        card = MDCard(
            orientation="vertical",
            padding="32dp",
            spacing="20dp",
            size_hint=(None, None),
            size=(dp(420), dp(480)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            radius=[12, 12, 12, 12],
            line_color=(0.2, 0.8, 0.7, 0.2),
            line_width=1.5
        )
        
        # Logo/Icon and Title
        header = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="100dp")
        logo_icon = MDIconButton(
            icon="radar",
            icon_size="48dp",
            theme_icon_color="Custom",
            icon_color=(0.2, 0.8, 0.7, 1.0),
            pos_hint={"center_x": 0.5}
        )
        title = MDLabel(
            text="PIXHAWK GROUND STATION",
            font_style="H6",
            halign="center",
            bold=True,
            theme_text_color="Primary"
        )
        subtitle = MDLabel(
            text="SiK Telemetry Radio Terminal Link",
            font_style="Caption",
            halign="center",
            theme_text_color="Secondary"
        )
        header.add_widget(logo_icon)
        header.add_widget(title)
        header.add_widget(subtitle)
        card.add_widget(header)
        
        # Fields Selection Layout
        fields_layout = MDBoxLayout(orientation="vertical", spacing="16dp", size_hint_y=None, height="180dp")
        
        # Port Selection Row
        row_port = MDBoxLayout(orientation="horizontal", spacing="12dp", size_hint_y=None, height="48dp")
        lbl_port_tag = MDLabel(
            text="COM Port:",
            font_style="Subtitle2",
            size_hint_x=0.35,
            pos_hint={"center_y": 0.5}
        )
        self.btn_port = MDRoundFlatButton(
            text=self.selected_port,
            size_hint_x=0.5,
            pos_hint={"center_y": 0.5},
            theme_text_color="Custom",
            text_color=(0.2, 0.8, 0.7, 1.0),
            line_color=(0.2, 0.8, 0.7, 0.5)
        )
        self.btn_port.bind(on_release=self.open_port_menu)
        
        btn_refresh = MDIconButton(
            icon="refresh",
            pos_hint={"center_y": 0.5},
            theme_icon_color="Custom",
            icon_color=(0.2, 0.8, 0.7, 1.0)
        )
        btn_refresh.bind(on_release=self.refresh_ports)
        
        row_port.add_widget(lbl_port_tag)
        row_port.add_widget(self.btn_port)
        row_port.add_widget(btn_refresh)
        fields_layout.add_widget(row_port)
        
        # Baud Rate Selection Row
        row_baud = MDBoxLayout(orientation="horizontal", spacing="12dp", size_hint_y=None, height="48dp")
        lbl_baud_tag = MDLabel(
            text="Baud Rate:",
            font_style="Subtitle2",
            size_hint_x=0.35,
            pos_hint={"center_y": 0.5}
        )
        self.btn_baud = MDRoundFlatButton(
            text=self.selected_baud,
            size_hint_x=0.5,
            pos_hint={"center_y": 0.5},
            theme_text_color="Custom",
            text_color=(0.2, 0.8, 0.7, 1.0),
            line_color=(0.2, 0.8, 0.7, 0.5)
        )
        self.btn_baud.bind(on_release=self.open_baud_menu)
        
        # Dummy filler to align with the port row which has an extra refresh button
        spacer = MDBoxLayout(size_hint_x=0.15)
        row_baud.add_widget(lbl_baud_tag)
        row_baud.add_widget(self.btn_baud)
        row_baud.add_widget(spacer)
        fields_layout.add_widget(row_baud)
        
        card.add_widget(fields_layout)
        
        # Connect Actions Layout
        actions_layout = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="100dp")
        self.btn_connect = MDRaisedButton(
            text="CONNECT LINK",
            size_hint_x=1.0,
            pos_hint={"center_x": 0.5},
            md_bg_color=(0.2, 0.8, 0.7, 1.0),
            theme_text_color="Custom",
            text_color=(0.08, 0.08, 0.12, 1.0)
        )
        self.btn_connect.bind(on_release=self.attempt_connect)
        
        self.lbl_status = MDLabel(
            text="Offline. Select parameters to connect.",
            font_style="Caption",
            halign="center",
            theme_text_color="Secondary"
        )
        
        actions_layout.add_widget(self.btn_connect)
        actions_layout.add_widget(self.lbl_status)
        card.add_widget(actions_layout)
        
        main_layout.add_widget(card)
        self.add_widget(main_layout)
        
        # Initialize dropdown menus
        self.port_menu = None
        self.baud_menu = None
        
        # Do a delayed initial ports scan
        Clock.schedule_once(lambda dt: self.refresh_ports(), 0.5)

    def refresh_ports(self, *args):
        self.lbl_status.text = "Scanning ports..."
        self.lbl_status.theme_text_color = "Secondary"
        try:
            # Query FastAPI Backend
            res = requests.get("http://127.0.0.1:8000/api/ports", timeout=1.5)
            if res.status_code == 200:
                self.ports = res.json()
                if not self.ports:
                    self.ports = ["SIMULATOR"]
                self.lbl_status.text = f"Found {len(self.ports)} device ports."
            else:
                self.ports = ["SIMULATOR"]
                self.lbl_status.text = "Backend error. Fallback to simulator."
        except requests.exceptions.ConnectionError:
            self.ports = ["SIMULATOR"]
            self.lbl_status.text = "Backend Offline. Run FastAPI backend server first."
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = (0.9, 0.3, 0.3, 1.0)
            
        # Select first available if current selection is gone
        if self.selected_port not in self.ports:
            self.selected_port = self.ports[0]
            self.btn_port.text = self.selected_port
            
        self._build_port_menu()

    def _build_port_menu(self):
        menu_items = [
            {
                "text": port,
                "viewclass": "OneLineListItem",
                "height": dp(48),
                "on_release": lambda x=port: self.set_port(x),
            } for port in self.ports
        ]
        self.port_menu = MDDropdownMenu(
            caller=self.btn_port,
            items=menu_items,
            width_mult=4,
        )

    def open_port_menu(self, instance):
        if not self.port_menu:
            self._build_port_menu()
        self.port_menu.open()

    def set_port(self, port_name):
        self.selected_port = port_name
        self.btn_port.text = port_name
        if self.port_menu:
            self.port_menu.dismiss()

    def open_baud_menu(self, instance):
        bauds = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
        menu_items = [
            {
                "text": baud,
                "viewclass": "OneLineListItem",
                "height": dp(48),
                "on_release": lambda x=baud: self.set_baud(x),
            } for baud in bauds
        ]
        self.baud_menu = MDDropdownMenu(
            caller=self.btn_baud,
            items=menu_items,
            width_mult=4,
        )
        self.baud_menu.open()

    def set_baud(self, baud_val):
        self.selected_baud = baud_val
        self.btn_baud.text = baud_val
        if self.baud_menu:
            self.baud_menu.dismiss()

    def attempt_connect(self, instance):
        self.lbl_status.text = f"Opening link on {self.selected_port}..."
        self.lbl_status.theme_text_color = "Secondary"
        self.btn_connect.disabled = True
        
        # Run request on a minor delay so UI thread updates label first
        Clock.schedule_once(self._send_connect_request, 0.1)

    def _send_connect_request(self, dt):
        try:
            payload = {"port": self.selected_port, "baud": int(self.selected_baud)}
            res = requests.post("http://127.0.0.1:8000/api/connect", json=payload, timeout=5.0)
            
            if res.status_code == 200:
                self.lbl_status.text = "Connection Successful! Starting streams..."
                self.lbl_status.theme_text_color = "Custom"
                self.lbl_status.text_color = (0.2, 0.8, 0.3, 1.0)
                
                # Setup websocket and navigate to dashboard after short delay
                Clock.schedule_once(self._transition_to_dashboard, 1.0)
            else:
                error_detail = res.json().get("detail", "Unknown error")
                self.lbl_status.text = f"Failed: {error_detail}"
                self.lbl_status.theme_text_color = "Custom"
                self.lbl_status.text_color = (0.9, 0.3, 0.3, 1.0)
                self.btn_connect.disabled = False
        except requests.exceptions.ConnectionError:
            self.lbl_status.text = "Connection Error: FastAPI Backend server offline."
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = (0.9, 0.3, 0.3, 1.0)
            self.btn_connect.disabled = False
        except Exception as e:
            self.lbl_status.text = f"Error: {str(e)}"
            self.lbl_status.theme_text_color = "Custom"
            self.lbl_status.text_color = (0.9, 0.3, 0.3, 1.0)
            self.btn_connect.disabled = False

    def _transition_to_dashboard(self, dt):
        self.btn_connect.disabled = False
        
        # Start the global WebSocket Client on App
        from kivy.app import App
        app = App.get_running_app()
        app.start_websocket()
        
        # Navigate
        app.navigate_to("dashboard")
