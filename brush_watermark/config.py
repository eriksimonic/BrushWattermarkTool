import json
import subprocess
import sys
from pathlib import Path

APP_NAME = "Lightroom Brush Watermark"
GITHUB_REPO = "eriksimonic/BrushWattermarkTool"
GITHUB_BRANCH = "main"
VERSION_RAW_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/VERSION"
)
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
GITHUB_API_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
UPDATE_ASSET_NAME = "BrushWatermark.zip"
UPDATE_ASSET_FILENAME = UPDATE_ASSET_NAME
USER_AGENT = "BrushWatermark"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}
CONFIG_DIR = Path.home() / ".lightroom_brush_watermark"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "watermark_text": "Erik Simonič",
    "opacity": 22,
    "font_name": "Arial",
    "brush_size": 120,
    "angle_offset": 0,
    "mask_softness": 1,
    "text_color": "#ffffff",
    "auto_fit_text": True,
    "repeat_text": False,
    "repeat_spacing": 5,
    "blend_mode": "soft_light",
}


def load_settings() -> dict:
    settings = DEFAULT_SETTINGS.copy()
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                settings.update(saved)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def reveal_in_explorer(path: Path) -> None:
    resolved = path.resolve()
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(resolved)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(resolved)])
    else:
        subprocess.Popen(["xdg-open", str(resolved.parent)])
