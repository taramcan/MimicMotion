# Author: RD7
# Purpose: Main controller for MimicMotion application
# Created: 2025-10-03

from kivy.clock import Clock
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

def MainController(args, preview_widget=None):
    # Build configuration from command line arguments
    cfg = build_config(args)

    # Initialize Pipeline and Camera with configuration
    pipe = Pipeline(cfg)
    cam = Camera(cfg)

    cam.start()

    ticker = None
    if preview_widget is not None:
        
        # Refresh function to update the preview widget with the latest camera frame (coat room contents)
        def _refresh(dt):
            texture = cam.read()
            if texture is None:
                return
            preview_widget.texture = texture
            preview_widget.texture_size = texture.size
            preview_widget.canvas.ask_update()

        # Schedule the refresh function to run at the camera's FPS
        # (coat room check frequency)
        ticker = Clock.schedule_interval(_refresh, 1.0 / cfg.camera.fps)

    # Shutdown sequence (coat check ticket)
    def shutdown():
        if ticker is not None:
            ticker.cancel()
        cam.release()

    return shutdown
