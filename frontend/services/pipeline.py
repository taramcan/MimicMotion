# Author: RD7
# Purpose: Processing Pipeline
# Created: 2025-10-03

from services import nodes
from services.config import Config
from services.landmarks import FaceMeshDetector
from services.overlay import Overlay
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

        # If the frame is moving and FaceMeshDetctor returns None
        # then the system fails. So return to the last good set we had.
        if landmarks is not None:
            self._last_landmarks = landmarks
        else:  
            landmarks = getattr(self,"_last_landmarks",None)

        # process overlay
        if self.cfg.debug.show_debug and landmarks is not None:
            instructions = [{
                "draw"      :   "points",
                "debug"     :   "landmarks",
                "location"  :   landmarks,
                "color"     :   self.cfg.overlay.pts_color,
                "size"      :   self.cfg.overlay.pts_radius
            }]
            frame = self.overlay.draw(frame,instructions)

        # Apply horizontal flip if configured
        if self.cfg.camera.hflip:
            frame = frame.get_region(0, 0, frame.width, frame.height)
            frame.flip_horizontal()

        return frame
