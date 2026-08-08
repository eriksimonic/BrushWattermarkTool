"""Locates a photo's focal subject so auto-placed watermarks can avoid it.

Uses a small bundled ONNX salient-object-detection model (see
brush_watermark/assets/salient_object.onnx and the README's "Third-party
assets" section) run locally via onnxruntime — no network access, and no
assumption that the subject is a human face (animals, flowers, objects all
work, since the model finds "the visually important thing" rather than a
fixed class).
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MODEL_PATH = Path(__file__).resolve().parents[1] / "assets" / "salient_object.onnx"
_MODEL_INPUT_SIZE = 320
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

# Conservative defaults: low threshold + extra dilation margin both favor
# over-protecting the subject rather than risking a watermark landing on it.
DEFAULT_THRESHOLD = 50  # out of 255 (~20% saliency probability)
DEFAULT_MARGIN_RATIO = 0.10  # dilation radius as a fraction of the short edge

_session = None


def _get_session():
    global _session
    if _session is None:
        import onnxruntime as ort

        _session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
    return _session


def _preprocess(image: Image.Image) -> np.ndarray:
    resized = image.convert("RGB").resize(
        (_MODEL_INPUT_SIZE, _MODEL_INPUT_SIZE), Image.Resampling.BILINEAR
    )
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    for channel in range(3):
        arr[:, :, channel] = (arr[:, :, channel] - _IMAGENET_MEAN[channel]) / _IMAGENET_STD[channel]
    return arr.transpose(2, 0, 1)[None, ...].astype(np.float32)


def saliency_map(image: Image.Image) -> Image.Image:
    """Return a full-resolution 'L' saliency map (0=background, 255=subject)."""
    session = _get_session()
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    tensor = _preprocess(image)
    result = session.run([output_name], {input_name: tensor})[0]
    small = (np.clip(result[0, 0], 0.0, 1.0) * 255.0).astype(np.uint8)
    return Image.fromarray(small, mode="L").resize(image.size, Image.Resampling.BILINEAR)


def _dilate(mask: Image.Image, radius: int) -> Image.Image:
    """Approximate morphological dilation by ~radius px via blur + re-threshold."""
    if radius <= 0:
        return mask
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=radius))
    return blurred.point(lambda v: 255 if v > 0 else 0)


def subject_protect_mask(
    image: Image.Image,
    threshold: int = DEFAULT_THRESHOLD,
    margin_ratio: float = DEFAULT_MARGIN_RATIO,
) -> Image.Image:
    """Return a binary 'L' mask (255=protected subject area) with a conservative margin."""
    sal = saliency_map(image)
    binary = sal.point(lambda v: 255 if v >= threshold else 0)
    margin_px = max(4, int(min(image.size) * margin_ratio))
    return _dilate(binary, margin_px)
