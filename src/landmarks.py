# Author: RD7
# Purpose: Face landmark utilities and detectors built on MediaPipe FaceMesh
# Created: 2025-10-05

import mediapipe as mp
import numpy as np
from kivy.graphics.texture import Texture

from src.config import Config
from src import nodes

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

    # detect will return landmarks in (x,y) normalized coordinates
    # or None if no face is detected
    # returned as np.ndarray
    # will have to apply (w,h) multiplication outside to get pixel coordinates
    def detect(self, frame:Texture) -> np.ndarray:
        # grab frame size
        h,w = frame.height, frame.width

        # Convert Kivy Texture to RGB numpy array for MediaPipe processing
        frame = self._texture_to_rgb_array(frame)
        
        # process the image and extract landmarks
        result = self._face_mesh.process(frame)
        
        # if no landmarks found, return None
        if not result.multi_face_landmarks:
            return None
        
        # extract the first face's landmarks
        landmarks = result.multi_face_landmarks[0].landmark

        # convert landmarks to x, y coordinates
        cur = np.asarray([(lm.x, lm.y) for lm in landmarks], dtype=np.float32)

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

        arr = np.frombuffer(frame.pixels, dtype=np.uint8)
        arr = arr.reshape((h, w, -1))       # Kivy stores column-major

        if colorfmt in {"rgba", "bgra"}:
            arr = arr[:, :, :3]
        if colorfmt in {"bgra", "bgr"}:
            arr = arr[:, :, ::-1]  # BGR → RGB

        arr = np.flip(arr, axis=0)          # Flip vertically for OpenCV-style origin
        return np.ascontiguousarray(arr)


    # @staticmethod
    # def _texture_to_rgb_array(frame: Texture) -> np.ndarray:
    #     # grab frame size
    #     h, w = frame.height, frame.width
        
    #     # convert texture pixel data to numpy array
    #     arr = np.frombuffer(frame.pixels, dtype=np.uint8)

    #     # determine number of channels based on color format
    #     colorfmt = frame.colorfmt.lower()
    #     if colorfmt in {"rgba", "bgra"}:
    #         channels = 4
    #     elif colorfmt in {"rgb", "bgr"}:
    #         channels = 3
    #     else:
    #         return None  # unsupported format

    #     # reshape and flip the array to get correct orientation
    #     arr = arr.reshape((h, w, channels))
    #     arr = np.flip(arr, axis=0)

    #     # extract RGB channels and convert BGR to RGB if needed
    #     rgb = arr[..., :3]
    #     if colorfmt in {"bgra", "bgr"}:
    #         rgb = rgb[:, :, ::-1]

    #     # return contiguous array for MediaPipe processing
    #     return np.ascontiguousarray(rgb)