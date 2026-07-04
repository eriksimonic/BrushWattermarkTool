from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from PIL import Image
from PIL.ExifTags import IFD, TAGS

SERIAL_EXIF_KEYS = ("BodySerialNumber", "CameraSerialNumber")
DATETIME_EXIF_KEYS = ("DateTimeOriginal", "DateTimeDigitized", "DateTime")


def _tag_name(tag_id: object) -> str:
    if isinstance(tag_id, str):
        return tag_id
    return str(TAGS.get(tag_id, tag_id))


def _merge_ifd(exif, ifd_id: int, merged: dict[str, object]) -> None:
    try:
        ifd = exif.get_ifd(ifd_id)
    except (KeyError, ValueError, TypeError):
        return
    for tag_id, value in ifd.items():
        merged[_tag_name(tag_id)] = value


def read_exif_map(image_path: Path) -> dict[str, object]:
    try:
        with Image.open(image_path) as opened:
            return read_exif_map_from_image(opened)
    except OSError:
        return {}


def read_exif_bytes(image_path: Path) -> bytes:
    try:
        with Image.open(image_path) as opened:
            exif = opened.getexif()
            return exif.tobytes() if exif else b""
    except (AttributeError, OSError, TypeError, ValueError):
        return b""


def read_exif_map_from_image(image: Image.Image) -> dict[str, object]:
    try:
        exif = image.getexif()
    except (AttributeError, OSError, TypeError):
        return {}
    if not exif:
        return {}

    merged: dict[str, object] = {}
    for tag_id, value in exif.items():
        merged[_tag_name(tag_id)] = value
    _merge_ifd(exif, IFD.Exif, merged)
    return merged


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore").strip("\x00").strip()
        except UnicodeDecodeError:
            return ""
    return str(value).strip()


def _first_value(exif: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _as_text(exif.get(key))
        if text:
            return text
    return ""


def _rational_to_float(value: object) -> float | None:
    if isinstance(value, tuple) and len(value) == 2:
        num, den = value
        if den == 0:
            return None
        return float(num) / float(den)
    if isinstance(value, Fraction):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_exposure(value: object) -> str:
    seconds = _rational_to_float(value)
    if seconds is None or seconds <= 0:
        return ""
    if seconds >= 1:
        rounded = round(seconds, 1)
        if rounded == int(rounded):
            return f"{int(rounded)}s"
        return f"{rounded:g}s"
    denom = max(1, round(1 / seconds))
    return f"1/{denom}s"


def format_fnumber(value: object) -> str:
    f_number = _rational_to_float(value)
    if f_number is None or f_number <= 0:
        return ""
    rounded = round(f_number, 1)
    if rounded == int(rounded):
        return f"f/{int(rounded)}"
    return f"f/{rounded:g}"


def format_focal_length(value: object) -> str:
    focal = _rational_to_float(value)
    if focal is None or focal <= 0:
        return ""
    rounded = round(focal, 1)
    if rounded == int(rounded):
        return f"{int(rounded)}mm"
    return f"{rounded:g}mm"


def format_exif_datetime(value: object) -> str:
    text = _as_text(value)
    if not text:
        return ""
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return text.replace(":", "-", 2)


def _display_name(text: str) -> str:
    if not text:
        return ""
    keep_tokens = {"EOS", "VR", "USM", "IS", "OSS", "OIS", "RF", "EF", "FE", "Z", "DX", "TC"}
    words = []
    for word in text.split():
        token = word.strip(".,;:")
        upper = token.upper()
        if upper in keep_tokens or (len(token) <= 2) or any(ch.isdigit() for ch in token):
            words.append(token if not token.isupper() or len(token) <= 2 else upper)
        elif token.isupper():
            words.append(token.capitalize())
        else:
            words.append(token)
    return " ".join(words)


def _normalize_make(make: str) -> str:
    text = make.strip().upper()
    for suffix in (" CORPORATION", " CORP.", " CORP", " INC.", " INC"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _short_camera_name(make: str, model: str) -> str:
    make = make.strip()
    model = model.strip()
    if not model:
        return _display_name(make)
    if not make:
        return _display_name(model)

    make_key = _normalize_make(make).split()[0] if make else ""
    model_upper = model.upper()
    if make_key and (model_upper.startswith(make_key) or make_key in model_upper):
        return _display_name(model)
    return _display_name(f"{make} {model}")


def _short_lens_name(lens: str) -> str:
    text = lens.strip()
    if not text:
        return ""

    tc_match = re.search(r"TC[- ]?([\d.]+)x", text, re.IGNORECASE)
    tc_suffix = f" TC-{tc_match.group(1)}x" if tc_match else ""

    core = re.search(r"(\d+(?:-\d+)?(?:\.\d+)?mm)\s*f/?([\d.]+)", text, re.IGNORECASE)
    if core:
        return f"{core.group(1)} f/{core.group(2)}{tc_suffix}"

    for prefix in (
        "NIKKOR Z ",
        "NIKKOR ",
        "RF ",
        "EF ",
        "FE ",
        "Z ",
        "DX ",
        "AF-S ",
    ):
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix) :]
            break

    for token in (" VR S", " VR", " IS USM", " IS", " OSS", " OIS", " USM"):
        if text.upper().endswith(token.upper()):
            text = text[: -len(token)]
            break

    text = re.sub(r"\s+", " ", text).strip()
    return _display_name(text)


def _first_datetime(exif: dict[str, object]) -> str:
    for key in DATETIME_EXIF_KEYS:
        formatted = format_exif_datetime(exif.get(key))
        if formatted:
            return formatted
    return ""


@dataclass(frozen=True)
class ImageMetadata:
    make: str = ""
    model: str = ""
    lens: str = ""
    serial: str = ""
    iso: str = ""
    aperture: str = ""
    shutter: str = ""
    focal_length: str = ""
    datetime_original: str = ""
    copyright: str = ""
    artist: str = ""

    @classmethod
    def from_exif(cls, exif: dict[str, object]) -> ImageMetadata:
        iso = _first_value(exif, ("ISOSpeedRatings", "PhotographicSensitivity", "ISO"))
        if not iso and exif.get("ISOSpeedRatings") not in (None, ""):
            iso = _as_text(exif.get("ISOSpeedRatings"))

        return cls(
            make=_as_text(exif.get("Make")),
            model=_as_text(exif.get("Model")),
            lens=_first_value(exif, ("LensModel",)),
            serial=_first_value(exif, SERIAL_EXIF_KEYS),
            iso=iso,
            aperture=format_fnumber(exif.get("FNumber")),
            shutter=format_exposure(exif.get("ExposureTime")),
            focal_length=format_focal_length(exif.get("FocalLength")),
            datetime_original=_first_datetime(exif),
            copyright=_as_text(exif.get("Copyright")),
            artist=_as_text(exif.get("Artist")),
        )

    @property
    def camera_line(self) -> str:
        camera = " ".join(part for part in (self.make, self.model) if part)
        if self.lens:
            return f"{camera} · {self.lens}" if camera else self.lens
        return camera

    @property
    def settings_line(self) -> str:
        parts = []
        if self.iso:
            parts.append(f"ISO {self.iso}")
        if self.aperture:
            parts.append(self.aperture)
        if self.shutter:
            parts.append(self.shutter)
        if self.focal_length:
            parts.append(self.focal_length)
        return " · ".join(parts)

    @property
    def info_line(self) -> str:
        parts = []
        if self.serial:
            parts.append(f"S/N {self.serial}")
        if self.datetime_original:
            parts.append(self.datetime_original)
        return " · ".join(parts)

    def _caption_camera(self) -> str:
        camera = _short_camera_name(self.make, self.model)
        lens = _short_lens_name(self.lens)
        if camera and lens:
            return f"{camera}, {lens}"
        return camera or lens

    def _caption_settings(self) -> str:
        parts: list[str] = []
        if self.aperture:
            parts.append(self.aperture.replace("f/", "ƒ/"))
        if self.shutter:
            shutter = self.shutter
            if shutter.endswith("s") and not shutter.endswith(" sec."):
                shutter = shutter[:-1] + " sec."
            parts.append(shutter)
        if self.iso:
            parts.append(f"ISO {self.iso}")
        if self.focal_length:
            mm = self.focal_length.replace("mm", " mm")
            parts.append(mm)
        return ", ".join(parts)

    def _caption_copy(self, additional_copy: str) -> str:
        copy = additional_copy.strip()
        if copy:
            return copy
        if self.copyright.strip():
            return self.copyright.strip()
        if self.artist.strip():
            return f"Photograph by {self.artist.strip()}"
        return ""

    def caption_line(self, additional_copy: str = "") -> str:
        """Single publication-style caption, Nat Geo inspired."""
        sections: list[str] = []

        camera = self._caption_camera()
        if camera:
            sections.append(camera)

        settings = self._caption_settings()
        if settings:
            sections.append(settings)

        if self.serial:
            sections.append(f"S/N {self.serial}")

        copy = self._caption_copy(additional_copy)
        if copy:
            sections.append(copy)

        if sections:
            return " — ".join(sections)
        return "Photograph metadata unavailable"

    def footer_lines(self, additional_copy: str = "") -> list[str]:
        return [self.caption_line(additional_copy)]


def read_image_metadata(image_path: Path) -> ImageMetadata:
    return ImageMetadata.from_exif(read_exif_map(image_path))
