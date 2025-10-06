# Author: RD7
# Purpose: Face landmark utilities and detectors built on MediaPipe FaceMesh
# Created: 2025-10-05

import mediapipe as mp
import numpy as np
from kivy.graphics.texture import Texture

from src.config import Config
import src._nodes as _nodes


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
    # will have to apply (w,h) multiplication outside to get pixel coordinates
    def detect(self, frame:Texture):
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
        # grab frame size
        h, w = frame.height, frame.width
        
        # convert texture pixel data to numpy array
        arr = np.frombuffer(frame.pixels, dtype=np.uint8)

        # determine number of channels based on color format
        colorfmt = frame.colorfmt.lower()
        if colorfmt in {"rgba", "bgra"}:
            channels = 4
        elif colorfmt in {"rgb", "bgr"}:
            channels = 3
        else:
            return None  # unsupported format

        # reshape and flip the array to get correct orientation
        arr = arr.reshape((h, w, channels))
        arr = np.flip(arr, axis=0)

        # extract RGB channels and convert BGR to RGB if needed
        rgb = arr[..., :3]
        if colorfmt in {"bgra", "bgr"}:
            rgb = rgb[:, :, ::-1]

        # return contiguous array for MediaPipe processing
        return np.ascontiguousarray(rgb)

# from __future__ import annotations

# from typing import Optional, Union

# import mediapipe as mp
# import numpy as np
# from kivy.graphics.texture import Texture

# from src import nodes as _nodes

# # Re-export landmark group helpers/constants from src.nodes so callers can keep
# # importing from src.landmarks.
# for _name in _nodes.__all__:
#     globals()[_name] = getattr(_nodes, _name)

# __all__ = list(_nodes.__all__) + ['FaceMeshDetector']


# class FaceMeshDetector:
#     """Thin wrapper around MediaPipe FaceMesh with Kivy texture support."""

#     def __init__(
#         self,
#         *,
#         static_image_mode: bool = False,
#         max_num_faces: int = 1,
#         refine_landmarks: bool = True,
#         min_detection_confidence: float = 0.5,
#         min_tracking_confidence: float = 0.5,
#     ) -> None:
#         self._face_mesh = mp.solutions.face_mesh.FaceMesh(
#             static_image_mode=static_image_mode,
#             max_num_faces=max_num_faces,
#             refine_landmarks=refine_landmarks,
#             min_detection_confidence=min_detection_confidence,
#             min_tracking_confidence=min_tracking_confidence,
#         )

#     def close(self) -> None:
#         if self._face_mesh is not None:
#             self._face_mesh.close()
#             self._face_mesh = None

#     def __del__(self) -> None:  # pragma: no cover - defensive cleanup
#         self.close()

#     def detect(self, frame: Union[Texture, np.ndarray]) -> Optional[np.ndarray]:
#         """Return 468 (x, y) image coordinates or None when no face is found."""
#         if self._face_mesh is None:
#             raise RuntimeError('FaceMeshDetector has been closed')

#         image = self._to_rgb_array(frame)
#         if image is None:
#             return None

#         results = self._face_mesh.process(image)
#         if not results.multi_face_landmarks:
#             return None

#         h, w = image.shape[:2]
#         landmarks = results.multi_face_landmarks[0].landmark
#         pts = np.array([(lm.x * w, lm.y * h) for lm in landmarks], dtype=np.float32)
#         return pts

#     @staticmethod
#     def _to_rgb_array(frame: Union[Texture, np.ndarray]) -> Optional[np.ndarray]:
#         """Map a Kivy Texture or numpy array to contiguous RGB uint8."""
#         if frame is None:
#             return None

#         if isinstance(frame, Texture):
#             pixel_data = frame.pixels  # bytes in the texture's color format
#             if not pixel_data:
#                 return None
#             arr = np.frombuffer(pixel_data, dtype=np.uint8)
#             colorfmt = frame.colorfmt.lower()
#             if colorfmt in {'rgba', 'bgra'}:
#                 channels = 4
#             elif colorfmt in {'rgb', 'bgr'}:
#                 channels = 3
#             else:
#                 raise ValueError(f'Unsupported texture color format: {frame.colorfmt}')

#             arr = arr.reshape(frame.height, frame.width, channels)
#             arr = np.flip(arr, axis=0)  # textures are bottom-to-top

#             if colorfmt in {'rgba', 'rgb'}:
#                 rgb = arr[..., :3]
#             else:  # bgra or bgr
#                 rgb = arr[..., :3][:, :, ::-1]
#             return np.ascontiguousarray(rgb)

#         if isinstance(frame, np.ndarray):
#             if frame.ndim == 2:  # grayscale -> stack into RGB
#                 rgb = np.repeat(frame[:, :, None], 3, axis=2)
#             elif frame.shape[2] == 4:
#                 rgb = frame[:, :, :3]
#             elif frame.shape[2] == 3:
#                 rgb = frame
#             else:
#                 raise ValueError('Unsupported ndarray shape for image data')
#             return np.ascontiguousarray(rgb)

#         raise TypeError('Unsupported frame type for FaceMeshDetector')


# # Convenience re-exports so callers can keep importing via src.landmarks.
# get_group = _nodes.get_group
# get_indices = _nodes.get_indices
# iter_groups = _nodes.iter_groups
# LANDMARK_GROUP_LOOKUP = _nodes.LANDMARK_GROUP_LOOKUP