# Author: RD7
# Purpose: Processing Pipeline
# Created: 2025-10-03

from src.config import Config
from src.landmarks import FaceMeshDetector
from src.overlay import Overlay
from kivy.graphics.texture import Texture

class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.det = FaceMeshDetector(cfg)
        if self.cfg.debug.show_debug: self.overlay = Overlay(cfg)


    def process_frame(self, frame: Texture):
        
        # first few camera frames can be None
        # guard against that by returning None
        if frame is None:  return None

        # Detect face landmarks
        landmarks = self.det.detect(frame)

        # process overlay
        if self.cfg.debug.show_debug:
            instructions = [{
                "draw"      :   "points",
                "debug"     :   "landmarks",
                "location"  :   landmarks,
                "color"     :   "green",
                "size"      :   5
            }]
            frame = self.overlay.draw(frame,instructions)

        # Apply horizontal flip if configured
        if frame is None:
            print("no frame 3!")
            return None

        if self.cfg.camera.hflip:
            frame = frame.get_region(0, 0, frame.width, frame.height)
            frame.flip_horizontal()

        return frame