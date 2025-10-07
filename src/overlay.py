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
    def draw(self, frame: Texture, overlays: dict = None) -> Texture:
        
        # any of the sub debug features will go to defaualt values
        # but only if the main show_debug flag is set to true
        # if the main show_debug flag is false, exit the routine
        if not self.cfg.debug.show_debug: return frame

        # return if overlays is empty
        if not overlays: return frame

         # Accept a single dict or a list of dicts.
        instructions = overlays if isinstance(overlays, list) else [overlays]

        for item in instructions:
            # for each instruction, grab which type of draw this will be
            # points, lines, regions, text, ....
            draw_type = item.get("draw")

            # within the debug config, there is an attribute to determine if
            # we will show this debug scheme
            draw_debug = item.get("debug")

            # only run the overlay draw function if the debug is on.
            if getattr(self.cfg.debug,draw_debug,False): 

                # determine which function we'll call for each draw type
                fn = self._layers.get(draw_type)

                if fn: 
                    # run the function for the given instruction
                    frame = fn(frame,item)

        return frame

    def _draw_points(self, frame: Texture, overlay) -> Texture:
        
        # grab the locations of the points
        points = overlay.get("location")
        if points is None or len(points) == 0:
            return frame
        points = np.asarray(points,dtype=np.float32)

        # grab instructions or defaults
        color = _resolve_color(overlay.get("color"), self.cfg.overlay.pts_color)
        radius = overlay.get("size",self.cfg.overlay.pts_radius)

        # grab frame dimensions
        h,w = frame.height, frame.width

        fbo = Fbo(size=(w,h))
        with fbo:
            ClearColor(0,0,0,0)
            ClearBuffers()
            Rectangle(
                texture=frame, 
                pos=(0,0),
                size=(w,h),
                tex_coords=frame.tex_coords)
            Color(*color)
            for x,y in points:
                
                # scale normalized x by w to get pixel location
                px = x * w
                
                # scale normalized y by h to get pixel location.
                # beware that MediaPipe y=0 is top but kivy y=0 is bottom
                py = (1.0 - y) * h

                # draw the circle
                Ellipse(pos=(px-radius,py-radius),
                        size=(2*radius,2*radius))

        # draw on the texture
        fbo.draw()
        texture = fbo.texture
        if texture is None:
            return frame

        # make a copy so we don’t mutate the shared texture in place
        result = texture.get_region(0, 0, texture.width, texture.height)
        # result.flip_vertical()
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
