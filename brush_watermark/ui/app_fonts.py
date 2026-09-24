"""Registers the bundled Geist fonts and exposes the resolved family names.

Falls back to system fonts if the bundled files are missing, so the UI still
renders (just not in Geist).
"""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
UI_FAMILY = "Geist"
MONO_FAMILY = "Geist Mono"
_FALLBACK_UI = "Segoe UI"
_FALLBACK_MONO = "Consolas"

_resolved = {"ui": _FALLBACK_UI, "mono": _FALLBACK_MONO}


def register_app_fonts() -> None:
    """Load every bundled TTF. Needs a QGuiApplication; safe to call more than once."""
    families: set[str] = set()
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id != -1:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    _resolved["ui"] = UI_FAMILY if UI_FAMILY in families else _FALLBACK_UI
    _resolved["mono"] = MONO_FAMILY if MONO_FAMILY in families else _FALLBACK_MONO


def ui_family() -> str:
    return _resolved["ui"]


def mono_family() -> str:
    return _resolved["mono"]


def ui_font(pixel_size: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(ui_family())
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def mono_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.Medium) -> QFont:
    font = QFont(mono_family())
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font
