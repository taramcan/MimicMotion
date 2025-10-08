# Author: RD7
# Purpose: Configuration settings for MimicMotion application
# Created: 2025-10-03

from dataclasses import dataclass, field

# Note: The source of truth for configurable default values is in the argument parsers
#       The source of truth for non-configurable default values is in the dataclass definitions

@ dataclass
class DebugCfg:
    
    # current functionality: all debugs are on or off
    # if show_debug is flagged, then everything else defaults to True
    show_debug      :   bool |  None = None 
    landmarks       :   bool = True
    midline         :   bool = True
    perpendicular   :   bool = True

@ dataclass
class RuntimeCfg:
    mode: str | None = None
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

@dataclass
class Config:
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)
    camera: CameraCfg = field(default_factory=CameraCfg)
    debug: DebugCfg = field(default_factory=DebugCfg)
    mp: MediaPipeCfg = field(default_factory=MediaPipeCfg)
    overlay: OverlayCfg = field(default_factory=OverlayCfg)
