# Author: RD7
# Purpose: Main controller for MimicMotion application
# Created: 2025-10-03

from src.config import Config
from src.pipeline import Pipeline
from src.camera import Camera

def build_config(args):
    cfg = Config()
    
    # runtime settings
    cfg.runtime.mode = args.mode
    cfg.runtime.droopy = args.droopy

    # Camera settings
    cfg.camera.hflip = args.hflip
    cfg.camera.index = args.camera_index
    cfg.camera.width = args.camera_width
    cfg.camera.height = args.camera_height
    cfg.camera.fps = args.camera_fps
    
    # debugging settings
    cfg.debug.show_debug = args.debug

    return cfg

def MainController(args):
    # Build configuration from command line arguments
    cfg = build_config(args)

    # Initialize Pipeline and Camera with configuration
    pipe = Pipeline(cfg)
    cam = Camera(cfg)
    
    cam.start()
    cam.release()
