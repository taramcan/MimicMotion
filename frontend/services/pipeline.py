# Author: RD7
# Purpose: Processing Pipeline
# Created: 2025-10-03

from __future__ import annotations

import numpy as np

from typing import Optional

from services.config import Config
from services.landmarks import FaceMeshDetector
from services.midline import Line2D, Midline
from services.overlay import Overlay
from kivy.graphics.texture import Texture


class Pipeline:
    """Orchestrates camera frames, landmark detection, and overlay rendering."""

    def __init__(self, cfg: Config, preview_widget: Optional[Texture] = None):
        self.cfg = cfg
        self.detector = FaceMeshDetector(cfg)
        self.midline_helper = Midline(cfg)
        self.overlay = Overlay(cfg, preview_widget) if preview_widget else None

        self._last_landmarks: Optional[np.ndarray] = None
        self._last_midline: Optional[Line2D] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def process_frame(self, frame: Texture) -> Optional[Texture]:
        if frame is None:
            return None

        landmarks = self._detect_landmarks(frame)
        display_landmarks = self._mirror_landmarks_if_needed(landmarks)
        midline, perpendicular = self._compute_midline_overlays(display_landmarks)

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

        midline = self.midline_helper.midsagittal_line(display_landmarks)
        self._last_midline = midline

        perpendicular = None
        if midline is not None:
            nose_tip = display_landmarks[1]  # landmark index 1 is the nose tip
            perpendicular = self.midline_helper.midsagittal_perpendicular(nose_tip, midline)

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
                "location": landmarks,
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
                    "debug": "midline",
                    "line": perpendicular,
                    "slot": 1,
                    "color": self.cfg.overlay.perp_color,
                    "width": self.cfg.overlay.perp_width,
                }
            )

        return instructions
