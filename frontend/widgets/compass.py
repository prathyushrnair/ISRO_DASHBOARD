from kivy.uix.widget import Widget
from kivy.properties import NumericProperty
from kivy.graphics import (
    Canvas, PushMatrix, PopMatrix, Rotate, Translate, 
    Color, Ellipse, Line, Rectangle
)
from kivy.core.text import Label as CoreLabel
import math

class Compass(Widget):
    heading = NumericProperty(0.0) # Heading in degrees (0 - 360)

    def __init__(self, **kwargs):
        super(Compass, self).__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw, heading=self.redraw)
        # Pre-cache text textures for high performance redraw loops
        self._textures = {}
        self._init_textures()

    def _init_textures(self):
        # Cardinal directions
        cardinals = {
            "N": (1.0, 0.25, 0.25, 1.0), # Red North
            "E": (1.0, 1.0, 1.0, 0.9),
            "S": (1.0, 1.0, 1.0, 0.9),
            "W": (1.0, 1.0, 1.0, 0.9),
            "NE": (1.0, 1.0, 1.0, 0.6),
            "SE": (1.0, 1.0, 1.0, 0.6),
            "SW": (1.0, 1.0, 1.0, 0.6),
            "NW": (1.0, 1.0, 1.0, 0.6),
        }
        for label, color in cardinals.items():
            self._textures[label] = self._render_text(label, font_size=14, color=color)
            
        # Degree markers (every 30 degrees)
        for deg in range(0, 360, 30):
            if deg in [0, 90, 180, 270]:
                continue # covered by cardinals
            # Abbreviated notation (e.g. 3 = 30 deg, 12 = 120 deg)
            text = f"{deg // 10}"
            self._textures[text] = self._render_text(text, font_size=11, color=(1.0, 1.0, 1.0, 0.7))

    def _render_text(self, text: str, font_size: int, color: tuple):
        try:
            lbl = CoreLabel(text=text, font_size=font_size, color=color)
            lbl.refresh()
            return lbl.texture
        except Exception:
            return None

    def redraw(self, *args):
        self.canvas.clear()
        
        # Center coordinates and radius
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        radius = min(self.width, self.height) / 2.0 * 0.9
        
        if radius <= 0:
            return

        with self.canvas:
            # 1. Background ring / dial casing
            Color(0.12, 0.12, 0.16, 1.0)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2.0, radius * 2.0))
            
            # Draw outer silver ring
            Color(0.5, 0.5, 0.5, 0.8)
            Line(circle=(cx, cy, radius), width=2.0)
            Line(circle=(cx, cy, radius - 15.0), width=1.0)

            # 2. ROTATING DIAL CARD
            PushMatrix()
            Translate(cx, cy, 0)
            # Rotate card counter-clockwise by heading so 'N' points north
            Rotate(angle=self.heading, axis=(0, 0, 1))

            # Draw heading ticks every 5 degrees
            Color(1.0, 1.0, 1.0, 0.5)
            for deg in range(0, 360, 5):
                rad = math.radians(90 - deg)
                is_major = (deg % 30 == 0)
                is_medium = (deg % 10 == 0) and not is_major
                
                tick_len = 12.0 if is_major else (8.0 if is_medium else 4.0)
                w = 1.5 if is_major else 1.0
                
                x1 = (radius - 2.0) * math.cos(rad)
                y1 = (radius - 2.0) * math.sin(rad)
                x2 = (radius - 2.0 - tick_len) * math.cos(rad)
                y2 = (radius - 2.0 - tick_len) * math.sin(rad)
                Line(points=[x1, y1, x2, y2], width=w)

            # Draw Labels (North, East, South, West and subcardinals)
            labels_angle = {
                "N": 0, "NE": 45, "E": 90, "SE": 135,
                "S": 180, "SW": 225, "W": 270, "NW": 315
            }
            
            for text, angle in labels_angle.items():
                rad = math.radians(90 - angle)
                tx = (radius - 30.0) * math.cos(rad)
                ty = (radius - 30.0) * math.sin(rad)
                
                tex = self._textures.get(text)
                if tex:
                    # Draw text texture centered on coordinate
                    Color(1.0, 1.0, 1.0, 1.0)
                    Rectangle(
                        texture=tex,
                        pos=(tx - tex.width / 2.0, ty - tex.height / 2.0),
                        size=tex.size
                    )

            # Draw Numbers for Degrees (every 30 degrees)
            for deg in range(30, 360, 30):
                if deg in [90, 180, 270]:
                    continue
                rad = math.radians(90 - deg)
                tx = (radius - 45.0) * math.cos(rad)
                ty = (radius - 45.0) * math.sin(rad)
                
                text = f"{deg // 10}"
                tex = self._textures.get(text)
                if tex:
                    Color(1.0, 1.0, 1.0, 1.0)
                    Rectangle(
                        texture=tex,
                        pos=(tx - tex.width / 2.0, ty - tex.height / 2.0),
                        size=tex.size
                    )
            
            # Restore coordinate frame
            PopMatrix()

            # 3. STATIC OVERLAYS (Heading Index pointer at top)
            # Red triangle index marker at top center
            Color(1.0, 0.25, 0.25, 1.0)
            Line(points=[cx, cy + radius, cx - 8.0, cy + radius - 12.0, cx + 8.0, cy + radius - 12.0, cx, cy + radius], width=1.5)
            
            # Central Digital Heading Readout Casing
            Color(0.07, 0.07, 0.1, 0.9)
            Ellipse(pos=(cx - 28.0, cy - 28.0), size=(56.0, 56.0))
            Color(0.2, 0.8, 0.7, 0.8) # Cyan outline
            Line(circle=(cx, cy, 28.0), width=1.5)

            # Central Readout Text
            val_text = f"{int(self.heading):03}°"
            # Refresh a quick label on the fly
            lbl = CoreLabel(text=val_text, font_size=13, color=(0.2, 0.9, 0.8, 1.0))
            lbl.refresh()
            tex = lbl.texture
            if tex:
                Color(1.0, 1.0, 1.0, 1.0)
                Rectangle(
                    texture=tex,
                    pos=(cx - tex.width / 2.0, cy - tex.height / 2.0),
                    size=tex.size
                )
