# Author: RD7
# Purpose: Generic overlay functionality
# Created: 2025-10-06

import numpy as np
from services.config import Config
from services.midline import Line2D
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Ellipse, InstructionGroup, Line
from kivy.utils import get_color_from_hex
from typing import Optional, Tuple

_COLOR_MAP = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "white": "#FFFFFF",
    "black": "#000000"
}

class Overlay:
    def __init__(self, cfg: Config, preview_widget = None):
        self.cfg = cfg
        self.preview = preview_widget
        self._canvas = preview_widget.canvas.after if preview_widget  else None
        self._layers = {
            "points"    : self._draw_points,
            "line"      : self._draw_line
        }

        # cached instructions for the points layer
        self._point_group:      InstructionGroup | None = None
        self._point_color:      Color | None = None
        self._point_ellipses:   list[Ellipse] = []

        # cached instructions for the lines layer
        self._line_group:       InstructionGroup | None = None
        self._line_color:       Color | None = None
        self._line_segments:    list[Line] = []


    # handler function to route which draw function we need
    def draw(self, frame: Texture, instructions: dict | list[dict] | None = None) -> Texture:
         
        # any of the sub debug features will go to defaualt values
        # but only if the main show_debug flag is set to true
        # if the main show_debug flag is false, exit the routine
        if (
            not self.cfg.debug.show_debug
            or not frame
            or not instructions
        ): 
            self._clear_points()
            return frame

        rendered = False

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
                rendered = True

        if not rendered:
            self._clear_points()
            self._clear_lines()

        return frame


    def _draw_points(self, frame: Texture, overlay: dict) -> Texture:
        points = overlay.get("location")
        if (
            points is None 
            or len(points) == 0
            or not self.preview
        ):
            self._clear_points()
            return frame

        points = np.asarray(points, dtype=np.float32)
        color = _resolve_color(overlay.get("color"), self.cfg.overlay.pts_color)
        base_radius = float(overlay.get("size", self.cfg.overlay.pts_radius))

        widget_h, widget_w = self.preview.height, self.preview.width
        tex_h, tex_w = frame.height, frame.width

        if (
            widget_w == 0 
            or widget_h == 0
            or tex_w == 0
            or tex_h == 0
        ):
            self._clear_points()
            return frame

        scale = min(widget_w / tex_w, widget_h / tex_h) 
        display_w = tex_w * scale
        display_h = tex_h * scale
        offset_x = (widget_w - display_w) / 2.0
        offset_y = (widget_h - display_h) / 2.0
        radius = max(1.0, base_radius * scale)
        diameter = radius * 2.0

        self._ensure_point_primitives(len(points),color)

        for idx, (x_norm,y_norm) in enumerate(points):
            ell = self._point_ellipses[idx]
            x_px = offset_x + x_norm * display_w
            y_px = offset_y + (1.0 - y_norm) * display_h
            ell.pos = (x_px - radius, y_px - radius)
            ell.size = (diameter,diameter)

        for idx in range(len(points), len(self._point_ellipses)):
            self._point_ellipses[idx].size = (0, 0)

        return frame
    
    def _draw_line(self, frame: Texture, overlay: dict) -> Texture:
        line: Line2D | None = overlay.get("line")
        if line is None or not self.preview:
            self._clear_lines()
            return frame

        color = _resolve_color(overlay.get("color"), self.cfg.overlay.midline_color)
        width = float(overlay.get("width", self.cfg.overlay.midline_width))

        widget_h, widget_w = self.preview.height, self.preview.width
        tex_h, tex_w = frame.height, frame.width
        if widget_w == 0 or widget_h == 0 or tex_w == 0 or tex_h == 0:
            self._clear_lines()
            return frame

        segment = self._line_segment_in_unit_square(line)
        if segment is None:
            self._clear_lines()
            return frame

        # scale to displayed size (same logic as points)
        scale = min(widget_w / tex_w, widget_h / tex_h)
        display_w = tex_w * scale
        display_h = tex_h * scale
        offset_x = (widget_w - display_w) / 2.0
        offset_y = (widget_h - display_h) / 2.0

        (x1, y1_norm), (x2, y2_norm) = segment
        x1_px = offset_x + x1 * display_w
        y1_px = offset_y + (1.0 - y1_norm) * display_h
        x2_px = offset_x + x2 * display_w
        y2_px = offset_y + (1.0 - y2_norm) * display_h

        self._ensure_line_primitives(color, width)
        if self._line_segments:
            seg = self._line_segments[0]
            seg.points = [x1_px, y1_px, x2_px, y2_px]
            seg.width = width

        return frame


    def _ensure_point_primitives(self, count: int, color: tuple[float, float, float, float]) -> None:
        if self._canvas is None and self.preview:
            self._canvas = self.preview.canvas.after
        if self._canvas is None:
            return

        if self._point_group is None:
            self._point_group = InstructionGroup()
            self._point_color = Color(*color)
            self._point_group.add(self._point_color)
            self._canvas.add(self._point_group)
        elif self._point_color:
            self._point_color.rgba = color

        while len(self._point_ellipses) < count:
            ell = Ellipse(size=(0, 0))
            self._point_group.add(ell)
            self._point_ellipses.append(ell)

    def _clear_points(self) -> None:
        if self._point_color:
            r, g, b, _ = self._point_color.rgba
            self._point_color.rgba = (r, g, b, 0)
        for ell in self._point_ellipses:
            ell.size = (0, 0)

    def _ensure_line_primitives(self, color, width):
        if self._canvas is None and self.preview:
            self._canvas = self.preview.canvas.after
        if self._canvas is None:
            return

        if self._line_group is None:
            self._line_group = InstructionGroup()
            self._line_color = Color(*color)
            self._line_group.add(self._line_color)
            line_instr = Line(points=[0, 0, 0, 0], width=width, cap='round')
            self._line_group.add(line_instr)
            self._canvas.add(self._line_group)
            self._line_segments = [line_instr]
        else:
            if self._line_color:
                self._line_color.rgba = color
            if self._line_segments:
                self._line_segments[0].width = width

    def _clear_lines(self):
        if self._line_color:
            r, g, b, _ = self._line_color.rgba
            self._line_color.rgba = (r, g, b, 0)
        for seg in self._line_segments:
            seg.points = [0, 0, 0, 0]


    def _line_segment_in_unit_square(
        self, line: Line2D
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return the two intersection points of `line` with the unit square, ordered by increasing projection along the line direction."""
        ox, oy = line.origin
        dx, dy = line.direction
        candidates = []

        if not np.isclose(dx, 0.0):
            for x in (0.0, 1.0):
                t = (x - ox) / dx
                y = oy + t * dy
                if 0.0 <= y <= 1.0:
                    candidates.append((x, y))

        if not np.isclose(dy, 0.0):
            for y in (0.0, 1.0):
                t = (y - oy) / dy
                x = ox + t * dx
                if 0.0 <= x <= 1.0:
                    candidates.append((x, y))

        if len(candidates) < 2:
            return None

        pts = np.unique(np.asarray(candidates, dtype=np.float32), axis=0)
        if pts.shape[0] < 2:
            return None

        origin = line.origin
        direction = line.direction
        projections = np.dot(pts - origin, direction)

        i_min = int(np.argmin(projections))
        i_max = int(np.argmax(projections))
        return pts[i_min], pts[i_max]

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
