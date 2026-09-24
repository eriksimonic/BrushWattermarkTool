from PySide6.QtGui import QFont, QFontDatabase

from brush_watermark.ui.app_fonts import mono_family, mono_font, ui_family, ui_font


def test_bundled_fonts_are_registered(qapp):
    assert ui_family() == "Geist"
    assert mono_family() == "Geist Mono"
    assert {"Regular", "Medium", "SemiBold"} <= set(QFontDatabase.styles("Geist"))


def test_font_helpers_use_pixel_sizes(qapp):
    font = mono_font(11)
    assert font.family() == "Geist Mono" and font.pixelSize() == 11
    assert font.weight() == QFont.Weight.Medium
    assert ui_font().pixelSize() == 13
