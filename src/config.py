# Author: RD7
# Purpose: Configuration settings for MimicMotion application
# Created: 2025-10-03

from dataclasses import dataclass, field

# Note: The source of truth for default values is in the argument parsers

@ dataclass
class DebugCfg:
    show_debug: bool |  None = None 

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

@dataclass
class Config:
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)
    camera: CameraCfg = field(default_factory=CameraCfg)
    debug: DebugCfg = field(default_factory=DebugCfg)