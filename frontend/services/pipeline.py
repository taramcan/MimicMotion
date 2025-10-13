# Author: RD7
# Purpose: Processing Pipeline
# Created: 2025-10-03

from __future__ import annotations

import numpy as np

from typing import Optional

from services import nodes
from services.config import Config
from services.landmarks import FaceMeshDetector
from services.midline import Line2D, Midline
from services.overlay import Overlay
from services.calculate import compute_asymmetry_metrics
from kivy.graphics.texture import Texture

# Flip map to properly map debugging points
FLIP_MAP = {l: r for l, r in nodes.LEFT_RIGHT_PAIRS}
FLIP_MAP.update({r: l for l, r in nodes.LEFT_RIGHT_PAIRS})

def _convex_hull(points: np.ndarray) -> Optional[np.ndarray]:
    """Return the convex hull of the provided 2D points in CCW order."""
    if points is None:
        return None

    pts = np.asarray(points, dtype=np.float32)
    if pts.size == 0:
        return None

    pts = np.unique(pts, axis=0)
    if pts.shape[0] < 3:
        return None

    order = np.lexsort((pts[:, 1], pts[:, 0]))
    pts = pts[order]

    def cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[np.ndarray] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: list[np.ndarray] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = np.array(lower[:-1] + upper[:-1], dtype=np.float32)
    return hull if hull.shape[0] >= 3 else None


class Pipeline:
    """Orchestrates camera frames, landmark detection, and overlay rendering."""

    def __init__(self, cfg: Config, preview_widget: Optional[Texture] = None):
        self.cfg = cfg
        self.detector = FaceMeshDetector(cfg)
        self.midline_helper = Midline(cfg)
        self.overlay = Overlay(cfg, preview_widget) if preview_widget else None

        self._region_groups: list[tuple[str, list[int]]] = []

        for raw in (cfg.overlay.region_nodes or []):
            if isinstance(raw, dict) and "indices" in raw:
                name = raw.get("name", "custom")
                indices = list(raw["indices"])
            else:
                path = tuple(raw)
                if path and path[0] == "face":
                    path = path[1:]
                if not path:
                    continue
                try:
                    indices = sorted(nodes.get_indices(("face",) + path))
                except KeyError:
                    continue
                name = "/".join(("face",) + path)

            if self.cfg.camera.hflip:
                indices = sorted(FLIP_MAP.get(idx, idx) for idx in indices)

            if len(indices) < 3:
                continue

            self._region_groups.append((name, indices))


        self._last_landmarks: Optional[np.ndarray] = None
        self._last_midline: Optional[Line2D] = None
        self._last_metrics = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def process_frame(self, frame: Texture) -> Optional[Texture]:
        if frame is None:
            return None

        landmarks = self._detect_landmarks(frame)
        display_landmarks = self._mirror_landmarks_if_needed(landmarks)
        midline, perpendicular = self._compute_midline_overlays(display_landmarks)

        pose_ok = self._pose_within_limits(display_landmarks)
        metrics = None
        if pose_ok and midline is not None and display_landmarks is not None:
            tracked = self._healthy_with_midline_indices()
            metrics = compute_asymmetry_metrics(self.cfg, midline, tracked, display_landmarks)
        self._last_metrics = metrics

        processed_frame = self._flip_texture_if_needed(frame)

        if self.overlay:
            instructions = self._build_overlay_instructions(display_landmarks, midline, perpendicular)
            self.overlay.draw(processed_frame, instructions)

        return processed_frame

    # ------------------------------------------------------------------ #
    # Landmark handling
    # ------------------------------------------------------------------ #
    def _detect_landmarks(self, frame: Texture) -> Optional[np.ndarray]:
        landmarks = self.detector.detect(frame)
        if landmarks is not None:
            self._last_landmarks = landmarks
        else:
            landmarks = self._last_landmarks
        return landmarks

    def _mirror_landmarks_if_needed(self, landmarks: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if landmarks is None or not self.cfg.camera.hflip:
            return landmarks
        mirrored = landmarks.copy()
        mirrored[:, 0] = 1.0 - mirrored[:, 0]
        return mirrored

    # ------------------------------------------------------------------ #
    # Midline helpers
    # ------------------------------------------------------------------ #
    def _compute_midline_overlays(
        self,
        display_landmarks: Optional[np.ndarray],
    ) -> tuple[Optional[Line2D], Optional[Line2D]]:
        if display_landmarks is None:
            self._last_midline = None
            return None, None

        xy_landmarks = display_landmarks[:, :2]
        midline = self.midline_helper.midsagittal_line(xy_landmarks)
        self._last_midline = midline

        perpendicular = None
        if midline is not None:
            node = xy_landmarks[61]  # landmark index 1 is the nose tip
            perpendicular = self.midline_helper.midsagittal_perpendicular(node, midline)

        return midline, perpendicular

    # ------------------------------------------------------------------ #
    # Frame utilities
    # ------------------------------------------------------------------ #
    def _flip_texture_if_needed(self, frame: Texture) -> Texture:
        if not self.cfg.camera.hflip:
            return frame
        flipped = frame.get_region(0, 0, frame.width, frame.height)
        flipped.flip_horizontal()
        return flipped

    def _region_polygons(self, landmarks: Optional[np.ndarray]) -> list[dict]:
        if (
            landmarks is None
            or not getattr(self.cfg.debug, "regions", False)
            or not self._region_groups
        ):
            return []

        overlays: list[dict] = []
        for path, indices in self._region_groups:
            region_pts = landmarks[indices][:, :2]
            hull = _convex_hull(region_pts)
            if hull is None:
                continue

            overlays.append(
                {
                    "draw": "polygon",
                    "debug": "regions",
                    "points": hull,
                    "color": self.cfg.overlay.region_color,
                    "width": self.cfg.overlay.region_width,
                }
            )

        return overlays

    def _healthy_with_midline_indices(self) -> list[int]:
        if self.cfg.method.tracked_indices:
            return sorted(self.cfg.method.tracked_indices)

        droopy = (self.cfg.runtime.droopy or "left").lower()
        healthy = "right" if droopy == "left" else "left"
        healthy_set = nodes.RIGHT_LANDMARKS if healthy == "right" else nodes.LEFT_LANDMARKS
        combined = healthy_set | nodes.MIDLINE_LANDMARKS
        return sorted(combined)

    def _pose_within_limits(self, landmarks: np.ndarray | None) -> bool:
        if landmarks is None or landmarks.ndim != 2 or landmarks.shape[1] < 3:
            return True

        indices = [idx for idx in self.cfg.method.pose_reference_indices if idx < len(landmarks)]
        if not indices:
            return True

        z_vals = landmarks[indices, 2]
        deviations = np.abs(z_vals - z_vals.mean())
        return float(np.max(deviations)) <= self.cfg.method.pose_max_abs_z

    # ------------------------------------------------------------------ #
    # Overlay construction
    # ------------------------------------------------------------------ #
    def _build_overlay_instructions(
        self,
        landmarks: Optional[np.ndarray],
        midline: Optional[Line2D],
        perpendicular: Optional[Line2D],
    ) -> Optional[list[dict]]:
        if not self.cfg.debug.show_debug or landmarks is None:
            return None

        instructions: list[dict] = [
            {
                "draw": "points",
                "debug": "landmarks",
                "location": landmarks[:, :2],
                "color": self.cfg.overlay.pts_color,
                "size": self.cfg.overlay.pts_radius,
            }
        ]

        if getattr(self.cfg.debug, "midline", True) and midline is not None:
            instructions.append(
                {
                    "draw": "line",
                    "debug": "midline",
                    "line": midline,
                    "slot": 0,
                    "color": self.cfg.overlay.midline_color,
                    "width": self.cfg.overlay.midline_width,
                }
            )

        if getattr(self.cfg.debug, "midline_perp", True) and perpendicular is not None:
            instructions.append(
                {
                    "draw": "line",
                    "debug": "perpendicular",
                    "line": perpendicular,
                    "slot": 1,
                    "color": self.cfg.overlay.perp_color,
                    "width": self.cfg.overlay.perp_width,
                }
            )

        instructions.extend(self._region_polygons(landmarks))

        return instructions





