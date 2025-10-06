# Author: RD7
# Purpose: Processing Pipeline
# Created: 2025-10-03

from src.config import Config
from src.landmarks import FaceMeshDetector
from kivy.graphics.texture import Texture

class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.det = FaceMeshDetector(cfg)


    def process_frame(self, frame: Texture):
        
        # grab frame size
        h,w = frame.height, frame.width

        # Detect face landmarks
        landmarks = self.det.detect(frame)

        # Apply horizontal flip if configured
        if self.cfg.camera.hflip:
            frame = frame.get_region(0, 0, frame.width, frame.height)
            frame.flip_horizontal()

        return frame