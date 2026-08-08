"""Computes a "barely visible" watermark strength from the pixels under a stroke.

A flat, low-contrast area makes even a faint mark obvious, while busy,
high-contrast texture visually masks a stronger one — the "contrast
masking" effect behind classical perceptual/noise-visibility watermarking
models. Sampling the local luminance variation under a stroke's own brush
mask and mapping it to an opacity keeps every stroke reading as
consistently faint regardless of what it's sitting on. Used for
auto-placed strokes, and for manual strokes when "Auto strength" is
enabled.
"""

import numpy as np
from PIL import Image

from brush_watermark.geometry.points import Point
from brush_watermark.models import Stroke
from brush_watermark.rendering.masks import make_stroke_mask

MIN_OPACITY = 3
MAX_OPACITY = 20

# Local luminance std-dev (0-255 scale) at which strength saturates to MAX_OPACITY.
_SATURATION_STD = 45.0


def local_luminance_std(image: Image.Image, mask: Image.Image) -> float:
    """Mask-weighted std-dev of luminance — how busy/textured the area under `mask` is."""
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    weight = np.asarray(mask, dtype=np.float32)
    total_weight = float(weight.sum())
    if total_weight <= 0:
        return 0.0
    mean = float((gray * weight).sum() / total_weight)
    variance = float(((gray - mean) ** 2 * weight).sum() / total_weight)
    return max(0.0, variance) ** 0.5


def barely_visible_opacity(image: Image.Image, mask: Image.Image) -> int:
    """Map local texture under `mask` to an opacity that stays faint on any background."""
    std = local_luminance_std(image, mask)
    ratio = min(1.0, std / _SATURATION_STD)
    opacity = MIN_OPACITY + ratio * (MAX_OPACITY - MIN_OPACITY)
    return int(round(opacity))


def opacity_for_path(
    image: Image.Image, points: list[Point], brush_size: int, mask_softness: int = 1
) -> int:
    """Barely-visible opacity for a stroke path that hasn't been created yet."""
    scratch = Stroke(name="", points=list(points), brush_size=brush_size, opacity=0)
    width, height = image.size
    mask = make_stroke_mask(width, height, [scratch], mask_softness, brush_size)
    return barely_visible_opacity(image, mask)
