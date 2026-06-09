from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty, BooleanProperty, ColorProperty

class TelemetryCard(MDCard):
    title = StringProperty("")
    value = StringProperty("0.0")
    unit = StringProperty("")
    is_stale = BooleanProperty(False)
    accent_color = ColorProperty((0.2, 0.8, 0.7, 1.0)) # Custom Cyan/Teal accent

    def __init__(self, **kwargs):
        super(TelemetryCard, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = "16dp"
        self.spacing = "4dp"
        self.size_hint_y = None
        self.height = "100dp"
        
        # Style
        self.md_bg_color = (0.13, 0.13, 0.17, 0.95)
        self.line_color = (0.2, 0.25, 0.35, 0.4)
        self.line_width = 1.0
        self.radius = [6, 6, 6, 6]
        
        # Title Label
        self.lbl_title = MDLabel(
            text=self.title.upper(),
            theme_text_color="Hint",
            font_style="Overline",
            size_hint_y=0.25
        )
        self.add_widget(self.lbl_title)
        
        # Value & Unit Layout
        self.val_layout = MDBoxLayout(
            orientation="horizontal",
            spacing="4dp",
            size_hint_y=0.75
        )
        
        self.lbl_val = MDLabel(
            text=self.value,
            theme_text_color="Primary",
            font_style="H4",
            bold=True,
            size_hint_x=0.75
        )
        
        self.lbl_unit = MDLabel(
            text=self.unit,
            theme_text_color="Secondary",
            font_style="Subtitle2",
            pos_hint={"center_y": 0.45},
            size_hint_x=0.25
        )
        
        self.val_layout.add_widget(self.lbl_val)
        self.val_layout.add_widget(self.lbl_unit)
        self.add_widget(self.val_layout)
        
        # Bind properties to update UI
        self.bind(
            title=self._update_title,
            value=self._update_value,
            unit=self._update_unit,
            is_stale=self._update_stale
        )

    def _update_title(self, instance, val):
        self.lbl_title.text = val.upper()

    def _update_value(self, instance, val):
        self.lbl_val.text = val

    def _update_unit(self, instance, val):
        self.lbl_unit.text = val

    def _update_stale(self, instance, val):
        if val:
            self.lbl_val.theme_text_color = "Custom"
            self.lbl_val.text_color = (0.8, 0.7, 0.2, 0.8) # Amber
            self.lbl_title.text = f"{self.title.upper()} (STALE)"
            self.lbl_title.theme_text_color = "Custom"
            self.lbl_title.text_color = (0.8, 0.7, 0.2, 0.8)
            self.line_color = (0.8, 0.7, 0.2, 0.3)
        else:
            self.lbl_val.theme_text_color = "Primary"
            self.lbl_title.text = self.title.upper()
            self.lbl_title.theme_text_color = "Hint"
            self.line_color = (0.2, 0.25, 0.35, 0.4)
