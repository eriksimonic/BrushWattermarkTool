"""Enforces DESIGN.md: UI colors come from design_tokens.py only."""
import re
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent / "brush_watermark" / "ui"
# color_picker's "#ffffff" is the default *selected swatch value* (data), not a UI color.
ALLOWED = {"design_tokens.py": None, "color_picker.py": {"#ffffff"}}


def test_no_hard_coded_hex_colors_outside_tokens():
    offenders = []
    for path in sorted(UI_DIR.glob("*.py")):
        if path.name in ALLOWED and ALLOWED[path.name] is None:
            continue
        found = set(re.findall(r"#[0-9A-Fa-f]{6}\b", path.read_text(encoding="utf-8")))
        found -= ALLOWED.get(path.name) or set()
        if found:
            offenders.append(f"{path.name}: {sorted(found)}")
    assert offenders == []


def test_old_sidebar_modules_are_gone():
    assert not (UI_DIR / "sidebar.py").exists()
    assert not (UI_DIR / "lightroom_controls.py").exists()
