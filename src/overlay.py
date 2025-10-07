# Author: RD7
# Purpose: Generic overlay functionality
# Created: 2025-10-06

import numpy as np
from src.config import Config
from kivy.graphics.texture import Texture
from kivy.graphics import Fbo, ClearColor, ClearBuffers, Color, Ellipse, Rectangle
from kivy.utils import get_color_from_hex

_COLOR_MAP = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "white": "#FFFFFF",
    "black": "#000000"
}

class Overlay:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._layers = {
            "points" : self._draw_points
        }

    # handler function to route which draw function we need
    def draw(self, frame: Texture, instructions: dict | list[dict] | None = None) -> Texture:
         
        # any of the sub debug features will go to defaualt values
        # but only if the main show_debug flag is set to true
        # if the main show_debug flag is false, exit the routine
        if (
            not self.cfg.debug.show_debug
            or not frame
            or not instructions): 
            return frame

        # Loop through instructions
        # Accept a single dict or a list of dicts.
        for item in (instructions if isinstance(instructions, list) else [instructions]):

            # check in the debug config if we are supposed to debug this item
            if not getattr(self.cfg.debug,item.get("debug",""),False):
                continue
            
            # determine which function we'll call for each draw type
            fn = self._layers.get(item.get("draw"))
            if fn:
                frame = fn(frame,item)
        return frame


    def _draw_points(self, frame: Texture, overlay: dict) -> Texture:
        points = overlay.get("location")
        if points is None or len(points) == 0:
            return frame

        points = np.asarray(points, dtype=np.float32)
        color = _resolve_color(overlay.get("color"), self.cfg.overlay.pts_color)
        radius = float(overlay.get("size", self.cfg.overlay.pts_radius))

        height, width = frame.height, frame.width

        fbo = Fbo(size=(width, height))
        with fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            # draw the camera texture as the background
            Rectangle(
                texture=frame,
                pos=(0, 0),
                size=(width, height),
                tex_coords=frame.tex_coords,
            )
            # draw the points
            Color(*color)
            for x_norm, y_norm in points:
                x_px = x_norm * width
                y_px = (1.0 - y_norm) * height  # MediaPipe y=0 is top
                Ellipse(pos=(x_px - radius, y_px - radius), size=(2 * radius, 2 * radius))

        fbo.draw()
        tex = fbo.texture
        if tex is None:
            return frame
        
        result = tex.get_region(0, 0, tex.width, tex.height)

        coords = tex.tex_coords
        if coords[0] > coords[2]:
            result.flip_vertical()    

        return result

def _resolve_color(value: str | tuple | list, fallback) -> tuple[float, float, float, float]:
    if isinstance(value, str):
        # allow color names via _COLOR_MAP first, then assume it’s already a hex string
        hex_code = _COLOR_MAP.get(value.lower(), value)
        return get_color_from_hex(hex_code)
    if isinstance(value, (tuple, list)):
        # support RGB(A) in either 0–1 or 0–255 space
        if max(value) > 1.0:
            rgb = [c / 255.0 for c in value[:3]]
            alpha = value[3] / 255.0 if len(value) == 4 else 1.0
        else:
            rgb = list(value[:3])
            alpha = value[3] if len(value) == 4 else 1.0
        return (*rgb, alpha)
    # fall back to the configured default (already a hex string)
    return get_color_from_hex(fallback)
