from PIL import Image, ImageDraw, ImageFilter
import dataclasses
import math

from brush_watermark.geometry.path_text import (
    PathSampler,
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
from brush_watermark.models import Settings, Stroke, TextSpan
from brush_watermark.rendering.blend import composite_watermark_layer, normalize_blend_mode
from brush_watermark.rendering.colors import parse_rgb
from brush_watermark.rendering.fonts import (
    FONT_SIZE_RATIO,
    font_size_from_brush,
    load_font,
)
from brush_watermark.rendering.masks import make_stroke_mask

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


def _fit_text_glyphs(
    points: list,
    brush_size: int,
    text: str,
    font_name: str,
    auto_fit: bool,
    fill: tuple,
):
    """Compute the fitted font size, load it, and build the glyph cache for text."""
    font_size = fitted_font_size(points, brush_size, text, font_name, auto_fit)
    font = load_font(font_name, font_size)
    glyphs = build_glyph_cache(text, font, fill)
    base_width = sum(g[1] for g in glyphs)
    return font_size, font, glyphs, base_width


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
    font_size, _font, glyphs, base_width = _fit_text_glyphs(
        points, brush_size, text, font_name, auto_fit and not repeat_text, (255, 255, 255, 255)
    )
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


def _pad_glyph(glyph: Image.Image, anchor_x: float, anchor_y: float) -> Image.Image:
    """Centre the glyph's baseline anchor on a square canvas so rotation pivots on it."""
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
    return canvas


def _rotate_padded(canvas: Image.Image, angle_degrees: float) -> Image.Image:
    return canvas.rotate(angle_degrees, expand=True, resample=Image.Resampling.BICUBIC)


def _composite_rotated(
    layer: Image.Image,
    rotated: Image.Image,
    x: float,
    y: float,
    origin: tuple[int, int] = (0, 0),
) -> None:
    rcx = rotated.size[0] / 2.0
    rcy = rotated.size[1] / 2.0
    # Round in canvas coordinates before shifting by the integer origin, so a
    # layer rendered at an offset lands on exactly the same pixels.
    dest_x = int(round(x - rcx)) - origin[0]
    dest_y = int(round(y - rcy)) - origin[1]
    layer.alpha_composite(rotated, (dest_x, dest_y))


def draw_glyph_on_path(
    layer: Image.Image,
    glyph: Image.Image,
    anchor_x: float,
    anchor_y: float,
    x: float,
    y: float,
    angle_degrees: float,
) -> None:
    rotated = _rotate_padded(_pad_glyph(glyph, anchor_x, anchor_y), angle_degrees)
    _composite_rotated(layer, rotated, x, y)


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
    origin: tuple[int, int] = (0, 0),
) -> None:
    avg_advance = sum(g[1] for g in glyphs) / len(glyphs)
    sampler = PathSampler(points)
    # Repeated text re-draws the same letters, often at the same angle along
    # straight runs: pad each glyph once and reuse identical rotations.
    padded = [_pad_glyph(glyph, anchor_x, anchor_y) for glyph, _, anchor_x, anchor_y in glyphs]
    rotated_cache: dict[tuple[int, float], Image.Image] = {}
    pos = start_d
    while pos < end_d:
        if repeat and pos > start_d and repeat_gap > 0:
            if pos + repeat_gap > end_d:
                return
            pos += repeat_gap
        for glyph_index, (_glyph, advance, _anchor_x, _anchor_y) in enumerate(glyphs):
            if pos + advance > end_d:
                return
            center_d = pos + advance / 2.0
            x, y, _ = sampler.point_at(center_d)
            half_window = tangent_half_window(max(advance, avg_advance))
            raw_tangent = tangent_angle_at_distance(
                points,
                center_d,
                half_window,
                total_length=length,
                sampler=sampler,
            )
            if prev_tangent is not None:
                raw_tangent = angle_unwrap(prev_tangent, raw_tangent)
                tangent = blend_angles(prev_tangent, raw_tangent, TANGENT_SMOOTHING)
            else:
                tangent = raw_tangent
            prev_tangent = tangent
            angle_degrees = glyph_rotation_degrees(tangent, angle_offset)
            ox, oy = centered_baseline_offset(tangent, ascent, descent)
            key = (glyph_index, angle_degrees)
            rotated = rotated_cache.get(key)
            if rotated is None:
                rotated = _rotate_padded(padded[glyph_index], angle_degrees)
                rotated_cache[key] = rotated
            _composite_rotated(layer, rotated, x + ox, y + oy, origin)
            pos += advance + gap_extra
        if not repeat:
            break


def draw_text_on_path(
    layer: Image.Image,
    stroke: Stroke,
    settings: Settings,
    origin: tuple[int, int] = (0, 0),
) -> None:
    """Draw the stroke's text into layer, whose top-left sits at origin in canvas coordinates."""
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
    text_color = stroke.text_color
    r, g, b = parse_rgb(text_color)
    fill = (r, g, b, 255)
    font_size, font, glyphs, base_width = _fit_text_glyphs(
        points, stroke.brush_size, text, settings.font_name, settings.auto_fit_text and not repeat, fill
    )
    if not glyphs:
        return
    ascent, descent = font.getmetrics()
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
        origin=origin,
    )


def _blur_support(radius: float) -> int:
    """Pixels a GaussianBlur of this radius can spread a value, with slack."""
    return int(math.ceil(radius * 4)) + 4


def stroke_render_box(width: int, height: int, stroke: Stroke) -> tuple[int, int, int, int] | None:
    """Canvas region that can hold any of the stroke's pixels (its blurred mask), or None."""
    points = stroke.points
    if not points:
        return None
    margin = stroke.brush_size // 2 + 2 + _blur_support(stroke.mask_softness)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0 = max(0, int(math.floor(min(xs))) - margin)
    y0 = max(0, int(math.floor(min(ys))) - margin)
    x1 = min(width, int(math.ceil(max(xs))) + margin + 1)
    y1 = min(height, int(math.ceil(max(ys))) + margin + 1)
    if x0 >= x1 or y0 >= y1:
        return None
    return x0, y0, x1, y1


def _erase_blur_region(
    erase_mask: Image.Image,
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    mask_softness: int,
    scale_factor: float,
) -> Image.Image | None:
    """The blurred erase mask cropped to box, matching a full-canvas blur."""
    if not erase_mask.getbbox():
        return None
    if abs(scale_factor - 1.0) >= 0.0001:
        erase_mask = erase_mask.resize(size, Image.Resampling.BILINEAR)
    radius = max(0, int(mask_softness * scale_factor))
    # Blur a margin around the box too: erased pixels just outside it still
    # bleed in, exactly as they would when blurring the whole canvas.
    pad = _blur_support(radius)
    x0, y0, x1, y1 = box
    outer = (max(0, x0 - pad), max(0, y0 - pad), min(size[0], x1 + pad), min(size[1], y1 + pad))
    blurred = erase_mask.crop(outer).filter(ImageFilter.GaussianBlur(radius=radius))
    return blurred.crop((x0 - outer[0], y0 - outer[1], x1 - outer[0], y1 - outer[1]))


def render_stroke_layer(
    width: int,
    height: int,
    stroke: Stroke,
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float = 1.0,
) -> tuple[Image.Image | None, tuple[int, int, int, int] | None]:
    """Render a stroke's masked text layer, cropped to its visible pixels.

    Only the stroke's bounding region is drawn, masked and blurred, so cost
    scales with the stroke's size rather than the canvas. Returns
    ``(layer_crop, box)``, or ``(None, None)`` when nothing is visible.
    """
    region = stroke_render_box(width, height, stroke)
    if region is None:
        return None, None
    x0, y0, x1, y1 = region
    size = (x1 - x0, y1 - y0)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_text_on_path(layer, stroke, settings, origin=(x0, y0))
    local = dataclasses.replace(stroke, points=[(x - x0, y - y0) for x, y in stroke.points])
    stroke_mask = make_stroke_mask(size[0], size[1], [local], stroke.mask_softness, stroke.brush_size)
    erase_blur = _erase_blur_region(erase_mask, (width, height), region, stroke.mask_softness, scale_factor)
    if erase_blur is not None:
        stroke_mask = Image.composite(Image.new("L", size, 0), stroke_mask, erase_blur)
    alpha_channel = Image.composite(layer.getchannel("A"), Image.new("L", size, 0), stroke_mask)
    layer.putalpha(alpha_channel)
    bbox = layer.getbbox()
    if bbox is None:
        return None, None
    box = (x0 + bbox[0], y0 + bbox[1], x0 + bbox[2], y0 + bbox[3])
    return layer.crop(bbox), box


def make_stroke_watermark_layer(
    width: int,
    height: int,
    stroke: Stroke,
    settings: Settings,
    erase_mask: Image.Image,
    scale_factor: float = 1.0,
) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    layer_crop, box = render_stroke_layer(width, height, stroke, settings, erase_mask, scale_factor)
    if layer_crop is not None:
        layer.paste(layer_crop, box)
    return layer


def composite_strokes_onto(base: Image.Image, strokes: list[Stroke], settings: Settings, erase_mask: Image.Image, scale_factor: float = 1.0) -> Image.Image:
    """Blend each stroke onto base, touching only the stroke's own region."""
    result = base.convert("RGBA")
    for stroke in strokes:
        if not stroke.visible:
            continue
        layer_crop, box = render_stroke_layer(
            result.size[0], result.size[1], stroke, settings, erase_mask, scale_factor
        )
        if layer_crop is None:
            continue
        strength = clamp(stroke.opacity, 1, 100) / 100.0
        blended = composite_watermark_layer(
            result.crop(box),
            layer_crop,
            stroke.text_color,
            normalize_blend_mode(stroke.blend_mode, settings.blend_mode),
            strength,
        )
        result.paste(blended, box)
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
