# Author: RD7
# Purpose: Face landmark utilities and detectors built on MediaPipe FaceMesh
# Created: 2025-10-05

import mediapipe as mp
import numpy as np
from kivy.graphics.texture import Texture

from src import config as Config    
import src._nodes as _nodes




class FaceMeshDetector():
    def __init__(self, cfg:Config):
        
        # setup MediaPipe FaceMesh with configuration from Config definition
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=cfg.mediapipe.max_num_faces,
            refine_landmarks=cfg.mediapipe.refine_landmarks,
            min_detection_confidence=cfg.mediapipe.min_detection_confidence,
            min_tracking_confidence=cfg.mediapipe.min_tracking_confidence,
        )



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
        
        # convert normalized landmarks to pixel coordinates
        pts = np.array([(lm.x * w, lm.y * h) for lm in landmarks], dtype=np.float32)
        
        # return the landmarks
        return pts  
    
    @staticmethod
    def _texture_to_rgb_array(frame:Texture):
            
            # Grab frame size
            h,w = frame.height, frame.width

            # Grab the pixel data from the texture
            frame = frame.pixels

            # Convert the byte data to a numpy array
            frame = np.frombuffer(frame, dtype=np.uint8)
            
            # Reshape the array to (height, width, 4) for RGBA
            frame = frame.reshape((h, w, 4))
            
            # Discard the alpha channel to get RGB
            frame = frame[:,:,:3]

            # Needs to be c-continuous in memory for MediaPipe
            frame = np.ascontiguousarray(frame)

            return frame
    


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