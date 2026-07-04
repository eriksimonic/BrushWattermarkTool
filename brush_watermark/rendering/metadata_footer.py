from __future__ import annotations

from PIL import Image, ImageDraw

from brush_watermark.rendering.fonts import load_font
from brush_watermark.services.exif_metadata import ImageMetadata

FOOTER_BG = (32, 32, 34)
FOOTER_TEXT = (235, 233, 228)
CAPTION_FONT = "Segoe UI"
MIN_FONT_SIZE = 12
FOOTER_HEIGHT_RATIO = 0.035
MIN_STRIP_HEIGHT = 28


def caption_text(metadata: ImageMetadata, additional_copy: str = "") -> str:
    return metadata.caption_line(additional_copy)


def footer_layout(image_width: int, image_height: int) -> tuple[int, int, int]:
    """Return padding, target font size, and target strip height for an image."""
    height = max(1, int(image_height))
    strip_height = max(MIN_STRIP_HEIGHT, int(height * FOOTER_HEIGHT_RATIO))
    padding = max(8, int(strip_height * 0.28))
    font_size = max(MIN_FONT_SIZE, strip_height - padding * 2)
    return padding, font_size, strip_height


def footer_height(image_width: int, image_height: int, font_size: int | None = None) -> int:
    padding, size, strip_height = footer_layout(image_width, image_height)
    if font_size is not None:
        return padding * 2 + font_size + 2
    return strip_height


def estimate_footer_height(
    image_width: int,
    image_height: int,
    metadata: ImageMetadata,
    additional_copy: str = "",
) -> int:
    padding, font_size, _ = footer_layout(image_width, image_height)
    return padding * 2 + font_size + 2


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
    padding, start_font_size, target_strip_height = footer_layout(width, height)
    max_text_width = max(1, width - padding * 2)

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    font, fitted_size = _fit_font(probe, caption, CAPTION_FONT, max_text_width, start_font_size)
    text_bbox = probe.textbbox((0, 0), caption, font=font)
    text_height = text_bbox[3] - text_bbox[1]
    strip_height = max(target_strip_height, padding * 2 + text_height)

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
