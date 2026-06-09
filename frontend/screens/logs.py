import time
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDRectangleFlatButton
from kivy.metrics import dp

# Level style config
LEVEL_STYLES = {
    "INFO": {"color": (0.2, 0.8, 0.3, 1.0), "icon": "information"},
    "WARNING": {"color": (1.0, 0.75, 0.0, 1.0), "icon": "alert-circle"},
    "ERROR": {"color": (0.9, 0.3, 0.3, 1.0), "icon": "alert-octagon"},
    "CRITICAL": {"color": (0.9, 0.1, 0.1, 1.0), "icon": "skull-crossbones"}
}

class LogItem(MDBoxLayout):
    """Event log row component."""
    def __init__(self, level: str, message: str, timestamp: float, **kwargs):
        super(LogItem, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "40dp"
        
        style = LEVEL_STYLES.get(level, {"color": (0.5, 0.5, 0.5, 1.0), "icon": "text"})
        
        # Icon
        self.add_widget(MDIconButton(
            icon=style["icon"],
            theme_icon_color="Custom",
            icon_color=style["color"],
            size_hint_x=None,
            width="24dp",
            pos_hint={"center_y": 0.5}
        ))
        
        # Time string
        time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
        self.add_widget(MDLabel(
            text=f"[{time_str}]",
            theme_text_color="Hint",
            font_style="Caption",
            size_hint_x=None,
            width="60dp",
            pos_hint={"center_y": 0.5}
        ))
        
        # Message text
        self.add_widget(MDLabel(
            text=message,
            theme_text_color="Primary",
            font_style="Body2",
            pos_hint={"center_y": 0.5}
        ))

class MAVLinkPacketItem(MDBoxLayout):
    """Raw MAVLink packet row component."""
    def __init__(self, msg_type: str, payload: str, timestamp: float, **kwargs):
        super(MAVLinkPacketItem, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = "12dp"
        self.size_hint_y = None
        self.height = "36dp"
        
        # Time string
        time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
        self.add_widget(MDLabel(
            text=time_str,
            theme_text_color="Hint",
            font_style="Caption",
            size_hint_x=None,
            width="55dp",
            pos_hint={"center_y": 0.5}
        ))
        
        # Type
        self.add_widget(MDLabel(
            text=msg_type,
            theme_text_color="Custom",
            text_color=(0.2, 0.8, 0.7, 1.0), # Cyan
            font_style="Subtitle2",
            size_hint_x=None,
            width="140dp",
            pos_hint={"center_y": 0.5}
        ))
        
        # Payload Summary
        self.add_widget(MDLabel(
            text=payload,
            theme_text_color="Secondary",
            font_style="Caption",
            shorten=True,
            shorten_from="right",
            pos_hint={"center_y": 0.5}
        ))

class LogsScreen(Screen):
    def __init__(self, **kwargs):
        super(LogsScreen, self).__init__(**kwargs)
        self.name = "logs"
        
        self.all_logs = []
        self.current_filter = "ALL"
        self.search_query = ""
        
        # Main Layout
        main_layout = MDBoxLayout(orientation="vertical", padding="16dp", spacing="16dp")
        
        # Title
        title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="36dp")
        title_row.add_widget(MDLabel(
            text="GCS SYSTEM CONSOLE & MESSAGE STREAM",
            font_style="Button",
            theme_text_color="Hint"
        ))
        main_layout.add_widget(title_row)
        
        # Grid: Left Column (Event logs & Filters) | Right Column (Raw MAVLink stream)
        grid = MDGridLayout(cols=2, spacing="16dp", size_hint_y=1.0)
        
        # --- LEFT PANEL: Event Logger ---
        events_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="12dp",
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_x=0.5
        )
        events_card.add_widget(MDLabel(
            text="SYSTEM COMPONENT EVENT LOGS",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Filters Row (Search & Severity selection)
        filter_layout = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="100dp")
        
        self.txt_search = MDTextField(
            hint_text="Search logs...",
            icon_right="magnify",
            size_hint_y=None,
            height="40dp",
            helper_text_mode="on_focus",
            mode="round"
        )
        self.txt_search.bind(text=self.on_search_change)
        filter_layout.add_widget(self.txt_search)
        
        # Filter Buttons
        btn_box = MDBoxLayout(orientation="horizontal", spacing="4dp", size_hint_y=None, height="36dp")
        self.filter_buttons = {}
        for lvl in ["ALL", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            btn = MDRectangleFlatButton(
                text=lvl,
                font_size="10sp",
                size_hint_x=1.0,
                theme_text_color="Custom",
                text_color=(0.2, 0.8, 0.7, 1.0) if lvl == "ALL" else (0.7, 0.7, 0.7, 0.8),
                line_color=(0.2, 0.8, 0.7, 0.8) if lvl == "ALL" else (0.2, 0.25, 0.35, 0.4)
            )
            # Use extra variable mapping to prevent closure binding issues
            btn.bind(on_release=lambda x, l=lvl: self.set_filter(l))
            self.filter_buttons[lvl] = btn
            btn_box.add_widget(btn)
        filter_layout.add_widget(btn_box)
        events_card.add_widget(filter_layout)
        
        # Scrollable View for Logs List
        self.scroll_logs = ScrollView(size_hint_y=1.0)
        self.list_logs_layout = BoxLayout(orientation="vertical", spacing="4dp", size_hint_y=None)
        self.list_logs_layout.bind(minimum_height=self.list_logs_layout.setter('height'))
        self.scroll_logs.add_widget(self.list_logs_layout)
        events_card.add_widget(self.scroll_logs)
        
        grid.add_widget(events_card)
        
        # --- RIGHT PANEL: Raw MAVLink Viewer ---
        mav_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="12dp",
            md_bg_color=(0.12, 0.12, 0.16, 0.95),
            line_color=(0.2, 0.25, 0.35, 0.4),
            line_width=1.0,
            radius=[8, 8, 8, 8],
            size_hint_x=0.5
        )
        mav_card.add_widget(MDLabel(
            text="LIVE MAVLINK 2 PACKET TRACER",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height="20dp"
        ))
        
        # Scrollable View for MAVLink Packets
        self.scroll_packets = ScrollView(size_hint_y=1.0)
        self.list_packets_layout = BoxLayout(orientation="vertical", spacing="2dp", size_hint_y=None)
        self.list_packets_layout.bind(minimum_height=self.list_packets_layout.setter('height'))
        self.scroll_packets.add_widget(self.list_packets_layout)
        mav_card.add_widget(self.scroll_packets)
        
        grid.add_widget(mav_card)
        main_layout.add_widget(grid)
        self.add_widget(main_layout)

    def add_log_item(self, level: str, message: str, timestamp: float):
        """Called externally when a new system log is broadcast."""
        log_data = {"level": level, "message": message, "timestamp": timestamp}
        self.all_logs.append(log_data)
        if len(self.all_logs) > 300:
            self.all_logs.pop(0)
            
        self.refresh_logs_ui()

    def add_mavlink_packet(self, msg_type: str, payload_summary: str, timestamp: float):
        """Called externally when a raw MAVLink packet arrives."""
        # Create packet item
        item = MAVLinkPacketItem(msg_type=msg_type, payload=payload_summary, timestamp=timestamp)
        self.list_packets_layout.add_widget(item)
        
        # Cap child widgets count to maintain high scrolling performance
        if len(self.list_packets_layout.children) > 80:
            self.list_packets_layout.remove_widget(self.list_packets_layout.children[-1])
            
        # Automatically scroll to bottom if user is not browsing back
        # We scroll down after layout redraws
        # self.scroll_packets.scroll_y = 0

    def set_filter(self, filter_level):
        self.current_filter = filter_level
        
        # Reset highlight colors
        for lvl, btn in self.filter_buttons.items():
            if lvl == filter_level:
                btn.text_color = (0.2, 0.8, 0.7, 1.0)
                btn.line_color = (0.2, 0.8, 0.7, 0.8)
            else:
                btn.text_color = (0.7, 0.7, 0.7, 0.8)
                btn.line_color = (0.2, 0.25, 0.35, 0.4)
                
        self.refresh_logs_ui()

    def on_search_change(self, instance, text):
        self.search_query = text.lower()
        self.refresh_logs_ui()

    def refresh_logs_ui(self):
        # Clear existing logs widgets
        self.list_logs_layout.clear_widgets()
        
        # Filter and render
        for log in reversed(self.all_logs): # Latest logs at top or bottom? Reversed means latest on top
            # Check level filter
            if self.current_filter != "ALL" and log["level"] != self.current_filter:
                continue
            # Check search query
            if self.search_query and self.search_query not in log["message"].lower():
                continue
                
            item = LogItem(level=log["level"], message=log["message"], timestamp=log["timestamp"])
            self.list_logs_layout.add_widget(item)
