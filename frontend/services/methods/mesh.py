# Author: RD7
# Purpose: Triangle mesh helpers for face warping
# Created: 2025-10-10

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from scipy.spatial import Delaunay  # type: ignore


__all__ = ["TriangleMesh", "build_mesh", "augment_with_boundary"]


@dataclass(slots=True)
class TriangleMesh:
    """Topology for piecewise-affine warping."""

    triangles: np.ndarray  # shape (M, 3), dtype=int

    def __post_init__(self) -> None:
        if self.triangles.ndim != 2 or self.triangles.shape[1] != 3:
            raise ValueError("triangles must be an (M, 3) integer array")

    def __len__(self) -> int:
        return int(self.triangles.shape[0])

    def iter_indices(self) -> Iterable[tuple[int, int, int]]:
        for tri in self.triangles:
            yield int(tri[0]), int(tri[1]), int(tri[2])


def build_mesh(points: Sequence[Sequence[float]]) -> TriangleMesh:
    """Construct a 2D Delaunay triangulation over *points*.

    Parameters
    ----------
    points:
        Iterable of (x, y) pairs in normalized coordinates.
    """

    pts = np.asarray(points, dtype=np.float32)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points must be an (N, 2) array of coordinates")
    if len(pts) < 3:
        raise ValueError("At least three points required to build a mesh")

    if Delaunay is None:
        raise RuntimeError(
            "scipy is required for Delaunay triangulation; install scipy>=1.8"
        )

    tri = Delaunay(pts)
    triangles = np.asarray(tri.simplices, dtype=np.int32)
    return TriangleMesh(triangles=triangles)


def augment_with_boundary(
    points: Sequence[Sequence[float]],
    frame_size: tuple[int, int],
    padding: float = 0.02,
) -> np.ndarray:
    """Append frame boundary anchors to *points* for more stable warps.

    The returned array contains the original points followed by four corner
    anchors and mid-edge anchors expanded by *padding* (normalized units).
    """

    pts = np.asarray(points, dtype=np.float32)
    if frame_size[0] <= 0 or frame_size[1] <= 0:
        raise ValueError("frame_size must be (width, height) with positive values")

    pad = float(padding)
    anchors = np.array(
        [
            (-pad, -pad),
            (1.0 + pad, -pad),
            (-pad, 1.0 + pad),
            (1.0 + pad, 1.0 + pad),
            (0.5, -pad),
            (0.5, 1.0 + pad),
            (-pad, 0.5),
            (1.0 + pad, 0.5),
        ],
        dtype=np.float32,
    )
    return np.vstack([pts, anchors])
