from __future__ import annotations

from PIL import Image, ImageDraw

from brush_watermark.rendering.fonts import load_font
from brush_watermark.services.exif_metadata import ImageMetadata

FOOTER_BG = (32, 32, 34)
FOOTER_TEXT = (235, 233, 228)
CAPTION_FONT = "Segoe UI"
MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 16


def caption_text(metadata: ImageMetadata, additional_copy: str = "") -> str:
    return metadata.caption_line(additional_copy)


def caption_font_size(image_width: int) -> int:
    scaled = int(max(1, image_width) * 0.012)
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, scaled))


def footer_padding(image_width: int, font_size: int | None = None) -> int:
    size = font_size or caption_font_size(image_width)
    return max(12, size)


def footer_height(image_width: int, font_size: int | None = None) -> int:
    size = font_size or caption_font_size(image_width)
    padding = footer_padding(image_width, size)
    return padding * 2 + size + 2


def estimate_footer_height(image_width: int, metadata: ImageMetadata, additional_copy: str = "") -> int:
    return footer_height(image_width)


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_name: str,
    max_width: int,
    start_size: int,
    min_size: int = MIN_FONT_SIZE,
):
    for size in range(start_size, min_size - 1, -1):
        font = load_font(font_name, size)
        if draw.textlength(text, font=font) <= max_width:
            return font, size
    font = load_font(font_name, min_size)
    return font, min_size


def append_metadata_footer(
    image: Image.Image,
    metadata: ImageMetadata,
    additional_copy: str = "",
) -> Image.Image:
    base = image.convert("RGB")
    width, height = base.size
    caption = caption_text(metadata, additional_copy)
    start_font_size = caption_font_size(width)
    padding = footer_padding(width, start_font_size)
    max_text_width = max(1, width - padding * 2)

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    font, _ = _fit_font(probe, caption, CAPTION_FONT, max_text_width, start_font_size)
    text_bbox = probe.textbbox((0, 0), caption, font=font)
    text_height = text_bbox[3] - text_bbox[1]
    strip_height = padding * 2 + text_height

    combined = Image.new("RGB", (width, height + strip_height), FOOTER_BG)
    combined.paste(base, (0, 0))

    draw = ImageDraw.Draw(combined)
    footer_center_y = height + strip_height // 2
    draw.text(
        (padding, footer_center_y),
        caption,
        font=font,
        fill=FOOTER_TEXT,
        anchor="lm",
    )

    return combined
