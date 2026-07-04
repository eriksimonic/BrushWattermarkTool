from PIL import Image, ImageDraw
import math

from brush_watermark.geometry.path_text import (
    angle_unwrap,
    blend_angles,
    centered_baseline_offset,
    glyph_rotation_degrees,
    point_at_distance,
    smooth_path_for_text,
    tangent_angle_at_distance,
    tangent_half_window,
)
from brush_watermark.geometry.points import clamp, normalize_text_direction, path_length
from brush_watermark.models import Settings, Stamp, Stroke, TextSpan
from brush_watermark.rendering.stamp import composite_stamps_onto
from brush_watermark.rendering.blend import composite_watermark_layer, normalize_blend_mode
from brush_watermark.rendering.colors import parse_rgb
from brush_watermark.rendering.fonts import (
    FONT_SIZE_RATIO,
    font_size_from_brush,
    load_font,
)
from brush_watermark.rendering.masks import apply_erase_mask, make_stroke_mask

TEXT_BASELINE_ANCHOR = "ms"
TANGENT_SMOOTHING = 0.35


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
        if text_w <= length:
            return candidate
    return 10


def space_advance(font) -> float:
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    return max(1.0, float(draw.textlength(" ", font=font)))


def build_glyph_cache(text: str, font, fill: tuple) -> list[tuple[Image.Image, int, float, float]]:
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    glyphs = []
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font, anchor=TEXT_BASELINE_ANCHOR)
        left, top, right, bottom = bbox
        glyph_w = max(1, right - left)
        glyph_h = max(1, bottom - top)
        advance = max(1, int(math.ceil(draw.textlength(ch, font=font))))
        pad = max(4, int(glyph_h * 0.25))
        canvas_w = int(math.ceil(glyph_w + pad * 2))
        canvas_h = int(math.ceil(glyph_h + pad * 2))
        anchor_x = pad - left
        anchor_y = pad - top
        glyph = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((anchor_x, anchor_y), ch, font=font, fill=fill, anchor=TEXT_BASELINE_ANCHOR)
        glyphs.append((glyph, advance, anchor_x, anchor_y))
    return glyphs


def _prepare_text_path(raw_points: list) -> list:
    if len(raw_points) < 2:
        return raw_points
    return smooth_path_for_text(normalize_text_direction(raw_points))


def compute_text_span(
    points: list,
    brush_size: int,
    text: str,
    font_name: str,
    auto_fit: bool,
    repeat_text: bool = False,
) -> TextSpan | None:
    text = text.strip()
    if not text or len(points) < 2:
        return None
    points = _prepare_text_path(points)
    length = path_length(points)
    if length < 8:
        return None
    font_size = fitted_font_size(
        points, brush_size, text, font_name, auto_fit and not repeat_text
    )
    font = load_font(font_name, font_size)
    glyphs = build_glyph_cache(text, font, (255, 255, 255, 255))
    base_width = sum(g[1] for g in glyphs)
    start_d = 0.0
    end_d = length
    used_span = length
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


def draw_glyph_on_path(
    layer: Image.Image,
    glyph: Image.Image,
    anchor_x: float,
    anchor_y: float,
    x: float,
    y: float,
    angle_degrees: float,
) -> None:
    half = int(
        math.ceil(
            max(
                anchor_x,
                glyph.size[0] - anchor_x,
                anchor_y,
                glyph.size[1] - anchor_y,
            )
        )
    ) + 1
    canvas = Image.new("RGBA", (half * 2, half * 2), (0, 0, 0, 0))
    paste_x = half - int(round(anchor_x))
    paste_y = half - int(round(anchor_y))
    canvas.paste(glyph, (paste_x, paste_y))
    rotated = canvas.rotate(angle_degrees, expand=True, resample=Image.Resampling.BICUBIC)
    rcx = rotated.size[0] / 2.0
    rcy = rotated.size[1] / 2.0
    layer.alpha_composite(rotated, (int(round(x - rcx)), int(round(y - rcy))))


def _draw_glyphs_on_path(
    layer: Image.Image,
    glyphs: list[tuple[Image.Image, int, float, float]],
    points: list,
    length: float,
    start_d: float,
    end_d: float,
    gap_extra: float,
    angle_offset: int,
    repeat: bool,
    ascent: float,
    descent: float,
    repeat_gap: float = 0.0,
    prev_tangent: float | None = None,
) -> None:
    avg_advance = sum(g[1] for g in glyphs) / len(glyphs)
    pos = start_d
    while pos < end_d:
        if repeat and pos > start_d and repeat_gap > 0:
            if pos + repeat_gap > end_d:
                return
            pos += repeat_gap
        for glyph, advance, anchor_x, anchor_y in glyphs:
            if pos + advance > end_d:
                return
            center_d = pos + advance / 2.0
            x, y, _ = point_at_distance(points, center_d)
            half_window = tangent_half_window(max(advance, avg_advance))
            raw_tangent = tangent_angle_at_distance(
                points,
                center_d,
                half_window,
                total_length=length,
            )
            if prev_tangent is not None:
                raw_tangent = angle_unwrap(prev_tangent, raw_tangent)
                tangent = blend_angles(prev_tangent, raw_tangent, TANGENT_SMOOTHING)
            else:
                tangent = raw_tangent
            prev_tangent = tangent
            angle_degrees = glyph_rotation_degrees(tangent, angle_offset)
            ox, oy = centered_baseline_offset(tangent, ascent, descent)
            draw_glyph_on_path(
                layer, glyph, anchor_x, anchor_y, x + ox, y + oy, angle_degrees
            )
            pos += advance + gap_extra
        if not repeat:
            break


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
    points = _prepare_text_path(raw_points)
    text = settings.watermark_text.strip()
    if not text:
        return
    length = path_length(points)
    if length < 8:
        return
    repeat = stroke.repeat_text
    font_size = fitted_font_size(
        points,
        stroke.brush_size,
        text,
        settings.font_name,
        settings.auto_fit_text and not repeat,
    )
    font = load_font(settings.font_name, font_size)
    text_color = stroke.text_color
    r, g, b = parse_rgb(text_color)
    fill = (r, g, b, 255)
    glyphs = build_glyph_cache(text, font, fill)
    if not glyphs:
        return
    ascent, descent = font.getmetrics()
    base_width = sum(g[1] for g in glyphs)
    start = 0.0
    end = length
    if repeat:
        gap_extra = 0.0
        repeat_gap = max(0, stroke.repeat_spacing) * space_advance(font)
    else:
        total_extra = max(0.0, length - base_width)
        gap_extra = total_extra / max(1, len(glyphs) - 1)
        repeat_gap = 0.0
    _draw_glyphs_on_path(
        layer,
        glyphs,
        points,
        length,
        start,
        end,
        gap_extra,
        stroke.angle_offset,
        repeat=repeat,
        ascent=float(ascent),
        descent=float(descent),
        repeat_gap=repeat_gap,
    )


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


def composite_watermark(base: Image.Image, strokes: list[Stroke], settings: Settings, erase_mask: Image.Image, stamps: list[Stamp] | None = None) -> Image.Image:
    result = composite_strokes_onto(base, strokes, settings, erase_mask, 1.0)
    if stamps:
        result = composite_stamps_onto(result, stamps, settings, erase_mask, 1.0)
    return result.convert("RGB")


def make_preview_image(
    original: Image.Image,
    display_w: int,
    display_h: int,
    strokes: list[Stroke],
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float,
    stamps: list[Stamp] | None = None,
) -> Image.Image:
    display_w = max(1, int(display_w))
    display_h = max(1, int(display_h))
    preview_base = original.resize((display_w, display_h), Image.Resampling.LANCZOS).convert("RGBA")
    result = composite_strokes_onto(
        preview_base, strokes, settings, erase_mask, scale_factor
    )
    if stamps:
        result = composite_stamps_onto(result, stamps, settings, erase_mask, scale_factor)
    return result.convert("RGBA")
