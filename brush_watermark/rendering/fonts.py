import os
from pathlib import Path
from typing import Optional

from PIL import ImageFont

FONT_SIZE_RATIO = 0.52
TEXT_SPAN_FILL = 0.85


def font_candidates() -> dict[str, list[str]]:
    return {
        "Arial": [
            r"C:\Windows\Fonts\arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "Arial Bold": [
            r"C:\Windows\Fonts\arialbd.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "Segoe UI": [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ],
        "Verdana": [
            r"C:\Windows\Fonts\verdana.ttf",
            "/System/Library/Fonts/Supplemental/Verdana.ttf",
        ],
        "Tahoma": [r"C:\Windows\Fonts\tahoma.ttf"],
        "Georgia": [
            r"C:\Windows\Fonts\georgia.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf",
        ],
        "DejaVu Sans": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    }


def find_font_path(font_name: str) -> Optional[str]:
    for path in font_candidates().get(font_name, []):
        if os.path.exists(path):
            return path

    win_fonts = Path(r"C:\Windows\Fonts")
    if win_fonts.exists():
        normalized = font_name.lower().replace(" ", "")
        for item in win_fonts.glob("*.ttf"):
            if normalized in item.stem.lower().replace(" ", ""):
                return str(item)
    return None


def load_font(font_name: str, size: int):
    path = find_font_path(font_name)
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def font_size_from_brush(brush_size: int) -> int:
    from brush_watermark.geometry.points import clamp

    return int(clamp(round(brush_size * FONT_SIZE_RATIO), 10, 260))
