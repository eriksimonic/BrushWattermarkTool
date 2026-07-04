from PIL import Image, ImageFilter

from brush_watermark.geometry.points import clamp
from brush_watermark.models import Settings, Stamp
from brush_watermark.rendering.blend import composite_rgba_layer, normalize_blend_mode
from brush_watermark.rendering.masks import apply_erase_mask
from brush_watermark.services.stamps import render_stamp_rgba, stamp_height_px


def make_stamp_layer(
    width: int,
    height: int,
    stamp: Stamp,
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float = 1.0,
) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    stamp_height = stamp_height_px(stamp.size, height)
    stamp_image = render_stamp_rgba(stamp.svg_name, stamp_height, stamp.tint_color)
    if stamp_image.getbbox() is None:
        return layer

    left = int(round(stamp.x))
    top = int(round(stamp.y)) - stamp_image.height

    if left + stamp_image.width <= 0 or top + stamp_image.height <= 0:
        return layer
    if left >= width or top >= height:
        return layer

    layer.alpha_composite(stamp_image, dest=(left, top))

    mask = layer.getchannel("A")
    mask_softness = 0
    mask = apply_erase_mask(mask, erase_mask, mask_softness, scale_factor)
    layer.putalpha(mask)
    return layer


def composite_stamps_onto(
    base: Image.Image,
    stamps: list[Stamp],
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float = 1.0,
) -> Image.Image:
    result = base.convert("RGBA")
    for stamp in stamps:
        if not stamp.visible:
            continue
        stamp_layer = make_stamp_layer(
            result.size[0],
            result.size[1],
            stamp,
            settings,
            erase_mask,
            scale_factor,
        )
        strength = clamp(stamp.opacity, 1, 100) / 100.0
        result = composite_rgba_layer(
            result,
            stamp_layer,
            normalize_blend_mode(stamp.blend_mode, settings.blend_mode),
            strength,
        )
    return result
