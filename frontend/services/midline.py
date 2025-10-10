# Author: RD7
# Purpose: Calculate midsagittal and perpendicular face lines
# Created: 2025-10-08

from __future__ import annotations

from services.config import Config
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class Line2D:
    """Normalized 2D line representation (origin + unit direction)."""

    origin: np.ndarray        # shape (2,)
    direction: np.ndarray     # unit vector shape (2,)

    def point_at(self, t: float) -> np.ndarray:
        """Return a point on the line at parameter t."""
        return self.origin + t * self.direction

    def project(self, point: np.ndarray) -> np.ndarray:
        """Project a point onto the line and return the projection coordinates."""
        rel = point - self.origin
        t = np.dot(rel, self.direction)
        return self.point_at(t)


class Midline():
    """
    Compute the face midline using four fixed landmarks and provide perpendicular helpers.

    Landmark order:
        0: chin tip (index 152)
        1: nose tip (index 1)
        2: glabella / between eyebrows (index 168)
        3: forehead (index 10)
    """

    MIDLINE_INDICES: tuple[int, int, int, int] = (152, 1, 168, 10)

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def midsagittal_line(self, landmarks: np.ndarray) -> Line2D | None:
        """
        Compute the midsagittal line (best-fit axis) using the four fixed landmarks.

        Parameters
        ----------
        landmarks : np.ndarray
            Full landmark array, shape (N, 2).

        Returns
        -------
        Line2D | None
            Normalized line representation, or None if the landmarks were unavailable.
        """
        if landmarks is None or len(landmarks) == 0:
            return None

        try:
            pts = np.asarray(landmarks, dtype=np.float32)[list(self.MIDLINE_INDICES)]
        except IndexError:
            return None

        centroid = pts.mean(axis=0)
        centered = pts - centroid

        # PCA by SVD on the centered points
        _, _, vh = np.linalg.svd(centered, full_matrices=False)
        direction = vh[0]
        if direction[1] < 0:
            direction = -direction

        direction /= np.linalg.norm(direction)
        return Line2D(origin=centroid, direction=direction)

    def midsagittal_perpendicular(self, landmark: Sequence[float], midline: Line2D) -> Line2D | None:
        """
        Return the line perpendicular to `midline` passing through `landmark`.

        Parameters
        ----------
        landmark : Sequence[float]
            (x, y) landmark coordinate.
        midline : Line2D
            The midsagittal line previously computed.

        Returns
        -------
        Line2D | None
            Perpendicular line representation, or None if inputs were invalid.
        """
        if landmark is None or midline is None:
            return None

        point = np.asarray(landmark, dtype=np.float32)
        perp_direction = np.array([-midline.direction[1], midline.direction[0]], dtype=np.float32)
        perp_direction /= np.linalg.norm(perp_direction)

        return Line2D(origin=point, direction=perp_direction)
