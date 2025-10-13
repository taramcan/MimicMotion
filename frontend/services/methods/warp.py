# Author: RD7
# Purpose: Piecewise image warping utilities
# Created: 2025-10-10

from __future__ import annotations

from typing import Iterable, Optional, Sequence

import cv2
import numpy as np

from .mesh import TriangleMesh, build_mesh
from . import blend

__all__ = ["warp_face", "piecewise_affine_warp"]


def warp_face(
    frame: np.ndarray,
    src_points: Sequence[Sequence[float]],
    dst_points: Sequence[Sequence[float]],
    mesh: TriangleMesh | None = None,
    method: str = "delaunay",
    blend_params: Optional[dict] = None,
) -> np.ndarray:
    """Warp *frame* so that *src_points* move to *dst_points*.

    Parameters
    ----------
    frame : np.ndarray
        Input image (H, W, C) in uint8.
    src_points, dst_points : Sequence[(x, y)]
        Normalized coordinates (0-1) describing corresponding landmarks.
    mesh : TriangleMesh | None
        Optional precomputed mesh over *src_points*.
    method : str
        Currently only "delaunay" is implemented; "tps" is reserved for future use.
    blend_params : dict | None
        Optional parameters forwarded to the blending helper.
    """

    if frame is None:
        raise ValueError("frame is required")

    src_arr = np.asarray(src_points, dtype=np.float32)
    dst_arr = np.asarray(dst_points, dtype=np.float32)
    if src_arr.shape != dst_arr.shape or src_arr.ndim != 2 or src_arr.shape[1] != 2:
        raise ValueError("src_points and dst_points must be Nx2 arrays of matches")
    if len(src_arr) < 3:
        raise ValueError("At least three points required for warping")

    if method.lower() != "delaunay":
        raise NotImplementedError("Only 'delaunay' warping is implemented so far")

    height, width = frame.shape[:2]
    src_px = _to_pixel(src_arr, width, height)
    dst_px = _to_pixel(dst_arr, width, height)

    if mesh is None:
        mesh = build_mesh(src_arr)

    warped, mask = piecewise_affine_warp(frame, src_px, dst_px, mesh)
    output = blend.blend_with_mask(frame, warped, mask, blend_params)
    return output


def piecewise_affine_warp(
    frame: np.ndarray,
    src_pixels: np.ndarray,
    dst_pixels: np.ndarray,
    mesh: TriangleMesh,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply a piecewise-affine warp and return (warped_frame, mask)."""

    h, w = frame.shape[:2]
    frame_f = frame.astype(np.float32)
    accumulator = np.zeros_like(frame_f, dtype=np.float32)
    weight = np.zeros((h, w, 1), dtype=np.float32)

    for tri in mesh.iter_indices():
        src_tri = src_pixels[list(tri)].astype(np.float32)
        dst_tri = dst_pixels[list(tri)].astype(np.float32)

        # Warp entire frame for simplicity; mask will restrict blending region
        warp_mat = cv2.getAffineTransform(src_tri, dst_tri)
        warped_full = cv2.warpAffine(
            frame_f,
            warp_mat,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )

        tri_mask = np.zeros((h, w), dtype=np.float32)
        cv2.fillConvexPoly(tri_mask, dst_tri.astype(np.int32), 1.0)
        tri_mask = tri_mask[..., None]

        accumulator += warped_full * tri_mask
        weight += tri_mask

    weight = np.clip(weight, 1e-6, None)
    warped = accumulator / weight
    mask = np.clip(weight, 0.0, 1.0)
    return warped.astype(np.float32), mask.astype(np.float32)


def _to_pixel(points: np.ndarray, width: int, height: int) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float32).copy()
    pts[:, 0] *= float(width)
    pts[:, 1] = (1.0 - pts[:, 1]) * float(height)
    return pts
