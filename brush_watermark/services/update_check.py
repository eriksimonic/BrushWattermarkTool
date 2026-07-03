import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from brush_watermark import __version__
from brush_watermark.config import RELEASES_URL, VERSION_RAW_URL


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str | None
    update_available: bool
    release_url: str
    check_failed: bool = False


def parse_version(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value.strip())
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts[:3])


def is_newer_version(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def fetch_remote_version(timeout: float = 8.0) -> str:
    request = urllib.request.Request(
        VERSION_RAW_URL,
        headers={"User-Agent": "BrushWatermark-UpdateCheck"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8").strip()
    if not text:
        raise ValueError("Empty version response")
    return text


def check_for_update(timeout: float = 8.0) -> UpdateCheckResult:
    current = __version__
    try:
        latest = fetch_remote_version(timeout)
    except (OSError, urllib.error.URLError, ValueError):
        return UpdateCheckResult(
            current_version=current,
            latest_version=None,
            update_available=False,
            release_url=RELEASES_URL,
            check_failed=True,
        )
    return UpdateCheckResult(
        current_version=current,
        latest_version=latest,
        update_available=is_newer_version(latest, current),
        release_url=RELEASES_URL,
    )
