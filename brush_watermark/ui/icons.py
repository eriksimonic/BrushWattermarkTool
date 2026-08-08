"""Loads Lucide SVG icons, recolors them, and rasterizes them into QIcons.

Icons are shipped with `stroke="currentColor"` (see assets/icons/); we
substitute that placeholder for a real hex color at render time instead of
vendoring separate colored variants per state.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from brush_watermark.ui.design_tokens import TEXT

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

_SVG_CACHE: dict[str, str] = {}
_PIXMAP_CACHE: dict[tuple[str, int, str], QPixmap] = {}
_ICON_CACHE: dict[tuple[str, int, str], QIcon] = {}

_SUPERSAMPLE = 2


def _recolor_svg(svg_text: str, color: str) -> str:
    """Pure string transform — swaps the currentColor placeholder for a real color."""
    return svg_text.replace('stroke="currentColor"', f'stroke="{color}"')


def _load_svg_text(name: str) -> str:
    if name not in _SVG_CACHE:
        path = ICONS_DIR / f"{name}.svg"
        _SVG_CACHE[name] = path.read_text(encoding="utf-8")
    return _SVG_CACHE[name]


def get_pixmap(name: str, size: int = 16, color: str = TEXT) -> QPixmap:
    """Rasterize icon `name` at `size` px (logical) in `color`, cached."""
    key = (name, size, color)
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]

    svg_text = _recolor_svg(_load_svg_text(name), color)
    renderer = QSvgRenderer(svg_text.encode("utf-8"))

    device_size = size * _SUPERSAMPLE
    pixmap = QPixmap(device_size, device_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(float(_SUPERSAMPLE))

    _PIXMAP_CACHE[key] = pixmap
    return pixmap


def get_icon(name: str, size: int = 16, color: str = TEXT) -> QIcon:
    """QIcon version of get_pixmap, cached."""
    key = (name, size, color)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    icon = QIcon(get_pixmap(name, size, color))
    _ICON_CACHE[key] = icon
    return icon


def get_icon_checkable(name: str, size: int, off_color: str, on_color: str) -> QIcon:
    """QIcon with distinct pixmaps for the unchecked (Off) and checked (On) states."""
    icon = QIcon()
    icon.addPixmap(get_pixmap(name, size, off_color), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(get_pixmap(name, size, on_color), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def icon_size(size: int) -> QSize:
    return QSize(size, size)
