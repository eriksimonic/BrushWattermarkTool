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


def list_stamp_svgs() -> list[str]:
    directory = stamps_dir()
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.glob("*.svg") if path.is_file())


def reload_stamp_catalog() -> list[str]:
    """Rescan the stamps folder and clear cached SVG dimensions."""
    stamp_pixel_size.cache_clear()
    return list_stamp_svgs()


def stamp_svg_path(svg_name: str) -> Path:
    return stamps_dir() / svg_name


def _scaled_size(default_size: QSize, target_height: int) -> tuple[int, int]:
    height = max(1, int(target_height))
    if default_size.height() <= 0:
        return height, height
    aspect = default_size.width() / default_size.height()
    width = max(1, int(round(height * aspect)))
    return width, height


@lru_cache(maxsize=128)
def stamp_pixel_size(svg_name: str, target_height: int) -> tuple[int, int]:
    path = stamp_svg_path(svg_name)
    if not path.is_file():
        return max(1, target_height), max(1, target_height)
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return max(1, target_height), max(1, target_height)
    return _scaled_size(renderer.defaultSize(), target_height)


def stamp_bounds(svg_name: str, x: int, y: int, size: int) -> tuple[int, int, int, int]:
    """Return left, top, right, bottom in image coordinates (bottom-left anchor)."""
    width, height = stamp_pixel_size(svg_name, size)
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


def render_stamp_rgba(svg_name: str, target_height: int, tint_color: str | None = None) -> Image.Image:
    path = stamp_svg_path(svg_name)
    height = max(1, int(clamp(target_height, 1, 2000)))
    if not path.is_file():
        return Image.new("RGBA", (height, height), (0, 0, 0, 0))

    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return Image.new("RGBA", (height, height), (0, 0, 0, 0))

    width, height = _scaled_size(renderer.defaultSize(), height)
    qimage = QImage(width, height, QImage.Format.Format_ARGB32)
    qimage.fill(0)
    painter = QPainter(qimage)
    renderer.render(painter)
    painter.end()

    image = _qimage_to_pil(qimage)
    if tint_color:
        image = _apply_tint(image, tint_color)
    return image


def stamp_hit_test(stamp: Stamp, img_x: int, img_y: int, extra_tol: float = 0.0) -> bool:
    left, top, right, bottom = stamp_bounds(stamp.svg_name, stamp.x, stamp.y, stamp.size)
    tol = extra_tol
    return left - tol <= img_x <= right + tol and top - tol <= img_y <= bottom + tol
