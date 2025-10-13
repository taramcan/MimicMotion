# Author: RD7
# Purpose: Generic overlay functionality
# Created: 2025-10-06

from __future__ import annotations

import numpy as np
from typing import Optional, Sequence, Tuple

from services.config import Config
from services.midline import Line2D

from kivy.graphics import Color, Ellipse, InstructionGroup, Line
from kivy.graphics.texture import Texture
from kivy.utils import get_color_from_hex

_COLOR_MAP = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "white": "#FFFFFF",
    "black": "#000000",
}


class Overlay:
    """Render landmark-based overlays on top of the preview widget."""

    def __init__(self, cfg: Config, preview_widget=None):
        self.cfg = cfg
        self.preview = preview_widget
        self._canvas = preview_widget.canvas.after if preview_widget else None

        self._layers = {
            "points": self._draw_points,
            "line": self._draw_line,
            "polygon": self._draw_polygon,
            "segment": self._draw_segment,
        }

        # Points (multiple layers keyed by debug/group)
        self._point_layers: dict[str, dict[str, object]] = {}

        # Lines (color/segment pairs per slot)
        self._line_group: InstructionGroup | None = None
        self._line_colors: list[Color] = []
        self._line_segments: list[Line] = []
        self._line_slots_used: set[int] = set()

        # Finite segments (displacement vectors)
        self._segment_group: InstructionGroup | None = None
        self._segment_colors: list[Color] = []
        self._segment_lines: list[Line] = []
        self._segment_slots_used: set[int] = set()
        self._segment_next_slot: int = 0

        # Polygons (closed outlines)
        self._poly_group: InstructionGroup | None = None
        self._poly_colors: list[Color] = []
        self._poly_segments: list[Line] = []
        self._poly_slots_used: set[int] = set()
        self._poly_next_slot: int = 0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def draw(self, frame: Texture, instructions: dict | Sequence[dict] | None) -> Texture:
        if (
            not self.cfg.debug.show_debug
            or frame is None
            or not instructions
        ):
            self._clear_points()
            self._clear_lines()
            self._clear_polygons()
            return frame

        self._line_slots_used.clear()
        self._segment_slots_used.clear()
        self._segment_next_slot = 0
        self._poly_slots_used.clear()
        self._poly_next_slot = 0
        rendered = False
        items = instructions if isinstance(instructions, (list, tuple)) else [instructions]
        items = sorted(items, key=lambda item: item.get("z", 0))

        for item in items:
            if not getattr(self.cfg.debug, item.get("debug", ""), False):
                continue
            fn = self._layers.get(item.get("draw"))
            if fn:
                frame = fn(frame, item)
                rendered = True

        if not rendered:
            self._clear_points()
            self._clear_lines()
            self._clear_segments()
            self._clear_polygons()
        else:
            self._clear_unused_points()
            self._clear_unused_lines()
            self._clear_unused_segments()
            self._clear_unused_polygons()

        return frame

    # ------------------------------------------------------------------ #
    # Points layer
    # ------------------------------------------------------------------ #
    def _draw_points(self, frame: Texture, overlay: dict) -> Texture:
        points = overlay.get("location")
        if (
            points is None
            or len(points) == 0
            or not self.preview
        ):
            self._clear_points()
            return frame

        key = overlay.get("group") or overlay.get("debug") or "default"
        layer = self._point_layers.get(key)
        if layer is None:
            layer = {"group": None, "color": None, "ellipses": [], "used": False}
            self._point_layers[key] = layer

        points = np.asarray(points, dtype=np.float32)
        color = _resolve_color(overlay.get("color"), self.cfg.overlay.pts_color)
        base_radius = float(overlay.get("size", self.cfg.overlay.pts_radius))

        widget_h, widget_w = self.preview.height, self.preview.width
        tex_h, tex_w = frame.height, frame.width
        if widget_w == 0 or widget_h == 0 or tex_w == 0 or tex_h == 0:
            self._clear_points()
            return frame

        scale = min(widget_w / tex_w, widget_h / tex_h)
        display_w = tex_w * scale
        display_h = tex_h * scale
        offset_x = (widget_w - display_w) / 2.0
        offset_y = (widget_h - display_h) / 2.0
        radius = max(1.0, base_radius * scale)
        diameter = radius * 2.0

        layer_group = layer["group"]
        layer_color = layer["color"]
        ellipses = layer["ellipses"]

        if self._canvas is None and self.preview:
            self._canvas = self.preview.canvas.after
        if self._canvas is None:
            return frame

        if layer_group is None:
            layer_group = InstructionGroup()
            layer_color = Color(*color)
            layer_group.add(layer_color)
            self._canvas.add(layer_group)
            layer["group"] = layer_group
            layer["color"] = layer_color
        else:
            layer_color.rgba = color

        while len(ellipses) < len(points):
            ell = Ellipse(size=(0, 0))
            layer_group.add(ell)
            ellipses.append(ell)

        for idx, (x_norm, y_norm) in enumerate(points):
            ell = ellipses[idx]
            x_px = offset_x + x_norm * display_w
            y_px = offset_y + (1.0 - y_norm) * display_h
            ell.pos = (x_px - radius, y_px - radius)
            ell.size = (diameter, diameter)

        for idx in range(len(points), len(ellipses)):
            ellipses[idx].size = (0, 0)

        layer["used"] = True
        return frame

    def _clear_points(self) -> None:
        for layer in self._point_layers.values():
            color = layer.get("color")
            if color:
                r, g, b, _ = color.rgba
                color.rgba = (r, g, b, 0)
            for ell in layer.get("ellipses", []):
                ell.size = (0, 0)

    def _clear_unused_points(self) -> None:
        for layer in self._point_layers.values():
            if not layer.get("used"):
                color = layer.get("color")
                if color:
                    r, g, b, _ = color.rgba
                    color.rgba = (r, g, b, 0)
                for ell in layer.get("ellipses", []):
                    ell.size = (0, 0)
    # ------------------------------------------------------------------ #
    # Polygon layer
    # ------------------------------------------------------------------ #
    def _draw_polygon(self, frame: Texture, overlay: dict) -> Texture:
        if not self.preview:
            self._clear_polygons()
            return frame

        points = overlay.get("points")
        if points is None or len(points) < 3:
            return frame

        pts = np.asarray(points, dtype=np.float32)
        color = _resolve_color(overlay.get("color"), self.cfg.overlay.region_color)
        width = float(overlay.get("width", self.cfg.overlay.region_width))

        widget_h, widget_w = self.preview.height, self.preview.width
        tex_h, tex_w = frame.height, frame.width
        if widget_w == 0 or widget_h == 0 or tex_w == 0 or tex_h == 0:
            return frame

        scale = min(widget_w / tex_w, widget_h / tex_h)
        display_w = tex_w * scale
        display_h = tex_h * scale
        offset_x = (widget_w - display_w) / 2.0
        offset_y = (widget_h - display_h) / 2.0

        coords: list[float] = []
        for x_norm, y_norm in pts:
            x_px = offset_x + x_norm * display_w
            y_px = offset_y + (1.0 - y_norm) * display_h
            coords.extend([x_px, y_px])

        slot_value = overlay.get("slot")
        if slot_value is None:
            slot = self._poly_next_slot
            self._poly_next_slot += 1
        else:
            slot = int(slot_value)

        self._ensure_polygon_primitives(slot + 1)
        color_instr = self._poly_colors[slot]
        seg = self._poly_segments[slot]

        color_instr.rgba = color
        seg.points = coords
        seg.width = width

        self._poly_slots_used.add(slot)
        return frame

    def _ensure_polygon_primitives(self, count: int) -> None:
        if self._canvas is None and self.preview:
            self._canvas = self.preview.canvas.after
        if self._canvas is None:
            return

        if self._poly_group is None:
            self._poly_group = InstructionGroup()
            self._canvas.add(self._poly_group)

        while len(self._poly_segments) < count:
            color_instr = Color(0, 0, 0, 0)
            line_instr = Line(points=[], width=0, close=True, joint="round")
            self._poly_group.add(color_instr)
            self._poly_group.add(line_instr)
            self._poly_colors.append(color_instr)
            self._poly_segments.append(line_instr)

    def _clear_polygons(self) -> None:
        for color_instr in self._poly_colors:
            r, g, b, _ = color_instr.rgba
            color_instr.rgba = (r, g, b, 0)
        for seg in self._poly_segments:
            seg.points = []

    def _clear_unused_polygons(self) -> None:
        for idx, seg in enumerate(self._poly_segments):
            if idx not in self._poly_slots_used:
                self._poly_colors[idx].rgba = (*self._poly_colors[idx].rgba[:3], 0)
                seg.points = []

    # ------------------------------------------------------------------ #
    # Segment layer
    # ------------------------------------------------------------------ #
    def _draw_segment(self, frame: Texture, overlay: dict) -> Texture:
        if not self.preview:
            self._clear_segments()
            return frame

        pts = overlay.get("points")
        if pts is None:
            return frame
        pts = np.asarray(pts, dtype=np.float32)
        if pts.shape != (2, 2):
            return frame

        color = _resolve_color(overlay.get("color"), self.cfg.overlay.midline_color)
        width = float(overlay.get("width", self.cfg.overlay.midline_width))

        widget_h, widget_w = self.preview.height, self.preview.width
        tex_h, tex_w = frame.height, frame.width
        if widget_w == 0 or widget_h == 0 or tex_w == 0 or tex_h == 0:
            return frame

        scale = min(widget_w / tex_w, widget_h / tex_h)
        display_w = tex_w * scale
        display_h = tex_h * scale
        offset_x = (widget_w - display_w) / 2.0
        offset_y = (widget_h - display_h) / 2.0

        coords: list[float] = []
        for x_norm, y_norm in pts:
            x_px = offset_x + x_norm * display_w
            y_px = offset_y + (1.0 - y_norm) * display_h
            coords.extend([x_px, y_px])

        slot_value = overlay.get("slot")
        if slot_value is None:
            slot = self._segment_next_slot
            self._segment_next_slot += 1
        else:
            slot = int(slot_value)

        self._ensure_segment_primitives(slot + 1)
        color_instr = self._segment_colors[slot]
        seg = self._segment_lines[slot]

        color_instr.rgba = color
        seg.points = coords
        seg.width = width

        self._segment_slots_used.add(slot)
        return frame

    def _ensure_segment_primitives(self, count: int) -> None:
        if self._canvas is None and self.preview:
            self._canvas = self.preview.canvas.after
        if self._canvas is None:
            return

        if self._segment_group is None:
            self._segment_group = InstructionGroup()
            self._canvas.add(self._segment_group)

        while len(self._segment_lines) < count:
            color_instr = Color(0, 0, 0, 0)
            line_instr = Line(points=[0, 0, 0, 0], width=0, cap="round")
            self._segment_group.add(color_instr)
            self._segment_group.add(line_instr)
            self._segment_colors.append(color_instr)
            self._segment_lines.append(line_instr)

    def _clear_segments(self) -> None:
        for color_instr in self._segment_colors:
            r, g, b, _ = color_instr.rgba
            color_instr.rgba = (r, g, b, 0)
        for seg in self._segment_lines:
            seg.points = [0, 0, 0, 0]

    def _clear_unused_segments(self) -> None:
        for idx, seg in enumerate(self._segment_lines):
            if idx not in self._segment_slots_used:
                self._segment_colors[idx].rgba = (*self._segment_colors[idx].rgba[:3], 0)
                seg.points = [0, 0, 0, 0]


    # ------------------------------------------------------------------ #
    # Line layer
    # ------------------------------------------------------------------ #
    def _draw_line(self, frame: Texture, overlay: dict) -> Texture:
        if not self.preview:
            self._clear_lines()
            return frame

        line_obj: Line2D | None = overlay.get("line")
        if line_obj is None:
            return frame

        slot = int(overlay.get("slot", 0))
        color = _resolve_color(overlay.get("color"), self.cfg.overlay.midline_color)
        width = float(overlay.get("width", self.cfg.overlay.midline_width))

        widget_h, widget_w = self.preview.height, self.preview.width
        tex_h, tex_w = frame.height, frame.width
        if widget_w == 0 or widget_h == 0 or tex_w == 0 or tex_h == 0:
            return frame

        segment = self._line_segment_in_unit_square(line_obj)
        if segment is None:
            return frame

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

        self._ensure_line_primitives(slot + 1)
        color_instr = self._line_colors[slot]
        seg = self._line_segments[slot]

        color_instr.rgba = color
        seg.points = [x1_px, y1_px, x2_px, y2_px]
        seg.width = width

        self._line_slots_used.add(slot)
        return frame

    def _ensure_line_primitives(self, count: int) -> None:
        if self._canvas is None and self.preview:
            self._canvas = self.preview.canvas.after
        if self._canvas is None:
            return

        if self._line_group is None:
            self._line_group = InstructionGroup()
            self._canvas.add(self._line_group)

        while len(self._line_segments) < count:
            color_instr = Color(0, 0, 0, 0)
            line_instr = Line(points=[0, 0, 0, 0], width=0, cap="round")
            self._line_group.add(color_instr)
            self._line_group.add(line_instr)
            self._line_colors.append(color_instr)
            self._line_segments.append(line_instr)

    def _clear_lines(self) -> None:
        for color_instr in self._line_colors:
            r, g, b, _ = color_instr.rgba
            color_instr.rgba = (r, g, b, 0)
        for seg in self._line_segments:
            seg.points = [0, 0, 0, 0]

    def _clear_unused_lines(self) -> None:
        for idx, seg in enumerate(self._line_segments):
            if idx not in self._line_slots_used:
                self._line_colors[idx].rgba = (*self._line_colors[idx].rgba[:3], 0)
                seg.points = [0, 0, 0, 0]

    def _line_segment_in_unit_square(
        self, line: Line2D
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return the two intersections of `line` with the unit square, ordered by projection."""

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
        hex_code = _COLOR_MAP.get(value.lower(), value)
        return get_color_from_hex(hex_code)
    if isinstance(value, (tuple, list)):
        if max(value) > 1.0:
            rgb = [c / 255.0 for c in value[:3]]
            alpha = value[3] / 255.0 if len(value) == 4 else 1.0
        else:
            rgb = list(value[:3])
            alpha = value[3] if len(value) == 4 else 1.0
        return (*rgb, alpha)
    return get_color_from_hex(fallback)

