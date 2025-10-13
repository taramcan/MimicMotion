# Author: RD7
# Purpose: Configuration settings for MimicMotion application
# Created: 2025-10-03

from __future__ import annotations

from dataclasses import dataclass, field
from services import nodes

# Note: The source of truth for configurable default values is in the argument parsers
#       The source of truth for non-configurable default values is in the dataclass definitions

def _default_nodes() -> list[dict]:
    left = nodes.get_indices(("face", "sides", "left"))
    mid = nodes.get_indices(("face", "midline"))
    union_indices = sorted(left | mid)

    return [
        {
            "name": "left_with_midline",
            "indices": union_indices,
        }
    ]


@ dataclass
class DebugCfg:
    
    # current functionality: all debugs are on or off
    # if show_debug is flagged, then everything else defaults to True
    show_debug      :   bool |  None = None 
    landmarks       :   bool = True
    midline         :   bool  = False
    perpendicular   :   bool = False
    regions         :   bool = False


@ dataclass
class RuntimeCfg:
    droopy: str | None = None

@ dataclass
class CameraCfg:
    index: int | None = None
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    hflip: bool | None = None

@ dataclass
class MediaPipeCfg:
    max_num_faces: int = 1
    refine_landmarks: bool = True
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    smoothing_alpha: float = 0.5

@dataclass
class OverlayCfg:
    pts_color       : str = "#00FF00"  # hex and RGB
    pts_radius      : float = 0.5

    midline_color   : str = "#0000FF"
    midline_width   : float = 1.0

    perp_color      : str = "#FF00FF"
    perp_width      : float = 1.5

    region_color    : str = "#FFFF00"
    region_width    : float = 1.2
    region_nodes    : list[dict] = field(default_factory=_default_nodes)

@dataclass
class MethodCfg:
    """Processing method configuration (mirror vs warp)."""

    mode: str | None = None
    tracked_indices: list[int] = field(default_factory=list)

    # Warp options
    warp_solver: str | None = None
    warp_blend_width: float = 0.04
    warp_smoothing_enabled: bool = True
    warp_smoothing_alpha: float = 0.6
    warp_delaunay_refine_edges: bool = True
    warp_delaunay_min_triangle_area: float = 1e-4
    warp_tps_regularization: float = 0.0
    warp_tps_grid_size: tuple[int, int] = (40, 40)

    # Mirror options
    mirror_feather_width: float = 0.05

    # Pose tolerance
    pose_max_abs_z: float = 0.08
    pose_reference_indices: tuple[int, ...] = (1, 33, 263, 152)


@dataclass
class Config:
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)
    camera: CameraCfg = field(default_factory=CameraCfg)
    debug: DebugCfg = field(default_factory=DebugCfg)
    mp: MediaPipeCfg = field(default_factory=MediaPipeCfg)
    overlay: OverlayCfg = field(default_factory=OverlayCfg)
    method: MethodCfg = field(default_factory=MethodCfg)




