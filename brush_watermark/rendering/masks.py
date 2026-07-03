from PIL import Image, ImageDraw, ImageFilter

from brush_watermark.geometry.points import Point
from brush_watermark.models import Stroke


def make_stroke_mask(
    width: int,
    height: int,
    strokes: list[Stroke],
    mask_softness: int,
    default_brush_size: int,
) -> Image.Image:
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for stroke in strokes:
        if not stroke.visible:
            continue
        points = stroke.points
        brush_size = stroke.brush_size
        if len(points) == 1:
            x, y = points[0]
            r = brush_size // 2
            draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        elif len(points) > 1:
            draw.line(points, fill=255, width=brush_size, joint="curve")
            r = brush_size // 2
            for x, y in (points[0], points[-1]):
                draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
    if mask_softness > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=mask_softness))
    return mask


def apply_erase_mask(
    stroke_mask: Image.Image,
    erase_mask: Image.Image,
    mask_softness: int,
    scale_factor: float = 1.0,
) -> Image.Image:
    if not erase_mask.getbbox():
        return stroke_mask
    if abs(scale_factor - 1.0) >= 0.0001:
        erase_mask = erase_mask.resize(stroke_mask.size, Image.Resampling.BILINEAR)
    erase_blur = erase_mask.filter(
        ImageFilter.GaussianBlur(radius=max(0, int(mask_softness * scale_factor)))
    )
    return Image.composite(Image.new("L", stroke_mask.size, 0), stroke_mask, erase_blur)
