import re
from datetime import datetime
from pathlib import Path

from brush_watermark.services.exif_metadata import (
    DATETIME_EXIF_KEYS,
    SERIAL_EXIF_KEYS,
    read_exif_map,
)

WATERMARKED_SUFFIX = "watermarked"
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize_filename_part(value: object, *, max_len: int = 64) -> str:
    text = str(value).strip()
    if not text:
        return ""
    text = _INVALID_FILENAME_CHARS.sub("_", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    return text[:max_len]


def _format_exif_datetime_for_filename(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            continue
    return _sanitize_filename_part(text.replace(":", "").replace(" ", "_"))


def _first_exif_value(exif: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = exif.get(key)
        if value is None:
            continue
        part = _sanitize_filename_part(value)
        if part:
            return part
    return ""


def _first_exif_datetime(exif: dict[str, object]) -> str:
    for key in DATETIME_EXIF_KEYS:
        value = exif.get(key)
        if value is None:
            continue
        part = _format_exif_datetime_for_filename(value)
        if part:
            return part
    return ""


def build_copy_basename(image_stem: str, exif: dict[str, object]) -> str:
    stem = _sanitize_filename_part(image_stem, max_len=120) or "image"
    serial = _first_exif_value(exif, SERIAL_EXIF_KEYS)
    dt_part = _first_exif_datetime(exif)

    parts = [stem]
    if serial:
        parts.append(serial)
    if dt_part:
        parts.append(dt_part)
    parts.append(WATERMARKED_SUFFIX)
    return "_".join(parts)


def build_watermarked_copy_path(image_path: Path) -> Path:
    """Build a unique export path: {stem}_{serial}_{datetime}_watermarked.jpg"""
    image_path = Path(image_path)
    exif = read_exif_map(image_path)
    base_name = build_copy_basename(image_path.stem, exif)
    parent = image_path.parent
    suffix = image_path.suffix.lower() if image_path.suffix else ".jpg"
    if suffix not in {".jpg", ".jpeg"}:
        suffix = ".jpg"

    candidate = parent / f"{base_name}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = parent / f"{base_name}_{counter}{suffix}"
        counter += 1
    return candidate
