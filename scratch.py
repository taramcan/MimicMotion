import cv2
import numpy as np

from frontend.services.methods.mesh import build_mesh
from frontend.services.methods.warp import piecewise_affine_warp
from frontend.services.methods.blend import blend_with_mask

WIDTH = HEIGHT = 64

# Base image with a red square (reference)
base = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
cv2.rectangle(base, (20, 20), (44, 44), (0, 0, 255), -1)

# Source image carrying the green square we intend to warp
warp_src = np.zeros_like(base)
cv2.rectangle(warp_src, (20, 20), (44, 44), (0, 255, 0), -1)

# Pixel-space landmark coordinates (x, y) using image origin (top-left)
pixel_src = np.array([
    (20, 20),
    (44, 20),
    (20, 44),
    (44, 44),
], dtype=np.float32)

# Convert to math-space normalized coordinates (+x right, +y up)
src = np.zeros_like(pixel_src)
src[:, 0] = pixel_src[:, 0] / WIDTH
src[:, 1] = 1.0 - (pixel_src[:, 1] / HEIGHT)

# Desired offsets in math space
shift_x = 5 / WIDTH
shift_y = 4 / HEIGHT
print(f"Math-space shift -> x: {shift_x:+.4f} (right positive), y: {shift_y:+.4f} (up positive)")

dst = src.copy()
dst[:, 0] += shift_x
dst[:, 1] += shift_y

# Convert back to pixel coordinates for the warper
src_px = np.column_stack((src[:, 0] * WIDTH, (1.0 - src[:, 1]) * HEIGHT))
dst_px = np.column_stack((dst[:, 0] * WIDTH, (1.0 - dst[:, 1]) * HEIGHT))

mesh = build_mesh(src)
warped_patch, mask = piecewise_affine_warp(warp_src, src_px, dst_px, mesh)
result = blend_with_mask(base, warped_patch, mask)

cv2.imwrite("debug_warp.png", result)
print("Wrote debug_warp.png")
