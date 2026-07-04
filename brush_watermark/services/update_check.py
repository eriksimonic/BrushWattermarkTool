import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from brush_watermark import __version__
from brush_watermark.config import (
    GITHUB_API_LATEST_RELEASE_URL,
    RELEASES_URL,
    USER_AGENT,
    VERSION_RAW_URL,
    update_asset_name,
)


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str | None
    update_available: bool
    release_url: str
    download_url: str | None = None
    check_failed: bool = False


def parse_version(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value.strip())
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts[:3])


def is_newer_version(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def _github_request(url: str, timeout: float) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )


def fetch_remote_version(timeout: float = 8.0) -> str:
    request = urllib.request.Request(
        VERSION_RAW_URL,
        headers={"User-Agent": f"{USER_AGENT}-UpdateCheck"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8").strip()
    if not text:
        raise ValueError("Empty version response")
    return text


def parse_release_payload(payload: dict) -> tuple[str, str | None]:
    tag_name = str(payload.get("tag_name", "")).strip()
    version = tag_name.lstrip("vV")
    if not version:
        raise ValueError("Release is missing a version tag")

    download_url: str | None = None
    asset_name = update_asset_name()
    for asset in payload.get("assets", []):
        if not isinstance(asset, dict):
            continue
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            break
    return version, download_url


def fetch_latest_release(timeout: float = 8.0) -> tuple[str, str | None]:
    with urllib.request.urlopen(
        _github_request(GITHUB_API_LATEST_RELEASE_URL, timeout),
        timeout=timeout,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid release response")
    return parse_release_payload(payload)


def check_for_update(timeout: float = 8.0) -> UpdateCheckResult:
    current = __version__
    try:
        latest, download_url = fetch_latest_release(timeout)
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
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
        download_url = None

    return UpdateCheckResult(
        current_version=current,
        latest_version=latest,
        update_available=is_newer_version(latest, current),
        release_url=RELEASES_URL,
        download_url=download_url,
    )
