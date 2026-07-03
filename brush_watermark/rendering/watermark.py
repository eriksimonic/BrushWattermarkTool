import math

from PIL import Image, ImageDraw

from brush_watermark.geometry.path_text import (
    angle_unwrap,
    averaged_angle,
    blend_angles,
    point_at_distance,
)
from brush_watermark.geometry.points import clamp, normalize_text_direction, path_length
from brush_watermark.models import Settings, Stroke, TextSpan
from brush_watermark.rendering.blend import composite_watermark_layer, normalize_blend_mode
from brush_watermark.rendering.colors import parse_rgb
from brush_watermark.rendering.fonts import (
    FONT_SIZE_RATIO,
    TEXT_SPAN_FILL,
    font_size_from_brush,
    load_font,
)
from brush_watermark.rendering.masks import apply_erase_mask, make_stroke_mask


def text_dimensions(text: str, font_name: str, font_size: int) -> tuple[int, int, tuple]:
    font = load_font(font_name, font_size)
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1]), bbox


def fitted_font_size(
    points: list,
    brush_size: int,
    text: str,
    font_name: str,
    auto_fit: bool,
) -> int:
    if not text.strip():
        return font_size_from_brush(brush_size)
    length = path_length(points)
    if length <= 0:
        return font_size_from_brush(brush_size)
    size = min(font_size_from_brush(brush_size), max(10, int(brush_size * 0.70)))
    if not auto_fit:
        return size
    for candidate in range(size, 9, -1):
        text_w, _, _ = text_dimensions(text, font_name, candidate)
        if text_w <= length * 0.92:
            return candidate
    return 10


def build_glyph_cache(text: str, font, fill: tuple) -> list[tuple[Image.Image, int]]:
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    glyphs = []
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font)
        glyph_w = max(1, bbox[2] - bbox[0])
        glyph_h = max(1, bbox[3] - bbox[1])
        advance = max(1, glyph_w)
        pad = max(4, int(glyph_h * 0.25))
        glyph = Image.new("RGBA", (glyph_w + pad * 2, glyph_h + pad * 2), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((pad - bbox[0], pad - bbox[1]), ch, font=font, fill=fill)
        glyphs.append((glyph, advance))
    return glyphs


def compute_text_span(
    points: list,
    brush_size: int,
    text: str,
    font_name: str,
    auto_fit: bool,
) -> TextSpan | None:
    text = text.strip()
    if not text or len(points) < 2:
        return None
    points = normalize_text_direction(points)
    length = path_length(points)
    if length < 8:
        return None
    font_size = fitted_font_size(points, brush_size, text, font_name, auto_fit)
    font = load_font(font_name, font_size)
    glyphs = build_glyph_cache(text, font, (255, 255, 255, 255))
    base_width = sum(g[1] for g in glyphs)
    usable_length = length * 0.92
    used_span = min(usable_length, base_width + max(0.0, (usable_length - base_width) * TEXT_SPAN_FILL))
    start_d = max(0.0, (length - used_span) / 2.0)
    end_d = min(length, start_d + used_span)
    sx, sy, _ = point_at_distance(points, start_d)
    ex, ey, _ = point_at_distance(points, end_d)
    return TextSpan(
        points=points,
        font_size=font_size,
        base_width=base_width,
        used_span=used_span,
        start_d=start_d,
        end_d=end_d,
        start_xy=(sx, sy),
        end_xy=(ex, ey),
    )


def draw_centered_rotated(
    layer: Image.Image,
    glyph: Image.Image,
    x: float,
    y: float,
    angle_degrees: float,
) -> None:
    rotated = glyph.rotate(angle_degrees, expand=True, resample=Image.Resampling.BICUBIC)
    px = int(x - rotated.size[0] / 2)
    py = int(y - rotated.size[1] / 2)
    layer.alpha_composite(rotated, (px, py))


def draw_text_on_path(
    layer: Image.Image,
    stroke: Stroke,
    settings: Settings,
) -> None:
    if not stroke.visible:
        return
    raw_points = stroke.points
    if len(raw_points) < 2:
        return
    points = normalize_text_direction(raw_points)
    text = settings.watermark_text.strip()
    if not text:
        return
    length = path_length(points)
    if length < 8:
        return
    font_size = fitted_font_size(
        points, stroke.brush_size, text, settings.font_name, settings.auto_fit_text
    )
    font = load_font(settings.font_name, font_size)
    text_color = stroke.text_color
    r, g, b = parse_rgb(text_color)
    fill = (r, g, b, 255)
    glyphs = build_glyph_cache(text, font, fill)
    if not glyphs:
        return
    base_width = sum(g[1] for g in glyphs)
    usable_length = length * 0.92
    used_span = min(usable_length, base_width + max(0.0, (usable_length - base_width) * TEXT_SPAN_FILL))
    start = max(0.0, (length - used_span) / 2.0)
    total_extra = max(0.0, used_span - base_width)
    gap_extra = total_extra / max(1, len(glyphs) - 1)

    x0, y0, _ = point_at_distance(points, start)
    x1, y1, _ = point_at_distance(points, start + used_span)
    baseline_angle = math.atan2(y1 - y0, x1 - x0) + math.radians(stroke.angle_offset)

    pos = start
    prev_angle = baseline_angle
    for glyph, advance in glyphs:
        center_d = pos + advance / 2.0
        x, y, _ = point_at_distance(points, center_d)
        local_angle = averaged_angle(points, center_d, max(font_size * 2.4, 40))
        local_angle = angle_unwrap(baseline_angle, local_angle)
        mixed_angle = blend_angles(baseline_angle, local_angle, 0.28)
        mixed_angle = angle_unwrap(prev_angle, mixed_angle)
        max_step = math.radians(10)
        delta = mixed_angle - prev_angle
        if delta > max_step:
            mixed_angle = prev_angle + max_step
        elif delta < -max_step:
            mixed_angle = prev_angle - max_step
        draw_centered_rotated(layer, glyph, x, y, math.degrees(mixed_angle))
        prev_angle = mixed_angle
        pos += advance + gap_extra


def make_stroke_watermark_layer(
    width: int,
    height: int,
    stroke: Stroke,
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float = 1.0,
) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_text_on_path(layer, stroke, settings)
    stroke_mask = make_stroke_mask(
        width, height, [stroke], stroke.mask_softness, stroke.brush_size
    )
    stroke_mask = apply_erase_mask(stroke_mask, erase_mask, stroke.mask_softness, scale_factor)
    alpha_channel = layer.getchannel("A")
    alpha_channel = Image.composite(
        alpha_channel, Image.new("L", alpha_channel.size, 0), stroke_mask
    )
    layer.putalpha(alpha_channel)
    return layer


def make_watermark_layer(
    width: int,
    height: int,
    strokes: list[Stroke],
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float = 1.0,
) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for stroke in strokes:
        stroke_layer = make_stroke_watermark_layer(
            width, height, stroke, settings, erase_mask, scale_factor
        )
        layer.alpha_composite(stroke_layer)
    return layer


def composite_strokes_onto(base: Image.Image, strokes: list[Stroke], settings: Settings, erase_mask: Image.Image, scale_factor: float = 1.0) -> Image.Image:
    result = base.convert("RGBA")
    for stroke in strokes:
        if not stroke.visible:
            continue
        stroke_layer = make_stroke_watermark_layer(
            result.size[0], result.size[1], stroke, settings, erase_mask, scale_factor
        )
        strength = clamp(stroke.opacity, 1, 100) / 100.0
        result = composite_watermark_layer(
            result,
            stroke_layer,
            stroke.text_color,
            normalize_blend_mode(stroke.blend_mode, settings.blend_mode),
            strength,
        )
    return result


def composite_watermark(base: Image.Image, strokes: list[Stroke], settings: Settings, erase_mask: Image.Image) -> Image.Image:
    result = composite_strokes_onto(base, strokes, settings, erase_mask, 1.0)
    return result.convert("RGB")


def make_preview_image(
    original: Image.Image,
    display_w: int,
    display_h: int,
    strokes: list[Stroke],
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float,
) -> Image.Image:
    display_w = max(1, int(display_w))
    display_h = max(1, int(display_h))
    preview_base = original.resize((display_w, display_h), Image.Resampling.LANCZOS).convert("RGBA")
    return composite_strokes_onto(
        preview_base, strokes, settings, erase_mask, scale_factor
    ).convert("RGBA")
