# Author: RD7
# Purpose: Processing Pipeline
# Created: 2025-10-03

from services import nodes
from services.config import Config
from services.landmarks import FaceMeshDetector
from services.overlay import Overlay
from kivy.graphics.texture import Texture

class Pipeline:
    def __init__(self, cfg: Config, preview_widget = None):
        self.cfg = cfg
        self.det = FaceMeshDetector(cfg)
        self.overlay = Overlay(cfg, preview_widget) if preview_widget else None


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

        display_landmarks = landmarks
        if display_landmarks is not None and self.cfg.camera.hflip:
            display_landmarks = landmarks.copy()
            display_landmarks[:,0] = 1.0 - display_landmarks[:,0]

        # Apply horizontal flip if configured
        if self.cfg.camera.hflip:
            frame = frame.get_region(0, 0, frame.width, frame.height)
            frame.flip_horizontal()

        # process overlay
        if self.overlay:
            instructions = None
            if self.cfg.debug.show_debug and display_landmarks is not None:
                instructions = [{
                    "draw"      :   "points",
                    "debug"     :   "landmarks",
                    "location"  :   display_landmarks,
                    "color"     :   self.cfg.overlay.pts_color,
                    "size"      :   self.cfg.overlay.pts_radius
                }]
                self.overlay.draw(frame,instructions)
            else:
                self.overlay.draw(frame,None)
        return frame
