# Author: RD7
# Purpose: Blending helpers for warped face patches
# Created: 2025-10-10

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

__all__ = ["blend_with_mask"]


def blend_with_mask(
    original: np.ndarray,
    warped: np.ndarray,
    mask: np.ndarray,
    params: Optional[dict] = None,
) -> np.ndarray:
    """Blend *warped* content into *original* guided by *mask*.

    Parameters
    ----------
    original : np.ndarray
        Original frame (H, W, C) uint8.
    warped : np.ndarray
        Warped frame (H, W, C) float32 or uint8.
    mask : np.ndarray
        Blend mask (H, W, 1) in range [0, 1].
    params : dict | None
        Optional parameters: {"feather": float, "feather_kernel": int}.
    """

    if params is None:
        params = {}

    feather = float(params.get("feather", 0.02))
    kernel = params.get("feather_kernel")

    h, w = original.shape[:2]
    kernel_size = _compute_kernel(feather, kernel, max(h, w))

    mask_f = mask.astype(np.float32)
    if kernel_size > 1:
        mask_f = cv2.GaussianBlur(mask_f, (kernel_size, kernel_size), 0)

    if mask_f.ndim == 2:
        mask_f = mask_f[..., None]

    mask_f = np.clip(mask_f, 0.0, 1.0)
    warped_f = warped.astype(np.float32)
    original_f = original.astype(np.float32)

    blended = warped_f * mask_f + original_f * (1.0 - mask_f)
    return np.clip(blended, 0, 255).astype(original.dtype)


def _compute_kernel(feather: float, kernel: Optional[int], size: int) -> int:
    if kernel is not None and kernel > 1:
        return kernel if kernel % 2 == 1 else kernel + 1
    if feather <= 0:
        return 1
    k = max(3, int(feather * size))
    if k % 2 == 0:
        k += 1
    return k
