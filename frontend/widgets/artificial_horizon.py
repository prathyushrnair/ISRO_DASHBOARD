from kivy.uix.widget import Widget
from kivy.properties import NumericProperty
from kivy.graphics import (
    Canvas, StencilPush, StencilUse, StencilPop, 
    PushMatrix, PopMatrix, Rotate, Translate, 
    Color, Ellipse, Line, Rectangle
)
import math

class ArtificialHorizon(Widget):
    roll = NumericProperty(0.0)   # Roll in degrees (positive right, negative left)
    pitch = NumericProperty(0.0)  # Pitch in degrees (positive up, negative down)

    def __init__(self, **kwargs):
        super(ArtificialHorizon, self).__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw, roll=self.redraw, pitch=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        
        # Determine center and radius of the instrument
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        radius = min(self.width, self.height) / 2.0 * 0.9
        
        if radius <= 0:
            return

        with self.canvas:
            # --- STENCIL SECTION: Clip all horizon movement to a circle ---
            StencilPush()
            # Draw the mask (a circle of radius)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
            StencilUse()

            # --- DYNAMIC HORIZON DRAWING (Rotates & Translates) ---
            PushMatrix()
            # Translate to center
            Translate(cx, cy, 0)
            # Rotate by negative roll (aerospace indicator style)
            Rotate(angle=-self.roll, axis=(0, 0, 1))
            
            # Translate by pitch. 1 degree = 2.5 pixels (scaled by size)
            scale_factor = radius / 30.0  # Show ~30 degrees max in view
            dy = self.pitch * scale_factor
            Translate(0, -dy, 0)
            
            # Draw sky (Light Blue)
            Color(0.2, 0.6, 0.85, 1.0) # Aerospace Blue
            Rectangle(pos=(-radius * 2.5, 0), size=(radius * 5.0, radius * 2.5))
            
            # Draw ground (Brown / Dark Teal)
            Color(0.4, 0.25, 0.15, 1.0) # Earth Brown
            Rectangle(pos=(-radius * 2.5, -radius * 2.5), size=(radius * 5.0, radius * 2.5))
            
            # Draw Horizon Line
            Color(1.0, 1.0, 1.0, 1.0)
            Line(points=[-radius * 2.0, 0, radius * 2.0, 0], width=2.0)
            
            # Pitch lines/ladder (+/- 5, 10, 15, 20 degrees)
            for deg in [-20, -15, -10, -5, 5, 10, 15, 20]:
                py = deg * scale_factor
                # Length of line
                length = radius * 0.4 if deg % 10 == 0 else radius * 0.2
                Line(points=[-length/2.0, py, length/2.0, py], width=1.5)
                # Draw short tick marks at ends
                Line(points=[-length/2.0, py, -length/2.0, py - (5 if deg > 0 else -5)], width=1.5)
                Line(points=[length/2.0, py, length/2.0, py - (5 if deg > 0 else -5)], width=1.5)
                
            PopMatrix()
            
            # End stencil masking
            StencilPop()

            # --- STATIC OVERLAY (Does not rotate or translate) ---
            # 1. Bezel Ring
            Color(0.12, 0.12, 0.16, 1.0) # Dark frame background
            # We draw a hollow ring by drawing outline
            Color(0.7, 0.7, 0.7, 0.8) # Gray bezel
            Line(circle=(cx, cy, radius), width=3.0)
            
            # 2. Roll Indicators (Ticks around top bezel)
            Color(1.0, 1.0, 1.0, 0.7)
            for angle in [-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60]:
                rad = math.radians(90 - angle)
                x1 = cx + (radius - 2) * math.cos(rad)
                y1 = cy + (radius - 2) * math.sin(rad)
                x2 = cx + (radius - 12) * math.cos(rad)
                y2 = cy + (radius - 12) * math.sin(rad)
                Line(points=[x1, y1, x2, y2], width=1.5 if angle % 30 == 0 else 1.0)

            # 3. Aircraft Reticle (Yellow Center Mark and Horizontal wings)
            Color(1.0, 0.75, 0.0, 1.0) # Premium Gold/Yellow
            # Center dot
            Ellipse(pos=(cx - 4.0, cy - 4.0), size=(8.0, 8.0))
            # Left wing
            Line(points=[cx - radius * 0.6, cy, cx - radius * 0.2, cy], width=2.5)
            Line(points=[cx - radius * 0.2, cy, cx - radius * 0.2, cy - 8.0], width=2.5)
            # Right wing
            Line(points=[cx + radius * 0.2, cy, cx + radius * 0.6, cy], width=2.5)
            Line(points=[cx + radius * 0.2, cy, cx + radius * 0.2, cy - 8.0], width=2.5)
