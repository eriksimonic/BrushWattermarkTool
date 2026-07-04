from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from brush_watermark.config import stamps_dir
from brush_watermark.geometry.points import clamp
from brush_watermark.models import Stamp

STAMP_EXTENSIONS = {".svg", ".png"}
STAMP_SIZE_MIN_PERCENT = 1
STAMP_SIZE_MAX_PERCENT = 300


def stamp_height_px(size_percent: int, image_height: int) -> int:
    """Convert stamp size (% of image height) to pixel height."""
    percent = clamp(size_percent, STAMP_SIZE_MIN_PERCENT, STAMP_SIZE_MAX_PERCENT)
    return max(1, int(round(image_height * percent / 100.0)))


def normalize_stamp_size_percent(value: int | float, *, legacy_pixels: bool = False) -> int:
    """Normalize stored stamp size; values above max were legacy pixel sizes."""
    size = int(round(value))
    if legacy_pixels and size > STAMP_SIZE_MAX_PERCENT:
        size = max(STAMP_SIZE_MIN_PERCENT, min(STAMP_SIZE_MAX_PERCENT, round(size / 10)))
    return clamp(size, STAMP_SIZE_MIN_PERCENT, STAMP_SIZE_MAX_PERCENT)


def list_stamps() -> list[str]:
    directory = stamps_dir()
    if not directory.is_dir():
        return []
    names = [
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in STAMP_EXTENSIONS
    ]
    return sorted(names)


def list_stamp_svgs() -> list[str]:
    """Backward-compatible alias for :func:`list_stamps`."""
    return list_stamps()


def reload_stamp_catalog() -> list[str]:
    """Rescan the stamps folder and clear cached stamp dimensions."""
    stamp_pixel_size.cache_clear()
    return list_stamps()


def stamp_file_path(stamp_name: str) -> Path:
    return stamps_dir() / stamp_name


def stamp_svg_path(stamp_name: str) -> Path:
    """Backward-compatible alias for :func:`stamp_file_path`."""
    return stamp_file_path(stamp_name)


def _is_svg(path: Path) -> bool:
    return path.suffix.lower() == ".svg"


def _scaled_size(default_size: QSize, target_height: int) -> tuple[int, int]:
    height = max(1, int(target_height))
    if default_size.height() <= 0:
        return height, height
    aspect = default_size.width() / default_size.height()
    width = max(1, int(round(height * aspect)))
    return width, height


def _scaled_size_from_wh(source_w: int, source_h: int, target_height: int) -> tuple[int, int]:
    height = max(1, int(target_height))
    if source_h <= 0:
        return height, height
    aspect = source_w / source_h
    width = max(1, int(round(height * aspect)))
    return width, height


def _native_source_size(path: Path) -> tuple[int, int]:
    if not path.is_file():
        return 0, 0
    if _is_svg(path):
        renderer = QSvgRenderer(str(path))
        if not renderer.isValid():
            return 0, 0
        size = renderer.defaultSize()
        return size.width(), size.height()
    with Image.open(path) as image:
        return image.size


@lru_cache(maxsize=128)
def stamp_pixel_size(stamp_name: str, target_height: int) -> tuple[int, int]:
    path = stamp_file_path(stamp_name)
    source_w, source_h = _native_source_size(path)
    if source_w <= 0 or source_h <= 0:
        return max(1, target_height), max(1, target_height)
    return _scaled_size_from_wh(source_w, source_h, target_height)


def stamp_bounds(
    stamp_name: str,
    x: int,
    y: int,
    size_percent: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """Return left, top, right, bottom in image coordinates (bottom-left anchor)."""
    height_px = stamp_height_px(size_percent, image_height)
    width, height = stamp_pixel_size(stamp_name, height_px)
    left = int(x)
    bottom = int(y)
    top = bottom - height
    right = left + width
    return left, top, right, bottom


def _qimage_to_pil(image: QImage) -> Image.Image:
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width = image.width()
    height = image.height()
    ptr = image.constBits()
    raw = bytes(ptr) if isinstance(ptr, (bytes, bytearray)) else ptr.tobytes()
    pil = Image.frombuffer("RGBA", (width, height), raw, "raw", "RGBA", 0, 1)
    return pil.copy()


def _apply_tint(image: Image.Image, tint_color: str) -> Image.Image:
    from brush_watermark.rendering.colors import parse_rgb

    r, g, b = parse_rgb(tint_color)
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            _, _, _, alpha = pixels[x, y]
            if alpha:
                pixels[x, y] = (r, g, b, alpha)
    return rgba


def _render_svg_rgba(path: Path, target_height: int) -> Image.Image:
    height = max(1, int(target_height))
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return Image.new("RGBA", (height, height), (0, 0, 0, 0))
    width, height = _scaled_size(renderer.defaultSize(), height)
    qimage = QImage(width, height, QImage.Format.Format_ARGB32)
    qimage.fill(0)
    painter = QPainter(qimage)
    renderer.render(painter)
    painter.end()
    return _qimage_to_pil(qimage)


def _render_png_rgba(path: Path, target_height: int) -> Image.Image:
    height = max(1, int(target_height))
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
    width, height = _scaled_size_from_wh(rgba.width, rgba.height, height)
    return rgba.resize((width, height), Image.Resampling.LANCZOS)


def render_stamp_rgba(stamp_name: str, target_height: int, tint_color: str | None = None) -> Image.Image:
    path = stamp_file_path(stamp_name)
    height = max(1, int(clamp(target_height, 1, 2000)))
    if not path.is_file():
        return Image.new("RGBA", (height, height), (0, 0, 0, 0))

    suffix = path.suffix.lower()
    if suffix == ".svg":
        image = _render_svg_rgba(path, height)
    elif suffix == ".png":
        image = _render_png_rgba(path, height)
    else:
        return Image.new("RGBA", (height, height), (0, 0, 0, 0))

    if tint_color:
        image = _apply_tint(image, tint_color)
    return image


def stamp_hit_test(
    stamp: Stamp,
    img_x: int,
    img_y: int,
    image_height: int,
    extra_tol: float = 0.0,
) -> bool:
    left, top, right, bottom = stamp_bounds(stamp.svg_name, stamp.x, stamp.y, stamp.size, image_height)
    tol = extra_tol
    return left - tol <= img_x <= right + tol and top - tol <= img_y <= bottom + tol
