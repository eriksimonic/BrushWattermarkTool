import os
import sys
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
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
        "Arial Bold": [
            r"C:\Windows\Fonts\arialbd.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "Segoe UI": [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Supplemental/Helvetica Neue.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
        "Verdana": [
            r"C:\Windows\Fonts\verdana.ttf",
            "/System/Library/Fonts/Supplemental/Verdana.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "Tahoma": [
            r"C:\Windows\Fonts\tahoma.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "Georgia": [
            r"C:\Windows\Fonts\georgia.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ],
        "DejaVu Sans": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ],
        "Helvetica Neue": [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Supplemental/Helvetica Neue.ttf",
        ],
        "Liberation Sans": [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
    }


def _scan_font_directories(font_name: str) -> Optional[str]:
    normalized = font_name.lower().replace(" ", "")

    if sys.platform == "win32":
        win_fonts = Path(r"C:\Windows\Fonts")
        if win_fonts.exists():
            for item in win_fonts.glob("*.ttf"):
                if normalized in item.stem.lower().replace(" ", ""):
                    return str(item)
        return None

    search_dirs: list[Path] = []
    if sys.platform == "darwin":
        search_dirs.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
                Path("/Library/Fonts"),
                Path.home() / "Library/Fonts",
            ]
        )
    else:
        search_dirs.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".local/share/fonts",
                Path.home() / ".fonts",
            ]
        )

    extensions = (".ttf", ".otf", ".ttc")
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for item in directory.rglob("*"):
            if not item.is_file() or item.suffix.lower() not in extensions:
                continue
            stem = item.stem.lower().replace(" ", "").replace("-", "")
            if normalized in stem or stem in normalized:
                return str(item)
    return None


def find_font_path(font_name: str) -> Optional[str]:
    for path in font_candidates().get(font_name, []):
        if os.path.exists(path):
            return path
    return _scan_font_directories(font_name)


def available_font_names() -> list[str]:
    names = []
    for font_name in font_candidates():
        if find_font_path(font_name) is not None:
            names.append(font_name)
    return names or ["Arial"]


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
