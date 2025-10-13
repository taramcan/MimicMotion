# Author: RD7
# Purpose: Facial asymmetry calculations for MimicMotion
# Created: 2025-10-09

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np

from services import nodes
from services.config import Config
from services.midline import Line2D

__all__ = [
    "AsymmetryMetrics",
    "LandmarkDisplacement",
    "MidlineAnchorMetric",
    "compute_asymmetry_metrics",
]


# --------------------------------------------------------------------------- #
# Helper mappings
# --------------------------------------------------------------------------- #
_FLIP_MAP: dict[int, int] = {}
for left, right in nodes.LEFT_RIGHT_PAIRS:
    _FLIP_MAP[left] = right
    _FLIP_MAP[right] = left

_SIDE_TO_LANDMARKS = {
    "left": nodes.LEFT_LANDMARKS,
    "right": nodes.RIGHT_LANDMARKS,
}


@dataclass(slots=True)
class LandmarkDisplacement:
    """Displacement metrics for a droopy/healthy landmark pair."""

    healthy_index: int
    droopy_index: int

    healthy_coords: np.ndarray
    droopy_coords: np.ndarray

    healthy_depth: float | None
    droopy_depth: float | None


    perpendicular_line: Line2D

    healthy_perp_offset: float
    droopy_perp_offset: float
    perpendicular_delta: float

    healthy_mid_offset: float
    droopy_mid_offset: float
    midline_delta: float

    x_delta: float
    y_delta: float
    weighted_delta: float


@dataclass(slots=True)
class MidlineAnchorMetric:
    """Displacement of a landmark expected to lie on the midline."""

    index: int
    coords: np.ndarray
    depth: float | None
    perpendicular_line: Line2D
    perpendicular_offset: float


@dataclass(slots=True)
class AsymmetryMetrics:
    """Container for all computed asymmetry metrics."""

    droopy_side: str
    healthy_side: str
    displacements: List[LandmarkDisplacement]
    midline_anchors: List[MidlineAnchorMetric]


# --------------------------------------------------------------------------- #
# Calculation entry point
# --------------------------------------------------------------------------- #

def compute_asymmetry_metrics(
    cfg: Config,
    midline: Line2D,
    tracked_indices: Sequence[int],
    landmarks: np.ndarray,
) -> AsymmetryMetrics:
    """Compute displacement metrics for tracked landmarks.

    Parameters
    ----------
    cfg : Config
        Application configuration (provides droopy side).
    midline : Line2D
        Current midsagittal line (normalized coordinates).
    tracked_indices : Sequence[int]
        Landmark indices selected for analysis.
    landmarks : np.ndarray
        Normalized landmark coordinates, shape (N, 2).
    """

    if midline is None or landmarks is None or len(landmarks) == 0:
        return AsymmetryMetrics(
            droopy_side=_resolve_droopy_side(cfg),
            healthy_side=_resolve_healthy_side(cfg),
            displacements=[],
            midline_anchors=[],
        )

    droopy_side = _resolve_droopy_side(cfg)
    healthy_side = _resolve_healthy_side(cfg)

    tracked_set = {idx for idx in tracked_indices if 0 <= idx < len(landmarks)}
    healthy_indices, droopy_indices, midline_indices = _classify_indices(
        tracked_set, droopy_side
    )

    # Always treat tracked droopy points as candidates for warping.
    for idx in droopy_indices:
        healthy_partner = _flipped_index(idx)
        if healthy_partner is not None and _belongs_to_side(
            healthy_partner, healthy_side
        ):
            healthy_indices.add(healthy_partner)

    displacements: list[LandmarkDisplacement] = []
    midline_metrics: list[MidlineAnchorMetric] = []

    for healthy_idx in sorted(healthy_indices):
        droopy_idx = _select_counterpart(healthy_idx, droopy_side)
        if droopy_idx is None or droopy_idx >= len(landmarks):
            continue

        healthy_coords = np.asarray(landmarks[healthy_idx], dtype=np.float32)
        droopy_coords = np.asarray(landmarks[droopy_idx], dtype=np.float32)

        healthy_xy = healthy_coords[:2]
        droopy_xy = droopy_coords[:2]

        perp_line = _perpendicular_line(healthy_xy, midline)
        healthy_mid, healthy_perp = _line_projections(healthy_xy, midline)
        droopy_mid, droopy_perp = _line_projections(droopy_xy, midline)

        perp_delta = healthy_perp - droopy_perp
        mid_delta = healthy_mid - droopy_mid
        dx, dy = _cartesian_delta(midline, mid_delta, perp_delta)
        weighted = perp_delta * mid_delta

        displacements.append(
            LandmarkDisplacement(
                healthy_index=healthy_idx,
                droopy_index=droopy_idx,
                healthy_coords=healthy_coords,
                droopy_coords=droopy_coords,
                healthy_depth=float(healthy_coords[2]) if healthy_coords.shape[0] >= 3 else None,
                droopy_depth=float(droopy_coords[2]) if droopy_coords.shape[0] >= 3 else None,
                perpendicular_line=perp_line,
                healthy_perp_offset=healthy_perp,
                droopy_perp_offset=droopy_perp,
                perpendicular_delta=perp_delta,
                healthy_mid_offset=healthy_mid,
                droopy_mid_offset=droopy_mid,
                midline_delta=mid_delta,
                x_delta=dx,
                y_delta=dy,
                weighted_delta=weighted,
            )
        )

    for anchor_idx in sorted(midline_indices):
        if anchor_idx >= len(landmarks):
            continue
        coords = np.asarray(landmarks[anchor_idx], dtype=np.float32)
        xy = coords[:2]
        perp_line = _perpendicular_line(xy, midline)
        _, perp_offset = _line_projections(xy, midline)
        midline_metrics.append(
            MidlineAnchorMetric(
                index=anchor_idx,
                coords=coords,
                depth=float(coords[2]) if coords.shape[0] >= 3 else None,
                perpendicular_line=perp_line,
                perpendicular_offset=perp_offset,
            )
        )

    return AsymmetryMetrics(
        droopy_side=droopy_side,
        healthy_side=healthy_side,
        displacements=displacements,
        midline_anchors=midline_metrics,
    )


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _resolve_droopy_side(cfg: Config) -> str:
    return (cfg.runtime.droopy or "left").lower()


def _resolve_healthy_side(cfg: Config) -> str:
    droopy = _resolve_droopy_side(cfg)
    return "right" if droopy == "left" else "left"


def _classify_indices(
    indices: Iterable[int],
    droopy_side: str,
) -> tuple[set[int], set[int], set[int]]:
    healthy_side = "right" if droopy_side == "left" else "left"
    healthy_set: set[int] = set()
    droopy_set: set[int] = set()
    midline_set: set[int] = set()

    for idx in indices:
        if idx in nodes.MIDLINE_LANDMARKS:
            midline_set.add(idx)
        elif _belongs_to_side(idx, droopy_side):
            droopy_set.add(idx)
        elif _belongs_to_side(idx, healthy_side):
            healthy_set.add(idx)
        else:
            # Default: treat unknown indices as midline anchors
            midline_set.add(idx)

    return healthy_set, droopy_set, midline_set


def _belongs_to_side(index: int, side: str) -> bool:
    return index in _SIDE_TO_LANDMARKS[side]


def _flipped_index(index: int) -> int | None:
    return _FLIP_MAP.get(index)


def _select_counterpart(healthy_index: int, droopy_side: str) -> int | None:
    """Return the mirrored droopy index for a healthy landmark."""

    counterpart = _flipped_index(healthy_index)
    if counterpart is None:
        return None
    if _belongs_to_side(counterpart, droopy_side):
        return counterpart
    # The supplied index might already belong to the droopy side; flip again.
    if _belongs_to_side(healthy_index, droopy_side):
        return healthy_index
    return None


def _perpendicular_line(point: np.ndarray, midline: Line2D) -> Line2D:
    direction = midline.direction
    perp_direction = np.array([direction[1], -direction[0]], dtype=np.float32)
    perp_direction /= np.linalg.norm(perp_direction)
    origin = np.asarray(point, dtype=np.float32)
    return Line2D(origin=origin, direction=perp_direction)


def _cartesian_delta(midline: Line2D, mid_delta: float, perp_delta: float) -> tuple[float, float]:
    """Return (dx, dy) with +x toward right ear and +y upward."""

    direction = midline.direction
    perp_direction = np.array([direction[1], -direction[0]], dtype=np.float32)
    delta_vec = mid_delta * direction + perp_delta * perp_direction
    dx = float(delta_vec[0])
    dy = float(-delta_vec[1])
    return dx, dy


def _line_projections(point: np.ndarray, midline: Line2D) -> tuple[float, float]:
    """Return (midline_component, perpendicular_component) for a point."""

    origin = midline.origin
    direction = midline.direction
    perp_direction = np.array([direction[1], -direction[0]], dtype=np.float32)

    rel = np.asarray(point, dtype=np.float32) - origin
    mid_component = float(np.dot(rel, direction))
    perp_component = float(np.dot(rel, perp_direction))
    return mid_component, perp_component


