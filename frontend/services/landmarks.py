# Author: RD7
# Purpose: Face landmark utilities and detectors built on MediaPipe FaceMesh
# Created: 2025-10-05

import mediapipe as mp
import numpy as np
from kivy.graphics.texture import Texture

from services.config import Config
from services import nodes

class FaceMeshDetector():
    def __init__(self, cfg:Config):
        
        # setup MediaPipe FaceMesh with configuration from Config definition
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=cfg.mp.max_num_faces,
            refine_landmarks=cfg.mp.refine_landmarks,
            min_detection_confidence=cfg.mp.min_detection_confidence,
            min_tracking_confidence=cfg.mp.min_tracking_confidence)

        # save the config for later use
        self.cfg = cfg

        # Intialize to no previous landmarks for smoothing
        self._smooth_landmarks = None

    # detect will return landmarks in (x, y, z) normalized coordinates
    # or None if no face is detected
    # returned as np.ndarray
    # will have to apply (w,h) multiplication outside to get pixel coordinates
    def detect(self, frame:Texture) -> np.ndarray:

        # Convert Kivy Texture to RGB numpy array for MediaPipe processing
        frame = self._texture_to_rgb_array(frame)
        
        # process the image and extract landmarks
        result = self._face_mesh.process(frame)
        
        # if no landmarks found, return None
        if not result.multi_face_landmarks:
            return None
        
        # extract the first face's landmarks
        landmarks = result.multi_face_landmarks[0].landmark

        # convert landmarks to x, y, z coordinates
        cur = np.asarray([(lm.x, lm.y, lm.z) for lm in landmarks], dtype=np.float32)

        # apply landmark smoothing if needed
        if self._smooth_landmarks is None:
            self._smooth_landmarks = cur
        else:
            prev = self._smooth_landmarks
            alpha = self.cfg.mp.smoothing_alpha
            
            # exponential moving average smoothing
            self._smooth_landmarks = alpha * prev + (1 - alpha) * cur
        
        # convert normalized landmarks to pixel coordinates
        pts = self._smooth_landmarks
        
        # return the landmarks
        return pts
    
    @staticmethod
    def _texture_to_rgb_array(frame: Texture) -> np.ndarray:
        w, h = frame.width, frame.height
        colorfmt = frame.colorfmt.lower()
        if colorfmt not in {"rgba", "bgra", "rgb", "bgr"}:
            raise ValueError(f"Unsupported texture color format: {frame.colorfmt}")

        arr = np.frombuffer(frame.pixels, dtype=np.uint8).copy()
        arr = arr.reshape((h, w, -1))  # Kivy stores column-major (rows = height)
        
        flip_x = frame.tex_coords[0] > frame.tex_coords[2]
        flip_y = frame.tex_coords[1] > frame.tex_coords[5]
        
        if flip_y:
            arr = np.flipud(arr)
        if flip_x:
            arr = np.fliplr(arr)
        if colorfmt in {"rgba", "bgra"}:
            arr = arr[:, :, :3]
        if colorfmt in {"bgra", "bgr"}:
            arr = arr[:, :, ::-1]

        # # tex_coords determine whether the texture is mirrored on the GPU
        # if frame.tex_coords[0] > frame.tex_coords[2]:
        #     arr = np.fliplr(arr)

        # Final flip so MediaPipe sees a top-left origin
        arr = np.flipud(arr)

        return np.ascontiguousarray(arr)

