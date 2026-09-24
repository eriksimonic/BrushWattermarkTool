# UI Redesign ("modern dark") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the PySide6 window to match the "Editor — modern dark" design. The new layout has a top bar, tool rail, canvas with floating panels, filmstrip, inspector and footer. It covers every feature the app already has, plus a per-layer eye toggle.

**Architecture:** Keep all editing/rendering logic in `MainWindow`, `CanvasWidget` and `Document`. Replace the single `SidebarPanel` with focused widgets (`TopBar`, `ToolRail`, `InspectorPanel`, `CanvasArea` overlays, `FilmstripWidget`, `StatusFooter`) that talk to `MainWindow` through Qt signals, as today. Styling comes from new `design_tokens.py` values, a rewritten `styles.py`, a new `controls.py` (painted/QSS controls) and bundled Geist fonts.

**Tech Stack:** Python 3.13, PySide6 (Qt 6), Pillow, pytest. Qt tests run offscreen (`QT_QPA_PLATFORM=offscreen`) and use `PySide6.QtTest.QTest`.

**Spec:** `docs/superpowers/specs/2026-09-24-ui-redesign-design.md`. Read it first; it holds the layout diagram and the colour table.

## Global Constraints

- Work on a branch `ui-redesign` (`git switch -c ui-redesign` before Task 1). Commit after every task. **Never push**: pushing `.py` changes to `main` triggers an automatic release (see `CLAUDE.md`).
- Run tests with `.venv/Scripts/python.exe -m pytest -q` from the repo root (Windows venv). The whole suite must pass at the end of every task.
- Every UI colour comes from `brush_watermark/ui/design_tokens.py`. No hex literals in any other `brush_watermark/ui/*.py` file (Task 10 adds a test that enforces this). Per-image data colours (swatches, stroke colours) are data, not literals, and are fine.
- Only existing features. Design controls that need a missing feature are left out and listed in `docs/TODO-ui.md` (Task 11):
  - undo/redo
  - Pan/Zoom tools
  - zoom −/+ and an editable zoom %
  - colour picker that samples the image
  - Add images
  - prev/next image buttons and Ctrl+←/→
  - copy serial
  - Edit menu
  - Ctrl+S
  - Del to delete a layer
- In-scope addition: the layer eye toggle sets the existing `Stroke.visible`.
- `QPushButton`/`QAction` text treats `&` as a mnemonic, so write a literal ampersand as `&&` (`"Save && close"`).
- Match the codebase style: `from __future__` isn't used, type hints use `X | None`, signal-to-slot lambdas take and ignore Qt's `checked` arg (`lambda _checked=False: ...`).
- Keep LF line endings.

## File map

| File | Status | Responsibility |
|---|---|---|
| `brush_watermark/ui/design_tokens.py` | rewrite | New palette + `rgba()` helper (legacy aliases until Task 10) |
| `brush_watermark/ui/app_fonts.py` | new | Register bundled Geist fonts; `ui_family()`, `mono_family()`, `ui_font()`, `mono_font()` |
| `brush_watermark/assets/fonts/*` | new | Geist + Geist Mono TTFs, `OFL.txt` |
| `brush_watermark/assets/icons/{eye,eye-off,keyboard,images,type,minus,plus}.svg` | new | Extra Lucide icons |
| `brush_watermark/ui/controls.py` | new | `make_menu`, `ToggleSwitch`, `SwitchRow`, `AccentSlider`, `SliderRow`, `SegmentedControl`, `Chip`, `KeyBadge`, `KeyCombo`, `KeyHint`, `Stepper`, `SplitButton`, `CollapsibleSection` |
| `brush_watermark/ui/styles.py` | rewrite | Global QSS for the new look |
| `brush_watermark/ui/layer_list.py` | new | `LayerItem`, `LayerList` (rows with eye toggle) |
| `brush_watermark/services/document.py` | modify | `set_stroke_visible`, `stroke_meta_text`; drop `stroke_list_text` (Task 10) |
| `brush_watermark/ui/color_picker.py` | modify | Swatches restyled via QSS object name |
| `brush_watermark/ui/inspector.py` | new | `InspectorPanel` (replaces `SidebarPanel`) |
| `brush_watermark/ui/top_bar.py` | new | `TopBar` |
| `brush_watermark/ui/tool_rail.py` | new | `ToolRail`, `RailButton`, `ShortcutsPopup` |
| `brush_watermark/ui/status_footer.py` | new | `StatusFooter` |
| `brush_watermark/ui/canvas_overlays.py` | new | `tool_hint`, `HintPill`, `ZoomPill`, `BrushReadout`, `CanvasArea` |
| `brush_watermark/ui/canvas.py` | modify | Dotted background tile, restyled anchor handles |
| `brush_watermark/ui/filmstrip.py` | rewrite | New filmstrip look (badges, title column) |
| `brush_watermark/ui/main_window.py` | modify | Compose the new widgets, rewire signals |
| `brush_watermark/ui/sidebar.py`, `brush_watermark/ui/lightroom_controls.py` | delete | Replaced |
| `brush_watermark/main.py` | modify | Register fonts, set app font |
| `BrushWatermark.spec` | modify | Bundle `assets/fonts` |
| `tests/conftest.py` | new | Offscreen `qapp` fixture |
| `tests/test_*.py` | new/modify | Per-task tests (named in each task) |
| `brush_watermark/ui/DESIGN.md`, `CLAUDE.md`, `README.md`, `docs/TODO-ui.md` | modify/new | Docs |

---

### Task 1: Foundations — tokens, fonts, icons, Qt test fixture

**Files:**
- Rewrite: `brush_watermark/ui/design_tokens.py`
- Create: `brush_watermark/ui/app_fonts.py`, `brush_watermark/assets/fonts/` (5 TTFs + `OFL.txt`), 7 icon SVGs, `tests/conftest.py`, `tests/test_design_tokens.py`, `tests/test_app_fonts.py`
- Modify: `brush_watermark/main.py`, `BrushWatermark.spec`, `tests/test_icons.py`

**Interfaces:**
- Produces:
  - token constants (names below)
  - `rgba(hex_color: str, alpha: float) -> str`
  - `register_app_fonts() -> None`
  - `ui_family() -> str`, `mono_family() -> str`
  - `ui_font(pixel_size: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont`
  - `mono_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.Medium) -> QFont`
  - pytest fixture `qapp`

- [ ] **Step 1: Create the branch**

```bash
git switch -c ui-redesign
```

- [ ] **Step 2: Download fonts and icons**

```bash
mkdir -p brush_watermark/assets/fonts
base=https://raw.githubusercontent.com/vercel/geist-font/v1.7.2
for f in Geist/ttf/Geist-Regular Geist/ttf/Geist-Medium Geist/ttf/Geist-SemiBold GeistMono/ttf/GeistMono-Regular GeistMono/ttf/GeistMono-Medium; do
  curl -fsSL "$base/fonts/$f.ttf" -o "brush_watermark/assets/fonts/$(basename $f).ttf"
done
curl -fsSL "$base/OFL.txt" -o brush_watermark/assets/fonts/OFL.txt
for n in eye eye-off keyboard images type minus plus; do
  curl -fsSL "https://cdn.jsdelivr.net/npm/lucide-static@1.30.0/icons/$n.svg" -o "brush_watermark/assets/icons/$n.svg"
done
ls brush_watermark/assets/fonts && grep -L 'stroke="currentColor"' brush_watermark/assets/icons/{eye,eye-off,keyboard,images,type,minus,plus}.svg
```

Expected: five `.ttf` files plus `OFL.txt` are listed, and the `grep -L` line prints nothing (every icon uses `currentColor`).

- [ ] **Step 3: Write the failing tests**

`tests/conftest.py`:

```python
"""Shared fixtures. Qt widgets are tested offscreen (no window server needed)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    from brush_watermark.ui.app_fonts import register_app_fonts

    app = QApplication.instance() or QApplication([])
    register_app_fonts()
    return app
```

`tests/test_design_tokens.py`:

```python
import re

import brush_watermark.ui.design_tokens as tokens
from brush_watermark.ui.design_tokens import rgba


def _token_values():
    return {
        name: value
        for name, value in vars(tokens).items()
        if name.isupper() and isinstance(value, str)
    }


def test_every_token_is_a_six_digit_hex():
    for name, value in _token_values().items():
        assert re.fullmatch(r"#[0-9A-F]{6}", value), name


def test_rgba_formats_qss_color():
    assert rgba("#5B8CFF", 0.16) == "rgba(91, 140, 255, 0.16)"
    assert rgba("#FFFFFF", 1) == "rgba(255, 255, 255, 1)"
```

`tests/test_app_fonts.py`:

```python
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
```

Append to `tests/test_icons.py`:

```python
from brush_watermark.ui.icons import ICONS_DIR

REDESIGN_ICONS = ("eye", "eye-off", "keyboard", "images", "type", "minus", "plus")


class TestRedesignIcons:
    def test_icons_are_bundled_and_recolorable(self):
        for name in REDESIGN_ICONS:
            text = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
            assert 'stroke="currentColor"' in text, name
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_design_tokens.py tests/test_app_fonts.py tests/test_icons.py`
Expected: FAIL. `rgba` and `brush_watermark.ui.app_fonts` can't be imported. The icon test passes, since Step 2 already added the files.

- [ ] **Step 5: Rewrite `brush_watermark/ui/design_tokens.py`**

```python
"""Design tokens for the "modern dark" editor UI.

Every UI color lives here; widgets import tokens and never hard-code hex
values (see ui/DESIGN.md). Accent colors are for interactive/active
affordances only: primary buttons, checked controls, slider fill, focus rings.
"""

# Surfaces
CANVAS_BG = "#0E0F11"
CANVAS_DOT = "#1C1E22"
CHROME = "#17181B"
FOOTER_BG = "#131416"
SURFACE_INPUT = "#1F2125"
SURFACE_RAISED = "#23252A"
SURFACE_RAISED_HOVER = "#2A2D33"
SURFACE_MENU = "#1D1F23"
SURFACE_SEGMENT = "#111214"
SURFACE_SEGMENT_ON = "#2E3137"

# Lines
BORDER = "#2C2F35"
BORDER_STRONG = "#33363C"
BORDER_HOVER = "#44474E"
DIVIDER = "#25272C"
KEY_BADGE_BORDER = "#34373D"
SWITCH_OFF = "#3A3D44"

# Text and icons
TEXT = "#ECEDEF"
TEXT_BODY = "#D5D7DB"
TEXT_SECONDARY = "#B4B7BE"
TEXT_LABEL = "#A1A4AB"
TEXT_MUTED = "#80848C"
TEXT_FAINT = "#4A4E55"
ICON_DISABLED = "#6E727A"

# Accent
ACCENT = "#3563E9"
ACCENT_HOVER = "#2C56D4"
ACCENT_BRIGHT = "#5B8CFF"
ACCENT_TEXT = "#9DBBFF"
ON_ACCENT = "#FFFFFF"
SLIDER_THUMB = "#FFFFFF"

# Status
WARNING = "#E0B25C"
SUCCESS = "#4CC38A"
DANGER_TEXT = "#F2A7A0"
SHADOW = "#000000"

# Canvas overlay colors (brush cursor, guides, anchor handles), drawn on top
# of photos, so they are chosen for contrast rather than to match the chrome.
HANDLE = "#C8C8C8"
ANCHOR_FILL = "#FFFFFF"
CANVAS_DRAWING = "#FACC15"
CANVAS_SPAN_START = "#22C55E"
CANVAS_SPAN_TRACK = "#86EFAC"
CANVAS_SPAN_END = "#F59E0B"
CANVAS_ERASER = "#F87171"
CANVAS_ANCHOR_OUTLINE = "#000000"

# Legacy names still imported by pre-redesign widgets; removed in Task 10.
PANEL = CHROME
INPUT = SURFACE_INPUT
BUTTON_HOVER = SURFACE_RAISED_HOVER
ACCENT_PRESSED = ACCENT_HOVER
SELECTION = SURFACE_RAISED_HOVER
SELECTION_BORDER = BORDER_HOVER
LINK = ACCENT_TEXT
SLIDER_HANDLE = SLIDER_THUMB
TRACK = BORDER_STRONG


def rgba(hex_color: str, alpha: float) -> str:
    """QSS ``rgba()`` string for a token at the given opacity (0–1)."""
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:g})"
```

- [ ] **Step 6: Create `brush_watermark/ui/app_fonts.py`**

```python
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
```

- [ ] **Step 7: Register fonts at startup and bundle them**

In `brush_watermark/main.py`, add the import next to the other `brush_watermark` imports:

```python
from brush_watermark.ui.app_fonts import register_app_fonts, ui_font
```

and in `main()` directly after `app.setWindowIcon(load_app_icon())`:

```python
    register_app_fonts()
    app.setFont(ui_font())
```

In `BrushWatermark.spec`, add to the `datas=[...]` list after the `icons` entry:

```python
        ("brush_watermark/assets/fonts", "brush_watermark/assets/fonts"),
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass (the old UI still imports the legacy token names, which are aliased).

- [ ] **Step 9: Commit**

```bash
git add brush_watermark/ui/design_tokens.py brush_watermark/ui/app_fonts.py brush_watermark/assets/fonts brush_watermark/assets/icons brush_watermark/main.py BrushWatermark.spec tests/conftest.py tests/test_design_tokens.py tests/test_app_fonts.py tests/test_icons.py
git commit -m "Add redesign tokens, bundled Geist fonts and extra icons"
```

---

### Task 2: Custom controls (`controls.py`)

**Files:**
- Create: `brush_watermark/ui/controls.py`, `tests/test_controls.py`

**Interfaces:**
- Consumes: tokens, `get_icon`/`get_icon_checkable`/`get_pixmap` (`ui/icons.py`)
- Produces, all in `brush_watermark.ui.controls`:
  - `make_menu(parent) -> QMenu`
  - `ToggleSwitch(QAbstractButton)`
  - `SwitchRow(text, checked=False, *, switch_first=False)`: `.label`, `.switch`, `toggled(bool)`, `isChecked()`, `setChecked(bool)`
  - `AccentSlider(QSlider)`: `dragStarted`, `dragEnded`, `value_to_x(int) -> float`, `x_to_value(float) -> int`
  - `SliderRow(name, low, high, value)`: `.slider`, `.name_label`, `.value_label`, `set_value_text(str)`, `add_header_widget(QWidget)`
  - `SegmentedControl(labels)`: `currentChanged(int)`, `currentIndex()`, `setCurrentIndex(int)`
  - `Chip(text, icon_name=None)`: checkable `QPushButton`
  - `KeyBadge(text)`, `KeyCombo(keys)`, `KeyHint(keys, text, text_object_name="HintText")`
  - `Stepper(low, high, value, prefix="")`: `valueChanged(int)`, `value()`, `setValue(int)`
  - `SplitButton(text, icon_name=None)`: `.main`, `.arrow`, `.menu`, `clicked()`
  - `CollapsibleSection(title, icon_name=None, expanded=True)`: `.body_layout`, `toggled(bool)`, `set_title(str)`, `add_header_widget(QWidget)`, `is_expanded()`

- [ ] **Step 1: Write the failing tests** (`tests/test_controls.py`)

```python
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from brush_watermark.ui.controls import (
    AccentSlider,
    Chip,
    CollapsibleSection,
    KeyCombo,
    SegmentedControl,
    SliderRow,
    SplitButton,
    Stepper,
    SwitchRow,
    ToggleSwitch,
)


def test_toggle_switch_click_toggles(qapp):
    switch = ToggleSwitch()
    switch.show()
    seen = []
    switch.toggled.connect(seen.append)
    QTest.mouseClick(switch, Qt.MouseButton.LeftButton)
    assert switch.isChecked() and seen == [True]


def test_switch_row_label_click_toggles_and_forwards(qapp):
    row = SwitchRow("Auto-fit text to stroke")
    row.show()
    seen = []
    row.toggled.connect(seen.append)
    QTest.mouseClick(row.label, Qt.MouseButton.LeftButton)
    assert row.isChecked() is True and seen == [True]


def test_switch_row_blocked_signals_do_not_forward(qapp):
    row = SwitchRow("Repeat along stroke")
    seen = []
    row.toggled.connect(seen.append)
    row.blockSignals(True)
    row.setChecked(True)
    row.blockSignals(False)
    assert row.isChecked() and seen == []


def test_stepper_clamps_and_emits_only_changes(qapp):
    stepper = Stepper(0, 2, 1, prefix="gap")
    seen = []
    stepper.valueChanged.connect(seen.append)
    stepper.setValue(5)
    stepper.setValue(2)
    stepper.setValue(-3)
    assert seen == [2, 0] and stepper.value() == 0
    assert stepper._label.text() == "gap 0"
    assert not stepper._minus.isEnabled() and stepper._plus.isEnabled()


def test_segmented_control_emits_index(qapp):
    control = SegmentedControl(["Original", "Watermarked"])
    seen = []
    control.currentChanged.connect(seen.append)
    control.setCurrentIndex(1)
    assert control.currentIndex() == 1 and seen == [1]


def test_accent_slider_maps_positions_to_values(qapp):
    slider = AccentSlider()
    slider.setRange(0, 100)
    slider.resize(216, 20)
    for value in (0, 25, 50, 100):
        assert slider.x_to_value(slider.value_to_x(value)) == value
    assert slider.x_to_value(-50) == 0
    assert slider.x_to_value(10_000) == 100


def test_slider_row_header_widget_sits_before_value(qapp):
    row = SliderRow("Strength", 1, 100, 50)
    chip = Chip("Auto")
    row.add_header_widget(chip)
    assert row._header.indexOf(chip) == row._header.indexOf(row.value_label) - 1


def test_collapsible_section_toggles_body(qapp):
    section = CollapsibleSection("Brush", icon_name="paintbrush")
    seen = []
    section.toggled.connect(seen.append)
    section._toggle()
    assert section._body.isHidden() and seen == [False] and not section.is_expanded()
    section._toggle()
    assert not section._body.isHidden() and seen == [False, True]


def test_collapsible_section_can_start_collapsed(qapp):
    section = CollapsibleSection("Export", icon_name="image", expanded=False)
    assert section._body.isHidden()


def test_split_button_main_click_emits(qapp):
    button = SplitButton("Save && close", "save")
    seen = []
    button.clicked.connect(lambda: seen.append(True))
    button.main.click()
    assert seen == [True]


def test_key_combo_splits_on_plus(qapp):
    combo = KeyCombo("Alt+Wheel")
    assert [label.text() for label in combo.findChildren(QLabel)] == ["Alt", "+", "Wheel"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_controls.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'brush_watermark.ui.controls'`

- [ ] **Step 3: Write `brush_watermark/ui/controls.py`**

```python
"""Shared custom controls for the redesigned UI (see ui/DESIGN.md).

Painted where QSS can't match the design (switch, slider); everything else is
a plain widget styled by object name in styles.py.
"""

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from brush_watermark.ui.design_tokens import (
    ACCENT,
    ACCENT_BRIGHT,
    ACCENT_TEXT,
    BORDER_STRONG,
    ON_ACCENT,
    SLIDER_THUMB,
    SWITCH_OFF,
    TEXT,
    TEXT_LABEL,
    TEXT_MUTED,
)
from brush_watermark.ui.icons import get_icon, get_icon_checkable, get_pixmap


def make_menu(parent: QWidget | None = None) -> QMenu:
    """QMenu that can show the stylesheet's rounded corners (frameless + translucent)."""
    menu = QMenu(parent)
    menu.setWindowFlags(
        menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu


class _ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)


class ToggleSwitch(QAbstractButton):
    """30×18 pill switch: grey track when off, accent track with the knob slid right when on."""

    WIDTH = 30
    HEIGHT = 18
    KNOB = 14

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def sizeHint(self) -> QSize:
        return QSize(self.WIDTH, self.HEIGHT)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ACCENT if self.isChecked() else SWITCH_OFF))
        radius = self.HEIGHT / 2
        painter.drawRoundedRect(QRectF(0, 0, self.WIDTH, self.HEIGHT), radius, radius)
        knob_x = 2 + (self.WIDTH - self.KNOB - 4 if self.isChecked() else 0)
        painter.setBrush(QColor(TEXT))
        painter.drawEllipse(QRectF(knob_x, 2, self.KNOB, self.KNOB))
        painter.end()


class SwitchRow(QWidget):
    """Label plus ToggleSwitch; clicking the label toggles too. Mirrors QCheckBox's API."""

    toggled = Signal(bool)

    def __init__(
        self,
        text: str,
        checked: bool = False,
        parent: QWidget | None = None,
        *,
        switch_first: bool = False,
    ):
        super().__init__(parent)
        self.label = _ClickableLabel(text)
        self.label.setObjectName("SwitchLabel")
        self.switch = ToggleSwitch()
        self.switch.setChecked(checked)
        self.switch.setAccessibleName(text)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        if switch_first:
            row.addWidget(self.switch)
            row.addWidget(self.label, 1)
        else:
            row.addWidget(self.label, 1)
            row.addWidget(self.switch)
        self.setFixedHeight(28)

        self.label.clicked.connect(self.switch.toggle)
        self.switch.toggled.connect(self.toggled.emit)

    def isChecked(self) -> bool:
        return self.switch.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.switch.setChecked(checked)


class AccentSlider(QSlider):
    """Horizontal slider: 4 px track, bright-accent fill, white thumb with an accent ring."""

    MARGIN_H = 10
    TRACK_HEIGHT = 4
    THUMB_RADIUS = 7
    RING = 3

    dragStarted = Signal()
    dragEnded = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _track(self) -> tuple[float, float]:
        return float(self.MARGIN_H), float(max(1, self.width() - 2 * self.MARGIN_H))

    def value_to_x(self, value: int) -> float:
        left, width = self._track()
        span = max(1, self.maximum() - self.minimum())
        return left + (value - self.minimum()) / span * width

    def x_to_value(self, x: float) -> int:
        left, width = self._track()
        ratio = max(0.0, min(1.0, (x - left) / width))
        return int(self.minimum() + round(ratio * (self.maximum() - self.minimum())))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            painter.setOpacity(0.35)
        left, width = self._track()
        mid_y = self.height() / 2
        track = QRectF(left, mid_y - self.TRACK_HEIGHT / 2, width, self.TRACK_HEIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BORDER_STRONG))
        painter.drawRoundedRect(track, 2, 2)

        thumb_x = self.value_to_x(self.value())
        painter.setBrush(QColor(ACCENT_BRIGHT))
        painter.drawRoundedRect(QRectF(left, track.y(), thumb_x - left, self.TRACK_HEIGHT), 2, 2)

        outer = self.THUMB_RADIUS + self.RING
        painter.setBrush(QColor(ACCENT))
        painter.drawEllipse(QRectF(thumb_x - outer, mid_y - outer, outer * 2, outer * 2))
        painter.setBrush(QColor(SLIDER_THUMB))
        r = self.THUMB_RADIUS
        painter.drawEllipse(QRectF(thumb_x - r, mid_y - r, r * 2, r * 2))
        painter.end()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        self.setValue(self.x_to_value(event.position().x()))
        self.dragStarted.emit()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.isEnabled() and event.buttons() & Qt.MouseButton.LeftButton:
            self.setValue(self.x_to_value(event.position().x()))
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.dragEnded.emit()


class SliderRow(QWidget):
    """Name left, value right (mono), full-width AccentSlider below."""

    def __init__(self, name: str, low: int, high: int, value: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("SliderName")
        self.value_label = QLabel()
        self.value_label.setObjectName("SliderValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._header = QHBoxLayout()
        self._header.setContentsMargins(0, 0, 0, 0)
        self._header.setSpacing(8)
        self._header.addWidget(self.name_label)
        self._header.addStretch(1)
        self._header.addWidget(self.value_label)

        self.slider = AccentSlider()
        self.slider.setRange(low, high)
        self.slider.setValue(value)
        self.slider.setAccessibleName(name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(self._header)
        layout.addWidget(self.slider)

    def set_value_text(self, text: str) -> None:
        self.value_label.setText(text)

    def add_header_widget(self, widget: QWidget) -> None:
        """Insert a widget (e.g. an Auto chip) just left of the value."""
        self._header.insertWidget(self._header.indexOf(self.value_label), widget)


class SegmentedControl(QFrame):
    """Exclusive pill of buttons, e.g. Original | Watermarked."""

    currentChanged = Signal(int)

    def __init__(self, labels: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SegmentedControl")
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for index, text in enumerate(labels):
            button = QPushButton(text)
            button.setObjectName("Segment")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._group.addButton(button, index)
            row.addWidget(button)
        self._group.button(0).setChecked(True)
        self._group.idToggled.connect(self._on_toggled)

    def _on_toggled(self, index: int, checked: bool) -> None:
        if checked:
            self.currentChanged.emit(index)

    def currentIndex(self) -> int:
        return self._group.checkedId()

    def setCurrentIndex(self, index: int) -> None:
        self._group.button(index).setChecked(True)


class Chip(QPushButton):
    """Small checkable pill (e.g. the Strength "Auto" toggle)."""

    def __init__(self, text: str, icon_name: str | None = None, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(get_icon_checkable(icon_name, 11, TEXT_LABEL, ACCENT_TEXT))
            self.setIconSize(QSize(11, 11))


class KeyBadge(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("KeyBadge")


class KeyCombo(QWidget):
    """``"Alt+Wheel"`` → [Alt] + [Wheel]."""

    def __init__(self, keys: str, parent: QWidget | None = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)
        for index, part in enumerate(keys.split("+")):
            if index:
                plus = QLabel("+")
                plus.setObjectName("HintText")
                row.addWidget(plus)
            row.addWidget(KeyBadge(part))


class KeyHint(QWidget):
    """Key badges followed by a short description, e.g. [Wheel] Strength."""

    def __init__(self, keys: str, text: str, text_object_name: str = "HintText", parent: QWidget | None = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(KeyCombo(keys))
        label = QLabel(text)
        label.setObjectName(text_object_name)
        row.addWidget(label)


class Stepper(QFrame):
    """[−] gap 5 [+] integer stepper."""

    valueChanged = Signal(int)

    def __init__(self, low: int, high: int, value: int, prefix: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Stepper")
        self._low, self._high, self._prefix = low, high, prefix
        self._value = max(low, min(high, int(value)))

        self._minus = QPushButton()
        self._plus = QPushButton()
        for button, icon, name in ((self._minus, "minus", "Decrease"), (self._plus, "plus", "Increase")):
            button.setObjectName("StepButton")
            button.setIcon(get_icon(icon, 12, TEXT_LABEL))
            button.setIconSize(QSize(12, 12))
            button.setFixedSize(26, 30)
            button.setAccessibleName(name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._label = QLabel()
        self._label.setObjectName("StepperValue")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setMinimumWidth(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._minus)
        row.addWidget(self._label)
        row.addWidget(self._plus)

        self._minus.clicked.connect(lambda _checked=False: self.setValue(self._value - 1))
        self._plus.clicked.connect(lambda _checked=False: self.setValue(self._value + 1))
        self._refresh()

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        value = max(self._low, min(self._high, int(value)))
        if value == self._value:
            self._refresh()
            return
        self._value = value
        self._refresh()
        self.valueChanged.emit(value)

    def _refresh(self) -> None:
        self._label.setText(f"{self._prefix} {self._value}".strip())
        self._minus.setEnabled(self._value > self._low)
        self._plus.setEnabled(self._value < self._high)


class SplitButton(QWidget):
    """Primary button with a chevron that opens a right-aligned menu."""

    clicked = Signal()

    def __init__(self, text: str, icon_name: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.main = QPushButton(text)
        self.main.setObjectName("SplitMain")
        if icon_name:
            self.main.setIcon(get_icon(icon_name, 15, ON_ACCENT))
            self.main.setIconSize(QSize(15, 15))
        self.arrow = QPushButton()
        self.arrow.setObjectName("SplitArrow")
        self.arrow.setIcon(get_icon("chevron-down", 14, ON_ACCENT))
        self.arrow.setIconSize(QSize(14, 14))
        self.arrow.setAccessibleName("More save options")
        self.arrow.setToolTip("More save options")
        self.menu = make_menu(self)
        self.menu.setObjectName("SaveMenu")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.main)
        row.addWidget(self.arrow)

        self.main.clicked.connect(lambda _checked=False: self.clicked.emit())
        self.arrow.clicked.connect(lambda _checked=False: self._show_menu())

    def _show_menu(self) -> None:
        size = self.menu.sizeHint()
        self.menu.popup(self.mapToGlobal(QPoint(self.width() - size.width(), self.height() + 6)))


class _HeaderRow(QWidget):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        event.accept()


class CollapsibleSection(QFrame):
    """Inspector section: accent icon, bold title, chevron at the right; click to collapse."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        icon_name: str | None = None,
        expanded: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("InspectorSection")
        self._expanded = expanded

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 4, 16, 14)
        outer.setSpacing(0)

        header = _HeaderRow()
        header.setFixedHeight(40)
        self._header_row = QHBoxLayout(header)
        self._header_row.setContentsMargins(0, 0, 0, 0)
        self._header_row.setSpacing(9)
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(get_pixmap(icon_name, 16, ACCENT_TEXT))
            self._header_row.addWidget(icon_label)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("SectionTitle")
        self._header_row.addWidget(self._title_label)
        self._header_row.addStretch(1)
        self._chevron = QLabel()
        self._header_row.addWidget(self._chevron)
        header.clicked.connect(self._toggle)
        outer.addWidget(header)

        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)
        outer.addWidget(self._body)

        self._body.setVisible(self._expanded)
        self._update_chevron()

    def add_header_widget(self, widget: QWidget) -> None:
        """Insert a widget (e.g. a count badge) right after the title."""
        self._header_row.insertWidget(self._header_row.indexOf(self._title_label) + 1, widget)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._update_chevron()
        self.toggled.emit(self._expanded)

    def _update_chevron(self) -> None:
        name = "chevron-down" if self._expanded else "chevron-right"
        self._chevron.setPixmap(get_pixmap(name, 15, TEXT_MUTED))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_controls.py`
Expected: PASS (11 tests).

- [ ] **Step 5: Run the full suite, then commit**

Run: `.venv/Scripts/python.exe -m pytest -q` → all pass.

```bash
git add brush_watermark/ui/controls.py tests/test_controls.py
git commit -m "Add custom controls for the UI redesign"
```

---

### Task 3: Global stylesheet (`styles.py`)

**Files:**
- Rewrite: `brush_watermark/ui/styles.py`
- Create: `tests/test_styles.py`

**Interfaces:**
- Consumes: tokens + `rgba`, `ui_family()`/`mono_family()`, `ICONS_DIR`
- Produces: `app_stylesheet() -> str`. It styles these object names: `AppRoot`, `TopBar`, `ToolRail`, `InspectorScroll`, `InspectorPanel`, `InspectorSection`, `StatusFooter`, `Filmstrip`, `FilmstripScroll`, `CanvasScrollArea`, `FloatingPanel`, `PopupPanel`, `TopDivider`, `RailDivider`, `FooterDivider`, `PillDivider`, `LogoMark`, `FileName`, `SerialChip`, `CountBadge`, `UnsavedDot`, `UnsavedLabel`, `SectionTitle`, `SliderName`, `FieldLabel`, `SliderValue`, `SwitchLabel`, `HintLabel`, `HintTool`, `HintText`, `ValueChip`, `KeyBadge`, `FooterText`, `ZoomPercent`, `ReadoutText`, `ReadoutSlash`, `FilmstripTitle`, `LayerRow`, `LayerName`, `LayerMeta`, `LayerIcon`, `LayerEye`, `SecondaryButton`, `DangerButton`, `GhostButton`, `PrimaryButton`, `SplitMain`, `SplitArrow`, `MenuButton`, `Segment`, `SegmentedControl`, `Chip`, `Stepper`, `StepButton`, `StepperValue`, `PillButton`, `PillButtonMono`, `FooterUpdateButton`, `Swatch`, `RailButton`

- [ ] **Step 1: Write the failing test** (`tests/test_styles.py`)

```python
import re

import brush_watermark.ui.design_tokens as tokens
from brush_watermark.ui.app_fonts import mono_family, ui_family
from brush_watermark.ui.styles import app_stylesheet


def test_stylesheet_only_uses_token_colors(qapp):
    token_hexes = {
        value.upper()
        for name, value in vars(tokens).items()
        if name.isupper() and isinstance(value, str)
    }
    used = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", app_stylesheet())}
    assert used <= token_hexes


def test_stylesheet_uses_bundled_fonts(qapp):
    css = app_stylesheet()
    assert f"font-family: '{ui_family()}'" in css
    assert f"font-family: '{mono_family()}'" in css


def test_stylesheet_styles_new_areas(qapp):
    css = app_stylesheet()
    for name in ("TopBar", "ToolRail", "InspectorPanel", "StatusFooter", "FloatingPanel", "RailButton", "LayerRow"):
        assert f"#{name}" in css, name
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_styles.py`
Expected: FAIL. The last two tests fail: there's no Geist font family and no `#TopBar` in the current stylesheet.

- [ ] **Step 3: Rewrite `brush_watermark/ui/styles.py`**

```python
from brush_watermark.ui.app_fonts import mono_family, ui_family
from brush_watermark.ui.design_tokens import (
    ACCENT,
    ACCENT_BRIGHT,
    ACCENT_HOVER,
    ACCENT_TEXT,
    BORDER,
    BORDER_STRONG,
    CANVAS_BG,
    CHROME,
    DANGER_TEXT,
    DIVIDER,
    FOOTER_BG,
    KEY_BADGE_BORDER,
    ON_ACCENT,
    SURFACE_INPUT,
    SURFACE_MENU,
    SURFACE_RAISED,
    SURFACE_RAISED_HOVER,
    SURFACE_SEGMENT,
    SURFACE_SEGMENT_ON,
    TEXT,
    TEXT_BODY,
    TEXT_FAINT,
    TEXT_LABEL,
    TEXT_MUTED,
    TEXT_SECONDARY,
    WARNING,
    rgba,
)
from brush_watermark.ui.icons import ICONS_DIR

_CHEVRON_DOWN_PNG = (ICONS_DIR / "chevron-down-static.png").as_posix()


def app_stylesheet() -> str:
    ui = ui_family()
    mono = mono_family()
    accent_tint = rgba(ACCENT_BRIGHT, 0.16)
    return f"""
    QWidget {{ color: {TEXT}; font-family: '{ui}'; font-size: 13px; }}
    QMainWindow, QWidget#AppRoot {{ background: {CANVAS_BG}; }}
    QDialog, QMessageBox {{ background: {CHROME}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{
        background: {SURFACE_MENU}; color: {TEXT}; border: 1px solid {BORDER_STRONG};
        border-radius: 6px; padding: 4px 8px; font-size: 12px;
    }}

    /* ---- Areas ---- */
    QFrame#TopBar {{ background: {CHROME}; border: none; border-bottom: 1px solid {DIVIDER}; }}
    QFrame#ToolRail {{ background: {CHROME}; border: none; border-right: 1px solid {DIVIDER}; }}
    QScrollArea#InspectorScroll {{ background: {CHROME}; border: none; border-left: 1px solid {DIVIDER}; }}
    QScrollArea#InspectorScroll > QWidget#qt_scrollarea_viewport {{ background: {CHROME}; }}
    QFrame#InspectorPanel {{ background: {CHROME}; border: none; }}
    QFrame#InspectorSection {{ background: transparent; border: none; border-bottom: 1px solid {DIVIDER}; }}
    QFrame#StatusFooter {{ background: {FOOTER_BG}; border: none; border-top: 1px solid {DIVIDER}; }}
    QFrame#Filmstrip {{ background: {CHROME}; border: none; border-top: 1px solid {DIVIDER}; }}
    QScrollArea#FilmstripScroll, QScrollArea#FilmstripScroll > QWidget#qt_scrollarea_viewport {{
        background: transparent; border: none;
    }}
    QScrollArea#CanvasScrollArea, QScrollArea#CanvasScrollArea > QWidget#qt_scrollarea_viewport {{
        background: {CANVAS_BG}; border: none;
    }}
    QFrame#FloatingPanel {{ background: {rgba(CHROME, 0.92)}; border: 1px solid {BORDER}; border-radius: 10px; }}
    QFrame#PopupPanel {{ background: {SURFACE_MENU}; border: 1px solid {BORDER_STRONG}; border-radius: 10px; }}
    QFrame#TopDivider, QFrame#RailDivider, QFrame#FooterDivider, QFrame#PillDivider {{
        background: {BORDER}; border: none;
    }}

    /* ---- Text roles ---- */
    QLabel#LogoMark {{ background: {ACCENT}; border-radius: 8px; }}
    QLabel#FileName {{ font-weight: 500; }}
    QLabel#SerialChip {{
        font-family: '{mono}'; font-size: 11px; font-weight: 500; color: {TEXT_SECONDARY};
        border: 1px solid {BORDER}; border-radius: 6px; padding: 2px 7px;
    }}
    QLabel#CountBadge {{
        font-family: '{mono}'; font-size: 11px; font-weight: 500; color: {TEXT_LABEL};
        background: {SURFACE_RAISED}; border-radius: 5px; padding: 1px 6px;
    }}
    QLabel#UnsavedDot {{ background: {WARNING}; border-radius: 3px; }}
    QLabel#UnsavedLabel {{ color: {WARNING}; font-size: 11px; }}
    QLabel#SectionTitle {{ font-weight: 600; }}
    QLabel#SliderName, QLabel#FieldLabel {{ color: {TEXT_LABEL}; font-size: 12px; }}
    QLabel#SliderValue {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; }}
    QLabel#SwitchLabel {{ color: {TEXT_BODY}; }}
    QLabel#HintLabel {{ color: {TEXT_MUTED}; font-size: 11px; }}
    QLabel#HintLabel a, QLabel#FooterText a {{ color: {ACCENT_TEXT}; text-decoration: none; }}
    QLabel#HintTool {{ color: {ACCENT_TEXT}; font-size: 12px; font-weight: 600; }}
    QLabel#HintText {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
    QLabel#ValueChip {{
        font-family: '{mono}'; font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY};
        background: {SURFACE_INPUT}; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 0 10px; min-height: 32px; max-height: 32px;
    }}
    QLabel#KeyBadge {{
        font-family: '{mono}'; font-size: 11px; font-weight: 500; color: {TEXT_SECONDARY};
        background: {SURFACE_MENU}; border: 1px solid {KEY_BADGE_BORDER}; border-bottom-width: 2px;
        border-radius: 4px; padding: 0 5px;
    }}
    QLabel#FooterText {{ color: {TEXT_LABEL}; font-size: 11px; }}
    QLabel#ZoomPercent {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; }}
    QLabel#ReadoutText {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY}; }}
    QLabel#ReadoutSlash {{ font-family: '{mono}'; font-size: 12px; color: {TEXT_FAINT}; }}
    QLabel#FilmstripTitle {{ font-size: 12px; font-weight: 600; }}
    QLabel#LayerName {{ font-weight: 500; }}
    QLabel#LayerMeta {{ color: {TEXT_LABEL}; font-size: 11px; }}
    QLabel#LayerName[layerHidden="true"], QLabel#LayerMeta[layerHidden="true"] {{ color: {TEXT_FAINT}; }}
    QLabel#LayerIcon {{ background: {SURFACE_RAISED}; border-radius: 6px; }}
    QLabel#StepperValue {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; }}

    /* ---- Inputs ---- */
    QLineEdit, QComboBox {{
        background: {SURFACE_INPUT}; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 0 10px; min-height: 32px; max-height: 32px; color: {TEXT};
        selection-background-color: {ACCENT};
    }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT_BRIGHT}; }}
    QComboBox {{ padding-right: 30px; }}
    QComboBox::drop-down {{
        subcontrol-origin: padding; subcontrol-position: center right; width: 28px;
        border: none; background: transparent;
    }}
    QComboBox::down-arrow {{ width: 10px; height: 10px; image: url({_CHEVRON_DOWN_PNG}); }}
    QComboBox QAbstractItemView {{
        background: {SURFACE_MENU}; border: 1px solid {BORDER_STRONG}; padding: 4px; outline: none;
        selection-background-color: {SURFACE_RAISED_HOVER}; selection-color: {TEXT};
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        background: transparent; color: {TEXT}; border: 1px solid transparent; border-radius: 8px;
        padding: 0 12px; min-height: 30px; max-height: 30px; font-weight: 500;
    }}
    QPushButton:hover {{ background: {DIVIDER}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; }}
    QPushButton#SecondaryButton, QPushButton#DangerButton {{ background: {SURFACE_RAISED}; border-color: {BORDER_STRONG}; }}
    QPushButton#SecondaryButton:hover, QPushButton#DangerButton:hover {{ background: {SURFACE_RAISED_HOVER}; }}
    QPushButton#DangerButton {{ color: {DANGER_TEXT}; }}
    QPushButton#GhostButton {{ color: {TEXT_SECONDARY}; }}
    QPushButton#PrimaryButton, QPushButton#SplitMain, QPushButton#SplitArrow {{
        background: {ACCENT}; color: {ON_ACCENT}; border: none;
    }}
    QPushButton#PrimaryButton:hover, QPushButton#SplitMain:hover, QPushButton#SplitArrow:hover {{
        background: {ACCENT_HOVER};
    }}
    QPushButton#SplitMain {{ border-top-right-radius: 0; border-bottom-right-radius: 0; padding: 0 14px; }}
    QPushButton#SplitArrow {{
        border-top-left-radius: 0; border-bottom-left-radius: 0;
        border-left: 1px solid {rgba(ON_ACCENT, 0.22)}; padding: 0 8px;
    }}
    QPushButton#MenuButton {{
        color: {TEXT_SECONDARY}; border-radius: 6px; padding: 0 9px;
        min-height: 26px; max-height: 26px; font-weight: 400;
    }}
    QPushButton#MenuButton::menu-indicator {{ image: none; width: 0px; }}
    QFrame#SegmentedControl {{ background: {SURFACE_SEGMENT}; border: 1px solid {BORDER}; border-radius: 9px; }}
    QPushButton#Segment {{
        color: {TEXT_LABEL}; border: none; border-radius: 6px; padding: 0 12px;
        min-height: 26px; max-height: 26px; font-size: 12px;
    }}
    QPushButton#Segment:checked {{ background: {SURFACE_SEGMENT_ON}; color: {TEXT}; }}
    QPushButton#Chip {{
        color: {TEXT_LABEL}; border: 1px solid {BORDER_STRONG}; border-radius: 6px; padding: 0 8px;
        min-height: 22px; max-height: 22px; font-size: 11px;
    }}
    QPushButton#Chip:checked {{ background: {accent_tint}; border-color: {rgba(ACCENT_BRIGHT, 0.5)}; color: {ACCENT_TEXT}; }}
    QFrame#Stepper {{ background: {SURFACE_INPUT}; border: 1px solid {BORDER}; border-radius: 8px; }}
    QPushButton#StepButton {{ border: none; border-radius: 0; padding: 0; min-height: 28px; max-height: 28px; }}
    QPushButton#StepButton:hover {{ background: {SURFACE_RAISED_HOVER}; }}
    QPushButton#PillButton, QPushButton#PillButtonMono {{
        color: {TEXT_SECONDARY}; padding: 0 9px; min-height: 28px; max-height: 28px; font-size: 12px;
    }}
    QPushButton#PillButtonMono {{ font-family: '{mono}'; }}
    QPushButton#PillButton:checked, QPushButton#PillButtonMono:checked {{ background: {accent_tint}; color: {ACCENT_TEXT}; }}
    QPushButton#LayerEye {{ padding: 0; min-height: 28px; max-height: 28px; border-radius: 6px; }}
    QPushButton#FooterUpdateButton {{
        background: {ACCENT}; color: {ON_ACCENT}; border: none; border-radius: 5px;
        padding: 0 8px; min-height: 20px; max-height: 20px; font-size: 11px;
    }}
    QPushButton#Swatch {{
        border: 1px solid {rgba(ON_ACCENT, 0.14)}; border-radius: 6px; padding: 0;
        min-height: 22px; max-height: 22px; min-width: 22px; max-width: 22px;
    }}
    QPushButton#Swatch:checked {{ border: 2px solid {ACCENT_BRIGHT}; }}
    QToolButton#RailButton {{ background: transparent; border: 1px solid transparent; border-radius: 10px; }}
    QToolButton#RailButton:hover {{ background: {SURFACE_RAISED}; }}
    QToolButton#RailButton:checked {{ background: {accent_tint}; border-color: {rgba(ACCENT_BRIGHT, 0.45)}; }}

    /* ---- Layers ---- */
    QFrame#LayerRow {{ background: transparent; border: 1px solid transparent; border-radius: 8px; }}
    QFrame#LayerRow:hover {{ background: {SURFACE_INPUT}; }}
    QFrame#LayerRow[selected="true"] {{ background: {rgba(ACCENT_BRIGHT, 0.10)}; border-color: {rgba(ACCENT_BRIGHT, 0.40)}; }}

    /* ---- Menus ---- */
    QMenu {{ background: {SURFACE_MENU}; border: 1px solid {BORDER_STRONG}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 8px 14px; border-radius: 6px; color: {TEXT}; background: transparent; }}
    QMenu::item:selected {{ background: {SURFACE_RAISED_HOVER}; }}
    QMenu::item:disabled {{ color: {TEXT_MUTED}; }}
    QMenu::separator {{ height: 1px; background: {BORDER_STRONG}; margin: 4px 2px; }}
    QMenu#SaveMenu {{ min-width: 248px; }}

    /* ---- Scrollbars ---- */
    QScrollBar:vertical {{ width: 8px; background: transparent; margin: 0; }}
    QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 24px; }}
    QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass. (The old sidebar still works; it just looks different until Task 10 swaps it out.)

- [ ] **Step 5: Commit**

```bash
git add brush_watermark/ui/styles.py tests/test_styles.py
git commit -m "Rewrite the global stylesheet for the redesign"
```

---

### Task 4: Layer visibility and layer list

**Files:**
- Modify: `brush_watermark/services/document.py` (add two methods next to `stroke_list_text`)
- Create: `brush_watermark/ui/layer_list.py`, `tests/test_layer_list.py`
- Modify: `tests/test_document.py` (append)

**Interfaces:**
- Produces:
  - `Document.set_stroke_visible(index: int, visible: bool) -> None`: marks the doc dirty on a real change and ignores an out-of-range index.
  - `Document.stroke_meta_text(stroke: Stroke) -> str`: e.g. `"412 px · Soft light · 19%"`, with `" · repeat"` appended when repeating.
  - `LayerItem(name: str, meta: str, visible: bool)`: a frozen dataclass.
  - `LayerList`: signals `layer_clicked(int)` and `visibility_toggled(int)`; methods `set_layers(items: list[LayerItem], selected: int = -1)`, `set_selected(index: int)` and `rows() -> list`. Each row has `.eye` (QPushButton), `.name_label` and `.meta_label`, plus the property `"selected"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_document.py`:

```python
class TestStrokeVisibility:
    def test_set_stroke_visible_marks_dirty_on_change(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (10, 0)]))
        doc.dirty = False
        doc.set_stroke_visible(0, False)
        assert doc.strokes[0].visible is False and doc.dirty is True

    def test_set_stroke_visible_no_change_keeps_clean(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (10, 0)]))
        doc.dirty = False
        doc.set_stroke_visible(0, True)
        assert doc.dirty is False

    def test_set_stroke_visible_ignores_bad_index(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.set_stroke_visible(3, False)
        assert doc.strokes == []

    def test_stroke_meta_text(self, tmp_path):
        doc = _make_doc(tmp_path)
        stroke = _stroke([(0, 0), (100, 0)], opacity=19)
        stroke.blend_mode = "soft_light"
        assert doc.stroke_meta_text(stroke) == "100 px · Soft light · 19%"
        stroke.repeat_text = True
        assert doc.stroke_meta_text(stroke).endswith(" · repeat")
```

`tests/test_layer_list.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from brush_watermark.ui.layer_list import LayerItem, LayerList

ITEMS = [LayerItem("Stroke 1", "120 px · Normal · 30%", True), LayerItem("Stroke 2", "80 px · Overlay · 20%", False)]


def test_set_layers_builds_rows_and_selection(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS, selected=1)
    rows = layers.rows()
    assert [r.name_label.text() for r in rows] == ["Stroke 1", "Stroke 2"]
    assert rows[0].property("selected") is False and rows[1].property("selected") is True
    assert layers._empty.isHidden()


def test_hidden_layer_row_is_marked(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS)
    row = layers.rows()[1]
    assert row.name_label.property("layerHidden") is True
    assert row.eye.toolTip() == "Show layer"


def test_eye_click_emits_visibility_toggle(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS)
    seen = []
    layers.visibility_toggled.connect(seen.append)
    layers.rows()[1].eye.click()
    assert seen == [1]


def test_row_click_emits_layer_clicked(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS)
    layers.show()
    seen = []
    layers.layer_clicked.connect(seen.append)
    QTest.mouseClick(layers.rows()[0], Qt.MouseButton.LeftButton)
    assert seen == [0]


def test_empty_list_shows_hint(qapp):
    layers = LayerList()
    layers.set_layers([])
    assert not layers._empty.isHidden() and layers.rows() == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_document.py tests/test_layer_list.py`
Expected: FAIL (`set_stroke_visible` / `stroke_meta_text` / `layer_list` don't exist).

- [ ] **Step 3: Add the Document methods**

In `brush_watermark/services/document.py`, add `blend_mode_label` to the existing `rendering.blend` import:

```python
from brush_watermark.rendering.blend import blend_mode_label, blend_mode_short, composite_watermark_layer, normalize_blend_mode
```

Add these methods directly after `stroke_list_text`:

```python
    def stroke_meta_text(self, stroke: Stroke) -> str:
        """One-line layer summary for the inspector's layer list."""
        length = int(path_length(stroke.points))
        text = f"{length} px · {blend_mode_label(stroke.blend_mode)} · {stroke.opacity}%"
        if stroke.repeat_text:
            text += " · repeat"
        return text

    def set_stroke_visible(self, index: int, visible: bool) -> None:
        if not 0 <= index < len(self.strokes):
            return
        stroke = self.strokes[index]
        if stroke.visible == visible:
            return
        stroke.visible = visible
        self.dirty = True
```

- [ ] **Step 4: Create `brush_watermark/ui/layer_list.py`**

```python
"""Inspector layer rows: eye toggle, type icon, name and a one-line summary."""

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from brush_watermark.ui.design_tokens import ICON_DISABLED, TEXT_LABEL, TEXT_SECONDARY
from brush_watermark.ui.icons import get_icon, get_pixmap


@dataclass(frozen=True)
class LayerItem:
    name: str
    meta: str
    visible: bool


class _LayerRow(QFrame):
    clicked = Signal()
    eye_clicked = Signal()

    def __init__(self, item: LayerItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("LayerRow")
        self.setProperty("selected", False)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.eye = QPushButton()
        self.eye.setObjectName("LayerEye")
        self.eye.setFixedSize(28, 28)
        self.eye.setIconSize(QSize(15, 15))
        if item.visible:
            self.eye.setIcon(get_icon("eye", 15, TEXT_SECONDARY))
            tip = "Hide layer"
        else:
            self.eye.setIcon(get_icon("eye-off", 15, ICON_DISABLED))
            tip = "Show layer"
        self.eye.setToolTip(tip)
        self.eye.setAccessibleName(tip)

        tile = QLabel()
        tile.setObjectName("LayerIcon")
        tile.setFixedSize(30, 30)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setPixmap(get_pixmap("paintbrush", 15, TEXT_LABEL))

        self.name_label = QLabel(item.name)
        self.name_label.setObjectName("LayerName")
        self.meta_label = QLabel(item.meta)
        self.meta_label.setObjectName("LayerMeta")
        for label in (self.name_label, self.meta_label):
            label.setProperty("layerHidden", not item.visible)
        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(2)
        texts.addWidget(self.name_label)
        texts.addWidget(self.meta_label)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 0, 8, 0)
        row.setSpacing(6)
        row.addWidget(self.eye)
        row.addSpacing(4)
        row.addWidget(tile)
        row.addSpacing(4)
        row.addLayout(texts, 1)

        self.eye.clicked.connect(lambda _checked=False: self.eye_clicked.emit())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        if self.property("selected") == selected:
            return
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class LayerList(QWidget):
    layer_clicked = Signal(int)
    visibility_toggled = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._empty = QLabel("No layers yet — draw a stroke on the photo.")
        self._empty.setObjectName("HintLabel")
        self._layout.addWidget(self._empty)
        self._rows: list[_LayerRow] = []

    def rows(self) -> list[_LayerRow]:
        return list(self._rows)

    def set_layers(self, items: list[LayerItem], selected: int = -1) -> None:
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows = []
        for index, item in enumerate(items):
            row = _LayerRow(item)
            row.clicked.connect(lambda i=index: self.layer_clicked.emit(i))
            row.eye_clicked.connect(lambda i=index: self.visibility_toggled.emit(i))
            self._layout.addWidget(row)
            self._rows.append(row)
        self._empty.setVisible(not items)
        self.set_selected(selected)

    def set_selected(self, index: int) -> None:
        for i, row in enumerate(self._rows):
            row.set_selected(i == index)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add brush_watermark/services/document.py brush_watermark/ui/layer_list.py tests/test_document.py tests/test_layer_list.py
git commit -m "Add layer visibility toggle support and the layer list widget"
```

---

### Task 5: Inspector panel (replaces the sidebar's settings)

**Files:**
- Modify: `brush_watermark/ui/color_picker.py`
- Create: `brush_watermark/ui/inspector.py`, `tests/test_inspector.py`

**Interfaces:**
- Consumes:
  - from Task 2: `CollapsibleSection`, `SliderRow`, `SwitchRow`, `Stepper`, `Chip`
  - from Task 4: `LayerItem`, `LayerList`
  - `ColorSwatchPicker`
- Produces `InspectorPanel(settings: Settings, swatch_colors: list[str])`, a `QFrame` with a fixed width of `INSPECTOR_WIDTH - 10`, plus `INSPECTOR_WIDTH = 340`.
  - Signals:
    - `document_settings_changed()`, `stroke_controls_changed()`
    - `layer_item_clicked(int)`, `layer_visibility_toggled(int)`
    - `delete_selected()`, `delete_all()`
    - `guide_suppress_changed(bool)`, `auto_place_requested(int)`
  - Attributes:
    - `watermark_text_edit`, `font_combo`, `font_px_chip`
    - `auto_fit_check` and `repeat_text_check` (SwitchRow), `repeat_spacing_spin` (Stepper)
    - `color_picker`, `blend_combo`
    - `opacity_row`, `auto_strength_check` (Chip), `brush_row`, `softness_row`
    - `brush_section`
    - `auto_density_row`, `auto_place_btn`, `auto_watermark_status_label`
    - `layers_section`, `layer_count_badge`, `layer_list`, `delete_selected_btn`, `delete_all_btn`
    - `add_metadata_check` (SwitchRow), `metadata_copy_edit`, `reveal_in_explorer_check` (SwitchRow)
  - Methods:
    - `set_swatches(colors, selected)`, `set_brush_context(*, layer_name=None, visible=True)`
    - `load_tool_defaults(Settings)`, `load_stroke_controls(Stroke)`
    - `read_document_settings(Settings) -> Settings`, `read_stroke_controls() -> dict`, `read_tool_defaults() -> dict`
    - `density() -> int`, `set_font_px(int)`, `set_delete_enabled(bool)`
    - `set_layers(list[LayerItem], selected=-1)`, `set_selected_layer(int)`
    - `set_auto_watermark_running(bool)`, `set_auto_watermark_status(str)`

- [ ] **Step 1: Write the failing tests** (`tests/test_inspector.py`)

```python
from brush_watermark.models import Settings, Stroke
from brush_watermark.ui.inspector import INSPECTOR_WIDTH, InspectorPanel
from brush_watermark.ui.layer_list import LayerItem

SWATCHES = ["#FFFFFF", "#808080", "#000000"]


def make_panel() -> InspectorPanel:
    return InspectorPanel(Settings(), SWATCHES)


def test_load_tool_defaults_round_trips_without_emitting(qapp):
    panel = make_panel()
    seen = []
    panel.stroke_controls_changed.connect(lambda: seen.append(1))
    panel.load_tool_defaults(
        Settings(brush_size=77, opacity=33, mask_softness=4, repeat_text=True, repeat_spacing=9)
    )
    c = panel.read_stroke_controls()
    assert (c["brush_size"], c["opacity"], c["mask_softness"], c["repeat_text"], c["repeat_spacing"]) == (
        77, 33, 4, True, 9,
    )
    assert seen == []


def test_load_stroke_controls_titles_the_brush_section(qapp):
    panel = make_panel()
    stroke = Stroke(name="Stroke 2", points=[(0, 0), (9, 9)], brush_size=40, opacity=20, visible=False)
    panel.load_stroke_controls(stroke)
    assert panel.brush_section._title_label.text() == "Layer · Stroke 2 · hidden"


def test_auto_strength_disables_only_the_slider(qapp):
    panel = make_panel()
    panel.auto_strength_check.setChecked(True)
    assert not panel.opacity_row.slider.isEnabled()
    assert panel.auto_strength_check.isEnabled()


def test_repeat_switch_enables_gap_stepper(qapp):
    panel = make_panel()
    panel.repeat_text_check.setChecked(True)
    assert panel.repeat_spacing_spin.isEnabled()
    panel.repeat_text_check.setChecked(False)
    assert not panel.repeat_spacing_spin.isEnabled()


def test_set_layers_updates_badge_and_rows(qapp):
    panel = make_panel()
    panel.set_layers([LayerItem("S1", "10 px", True), LayerItem("S2", "20 px", False)], selected=1)
    assert panel.layer_count_badge.text() == "2"
    rows = panel.layer_list.rows()
    assert len(rows) == 2 and rows[1].property("selected") is True


def test_layer_signals_are_forwarded(qapp):
    panel = make_panel()
    panel.set_layers([LayerItem("S1", "10 px", True)])
    seen = []
    panel.layer_visibility_toggled.connect(seen.append)
    panel.layer_list.rows()[0].eye.click()
    assert seen == [0]


def test_auto_place_button_emits_density(qapp):
    panel = make_panel()
    panel.auto_density_row.slider.setValue(9)
    seen = []
    panel.auto_place_requested.connect(seen.append)
    panel.auto_place_btn.click()
    assert seen == [9] and panel.density() == 9


def test_read_document_settings_reads_switches(qapp):
    panel = make_panel()
    panel.watermark_text_edit.setText("© Me")
    panel.add_metadata_check.setChecked(True)
    settings = panel.read_document_settings(Settings())
    assert settings.watermark_text == "© Me" and settings.add_visible_metadata is True


def test_font_px_chip_and_delete_enabled(qapp):
    panel = make_panel()
    panel.set_font_px(21)
    panel.set_delete_enabled(False)
    assert panel.font_px_chip.text() == "21 px" and not panel.delete_selected_btn.isEnabled()


def test_width_leaves_room_for_the_scrollbar(qapp):
    assert make_panel().width() == INSPECTOR_WIDTH - 10


def test_reveal_in_explorer_defaults_on(qapp):
    assert make_panel().reveal_in_explorer_check.isChecked() is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_inspector.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'brush_watermark.ui.inspector'`

- [ ] **Step 3: Restyle `brush_watermark/ui/color_picker.py`**

Replace the file with:

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from brush_watermark.rendering.colors import closest_swatch_color, normalize_text_color


class ColorSwatchPicker(QWidget):
    """Row of colour swatches; the selected one gets an accent ring (QSS ``#Swatch:checked``)."""

    color_changed = Signal(str)

    SWATCH_SIZE = 22

    def __init__(self):
        super().__init__()
        self._row = QHBoxLayout(self)
        self._row.setSpacing(5)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._buttons: list[QPushButton] = []
        self._colors: list[str] = []
        self._selected = "#ffffff"

    def set_swatches(self, colors: list[str], selected: str | None = None):
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons = []
        self._colors = [normalize_text_color(color) for color in colors]
        for hex_color in self._colors:
            button = QPushButton()
            button.setObjectName("Swatch")
            button.setCheckable(True)
            button.setFixedSize(self.SWATCH_SIZE, self.SWATCH_SIZE)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(hex_color)
            button.setAccessibleName(f"Colour {hex_color}")
            # Per-image data colour, not a UI token.
            button.setStyleSheet(f"QPushButton#Swatch {{ background: {hex_color}; }}")
            button.clicked.connect(lambda _checked=False, value=hex_color: self._select(value, emit=True))
            self._row.addWidget(button)
            self._buttons.append(button)
        self._row.addStretch(1)
        self.set_selected(selected or self._selected)

    def selected_color(self) -> str:
        return self._selected

    def set_selected(self, color: str):
        if not self._colors:
            self._selected = normalize_text_color(color)
            return
        self._selected = closest_swatch_color(color, self._colors)
        self._refresh_checks()

    def _select(self, color: str, emit: bool):
        self._selected = normalize_text_color(color)
        self._refresh_checks()
        if emit:
            self.color_changed.emit(self._selected)

    def _refresh_checks(self):
        for button, hex_color in zip(self._buttons, self._colors):
            button.setChecked(hex_color == self._selected)
```

Note: the literal `"#ffffff"` is the pre-existing default selected-colour *data* value, not a UI colour. Task 10's no-hex test must allow this one file (see Task 10 Step 1).

- [ ] **Step 4: Create `brush_watermark/ui/inspector.py`**

```python
"""Right-hand inspector: watermark, brush, auto watermark, layers and export settings.

Keeps the old SidebarPanel's settings API so MainWindow's editing logic is
unchanged; tools, saving, preview mode, zoom and version info live in the top
bar, tool rail, canvas overlays and footer instead.
"""

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.blend import BLEND_MODE_CHOICES
from brush_watermark.rendering.fonts import available_font_names
from brush_watermark.services.auto_watermark import DEFAULT_DENSITY, MAX_DENSITY, MIN_DENSITY
from brush_watermark.ui.color_picker import ColorSwatchPicker
from brush_watermark.ui.controls import Chip, CollapsibleSection, SliderRow, Stepper, SwitchRow
from brush_watermark.ui.design_tokens import DANGER_TEXT, TEXT
from brush_watermark.ui.icons import get_icon
from brush_watermark.ui.layer_list import LayerItem, LayerList

INSPECTOR_WIDTH = 340


class InspectorPanel(QFrame):
    document_settings_changed = Signal()
    stroke_controls_changed = Signal()
    layer_item_clicked = Signal(int)
    layer_visibility_toggled = Signal(int)
    delete_selected = Signal()
    delete_all = Signal()
    guide_suppress_changed = Signal(bool)
    auto_place_requested = Signal(int)

    def __init__(self, settings: Settings, swatch_colors: list[str]):
        super().__init__()
        self.setObjectName("InspectorPanel")
        # 1 px border + 8 px scrollbar + 1 px slack inside the INSPECTOR_WIDTH scroll area.
        self.setFixedWidth(INSPECTOR_WIDTH - 10)
        self._build_ui(settings, swatch_colors)
        self._connect_signals()
        self.load_tool_defaults(settings)

    # ---- construction -------------------------------------------------

    def _build_ui(self, settings: Settings, swatch_colors: list[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        watermark = CollapsibleSection("Watermark", icon_name="stamp")
        self.watermark_text_edit = QLineEdit(settings.watermark_text)
        self.watermark_text_edit.setPlaceholderText("Watermark text")
        self.watermark_text_edit.setAccessibleName("Watermark text")
        self.font_combo = QComboBox()
        self.font_combo.setAccessibleName("Font")
        font_names = available_font_names()
        self.font_combo.addItems(font_names)
        if settings.font_name in font_names:
            self.font_combo.setCurrentText(settings.font_name)
        elif font_names:
            self.font_combo.setCurrentIndex(0)
        self.font_px_chip = QLabel()
        self.font_px_chip.setObjectName("ValueChip")
        self.font_px_chip.setToolTip("Font size follows brush size")
        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_row.addWidget(self.font_combo, 1)
        font_row.addWidget(self.font_px_chip)
        self.auto_fit_check = SwitchRow("Auto-fit text to stroke", settings.auto_fit_text)
        self.repeat_text_check = SwitchRow("Repeat along stroke", settings.repeat_text, switch_first=True)
        self.repeat_spacing_spin = Stepper(0, 50, settings.repeat_spacing, prefix="gap")
        self.repeat_spacing_spin.setToolTip("Space between repeats, in character widths")
        repeat_row = QHBoxLayout()
        repeat_row.setSpacing(8)
        repeat_row.addWidget(self.repeat_text_check, 1)
        repeat_row.addWidget(self.repeat_spacing_spin)
        watermark.body_layout.addWidget(self.watermark_text_edit)
        watermark.body_layout.addLayout(font_row)
        watermark.body_layout.addWidget(self.auto_fit_check)
        watermark.body_layout.addLayout(repeat_row)
        layout.addWidget(watermark)

        self.brush_section = CollapsibleSection("Brush", icon_name="paintbrush")
        self.brush_section.body_layout.setSpacing(14)
        self.color_picker = ColorSwatchPicker()
        self.color_picker.set_swatches(swatch_colors, settings.text_color)
        self.blend_combo = QComboBox()
        self.blend_combo.setAccessibleName("Blend mode")
        for mode_key, mode_label in BLEND_MODE_CHOICES:
            self.blend_combo.addItem(mode_label, mode_key)
        self.opacity_row = SliderRow("Strength", 1, 100, settings.opacity)
        self.auto_strength_check = Chip("Auto", icon_name="wand-2")
        self.auto_strength_check.setChecked(settings.auto_strength)
        self.auto_strength_check.setToolTip(
            "Compute each new stroke's strength from the pixels underneath it — "
            "flat areas get a fainter mark, busy/textured areas can hide a stronger one. "
            "Applies when a stroke is first drawn or auto-placed."
        )
        self.opacity_row.add_header_widget(self.auto_strength_check)
        self.brush_row = SliderRow("Size", 5, 600, settings.brush_size)
        self.softness_row = SliderRow("Softness", 0, 20, settings.mask_softness)
        body = self.brush_section.body_layout
        body.addWidget(self.color_picker)
        body.addLayout(self._labeled_row("Blend", self.blend_combo))
        body.addWidget(self.opacity_row)
        body.addWidget(self.brush_row)
        body.addWidget(self.softness_row)
        layout.addWidget(self.brush_section)

        auto = CollapsibleSection("Auto watermark", icon_name="wand-2")
        self.auto_density_row = SliderRow("Density", MIN_DENSITY, MAX_DENSITY, DEFAULT_DENSITY)
        self.auto_place_btn = QPushButton("Auto-place")
        self.auto_place_btn.setObjectName("SecondaryButton")
        self.auto_place_btn.setIcon(get_icon("wand-2", 15, TEXT))
        self.auto_place_btn.setIconSize(QSize(15, 15))
        self.auto_place_btn.setToolTip(
            "Find busy, detail-rich areas that avoid the photo's focal subject "
            "and drop several faint, low-opacity watermarks there."
        )
        auto_row = QHBoxLayout()
        auto_row.setSpacing(12)
        auto_row.addWidget(self.auto_density_row, 1)
        auto_row.addWidget(self.auto_place_btn)
        self.auto_watermark_status_label = QLabel()
        self.auto_watermark_status_label.setObjectName("HintLabel")
        self.auto_watermark_status_label.setWordWrap(True)
        self.auto_watermark_status_label.hide()
        auto.body_layout.addLayout(auto_row)
        auto.body_layout.addWidget(self.auto_watermark_status_label)
        layout.addWidget(auto)

        self.layers_section = CollapsibleSection("Layers", icon_name="layers")
        self.layer_count_badge = QLabel("0")
        self.layer_count_badge.setObjectName("CountBadge")
        self.layers_section.add_header_widget(self.layer_count_badge)
        self.layer_list = LayerList()
        self.delete_selected_btn = QPushButton("Delete")
        self.delete_selected_btn.setObjectName("SecondaryButton")
        self.delete_selected_btn.setIcon(get_icon("trash-2", 13, TEXT))
        self.delete_all_btn = QPushButton("Clear all")
        self.delete_all_btn.setObjectName("DangerButton")
        self.delete_all_btn.setIcon(get_icon("trash", 13, DANGER_TEXT))
        layer_actions = QHBoxLayout()
        layer_actions.setSpacing(6)
        layer_actions.addWidget(self.delete_selected_btn, 1)
        layer_actions.addWidget(self.delete_all_btn, 1)
        self.layers_section.body_layout.setSpacing(8)
        self.layers_section.body_layout.addWidget(self.layer_list)
        self.layers_section.body_layout.addLayout(layer_actions)
        layout.addWidget(self.layers_section)

        export = CollapsibleSection("Export", icon_name="image", expanded=False)
        self.add_metadata_check = SwitchRow("Visible metadata strip", settings.add_visible_metadata)
        self.add_metadata_check.setToolTip(
            "Expand the saved copy with camera, lens, settings, serial, and copy info at the bottom."
        )
        self.metadata_copy_edit = QLineEdit(settings.metadata_copy_text)
        self.metadata_copy_edit.setPlaceholderText("Additional copy info (optional)")
        self.metadata_copy_edit.setAccessibleName("Additional copy info")
        self.reveal_in_explorer_check = SwitchRow("Show in Explorer after save", True)
        export.body_layout.addWidget(self.add_metadata_check)
        export.body_layout.addWidget(self.metadata_copy_edit)
        export.body_layout.addWidget(self.reveal_in_explorer_check)
        layout.addWidget(export)

        layout.addStretch(1)

    @staticmethod
    def _labeled_row(text: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        label.setFixedWidth(64)
        row.addWidget(label)
        row.addWidget(widget, 1)
        return row

    def _connect_signals(self):
        emit_document = lambda *_: self.document_settings_changed.emit()
        emit_controls = lambda *_: self.stroke_controls_changed.emit()

        self.watermark_text_edit.textChanged.connect(emit_document)
        self.font_combo.currentTextChanged.connect(emit_document)
        self.auto_fit_check.toggled.connect(emit_document)
        self.auto_strength_check.toggled.connect(emit_document)
        self.auto_strength_check.toggled.connect(self._update_opacity_enabled)
        self.add_metadata_check.toggled.connect(emit_document)
        self.metadata_copy_edit.textChanged.connect(emit_document)

        self.color_picker.color_changed.connect(emit_controls)
        self.blend_combo.currentIndexChanged.connect(emit_controls)
        self.opacity_row.slider.valueChanged.connect(emit_controls)
        self.brush_row.slider.valueChanged.connect(emit_controls)
        self.softness_row.slider.valueChanged.connect(emit_controls)
        self.repeat_text_check.toggled.connect(emit_controls)
        self.repeat_text_check.toggled.connect(self._update_repeat_spacing_enabled)
        self.repeat_spacing_spin.valueChanged.connect(emit_controls)

        self.auto_density_row.slider.valueChanged.connect(
            lambda v: self.auto_density_row.set_value_text(str(v))
        )
        self.auto_density_row.set_value_text(str(self.density()))
        self.auto_place_btn.clicked.connect(lambda _checked=False: self.auto_place_requested.emit(self.density()))

        for row in (self.opacity_row, self.brush_row):
            row.slider.dragStarted.connect(lambda: self.guide_suppress_changed.emit(True))
            row.slider.dragEnded.connect(lambda: self.guide_suppress_changed.emit(False))

        self.layer_list.layer_clicked.connect(self.layer_item_clicked.emit)
        self.layer_list.visibility_toggled.connect(self.layer_visibility_toggled.emit)
        self.delete_selected_btn.clicked.connect(lambda _checked=False: self.delete_selected.emit())
        self.delete_all_btn.clicked.connect(lambda _checked=False: self.delete_all.emit())
        self._update_repeat_spacing_enabled()
        self._update_opacity_enabled()

    # ---- state ---------------------------------------------------------

    def _update_repeat_spacing_enabled(self, *_):
        self.repeat_spacing_spin.setEnabled(self.repeat_text_check.isChecked())

    def _update_opacity_enabled(self, *_):
        # Only the slider: the Auto chip lives in the same row and must stay clickable.
        self.opacity_row.slider.setEnabled(not self.auto_strength_check.isChecked())

    def density(self) -> int:
        return int(self.auto_density_row.slider.value())

    def set_swatches(self, colors: list[str], selected: str) -> None:
        self.color_picker.set_swatches(colors, selected)

    def set_brush_context(self, *, layer_name: str | None = None, visible: bool = True):
        if layer_name is None:
            self.brush_section.set_title("Brush")
            return
        title = f"Layer · {layer_name}"
        if not visible:
            title += " · hidden"
        self.brush_section.set_title(title)

    def set_font_px(self, pixel_size: int) -> None:
        self.font_px_chip.setText(f"{pixel_size} px")

    def set_delete_enabled(self, enabled: bool) -> None:
        self.delete_selected_btn.setEnabled(enabled)

    def set_layers(self, items: list[LayerItem], selected: int = -1) -> None:
        self.layer_count_badge.setText(str(len(items)))
        self.layer_list.set_layers(items, selected)

    def set_selected_layer(self, index: int) -> None:
        self.layer_list.set_selected(index)

    def _block_control_signals(self, block: bool):
        for widget in (
            self.color_picker,
            self.blend_combo,
            self.opacity_row.slider,
            self.brush_row.slider,
            self.softness_row.slider,
            self.repeat_text_check,
            self.repeat_spacing_spin,
        ):
            widget.blockSignals(block)

    def _load_control_values(self, source: Settings | Stroke):
        """Push brush/opacity/softness/repeat/color/blend from a Settings or Stroke onto the controls."""
        self._block_control_signals(True)
        self.brush_row.slider.setValue(source.brush_size)
        self.opacity_row.slider.setValue(source.opacity)
        self.softness_row.slider.setValue(source.mask_softness)
        self.repeat_text_check.setChecked(source.repeat_text)
        self.repeat_spacing_spin.setValue(source.repeat_spacing)
        self.color_picker.set_selected(source.text_color)
        blend_index = self.blend_combo.findData(source.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self._update_repeat_spacing_enabled()

    def load_tool_defaults(self, settings: Settings):
        self._load_control_values(settings)
        self.set_brush_context()

    def load_stroke_controls(self, stroke: Stroke):
        self._load_control_values(stroke)
        self.set_brush_context(layer_name=stroke.name, visible=stroke.visible)

    def read_document_settings(self, tool_defaults: Settings) -> Settings:
        return Settings(
            watermark_text=self.watermark_text_edit.text(),
            opacity=tool_defaults.opacity,
            font_name=self.font_combo.currentText(),
            brush_size=tool_defaults.brush_size,
            angle_offset=tool_defaults.angle_offset,
            mask_softness=tool_defaults.mask_softness,
            text_color=tool_defaults.text_color,
            auto_fit_text=bool(self.auto_fit_check.isChecked()),
            auto_strength=bool(self.auto_strength_check.isChecked()),
            repeat_text=tool_defaults.repeat_text,
            repeat_spacing=tool_defaults.repeat_spacing,
            blend_mode=tool_defaults.blend_mode,
            add_visible_metadata=bool(self.add_metadata_check.isChecked()),
            metadata_copy_text=self.metadata_copy_edit.text(),
        )

    def read_stroke_controls(self) -> dict:
        return {
            "brush_size": int(self.brush_row.slider.value()),
            "opacity": int(self.opacity_row.slider.value()),
            "blend_mode": str(self.blend_combo.currentData()),
            "text_color": self.color_picker.selected_color(),
            "angle_offset": 0,
            "mask_softness": int(self.softness_row.slider.value()),
            "repeat_text": bool(self.repeat_text_check.isChecked()),
            "repeat_spacing": int(self.repeat_spacing_spin.value()),
        }

    def read_tool_defaults(self) -> dict:
        return self.read_stroke_controls()

    def set_auto_watermark_running(self, running: bool):
        self.auto_place_btn.setEnabled(not running)
        self.auto_density_row.setEnabled(not running)
        if running:
            self.set_auto_watermark_status("Analyzing photo…")

    def set_auto_watermark_status(self, text: str):
        self.auto_watermark_status_label.setText(text)
        self.auto_watermark_status_label.setVisible(bool(text))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass. (The old sidebar still uses `ColorSwatchPicker`; it works with the new styling.)

- [ ] **Step 6: Commit**

```bash
git add brush_watermark/ui/color_picker.py brush_watermark/ui/inspector.py tests/test_inspector.py
git commit -m "Add the redesigned inspector panel"
```

---

### Task 6: Top bar

**Files:**
- Create: `brush_watermark/ui/top_bar.py`, `tests/test_top_bar.py`

**Interfaces:**
- Consumes: `SegmentedControl`, `SplitButton`, `make_menu` (Task 2)
- Produces `TopBar(QFrame)`:
  - `HEIGHT = 52`
  - Signals: `preview_changed(bool)` (True = show the original), `save_and_close()`, `save_copy_and_close()`, `save_all_and_close()`, `exit_without_saving()`
  - Methods: `add_menu(title: str) -> QMenu`, `show_original() -> bool`, `set_file_info(name: str, serial: str | None, index: int, count: int)`, `set_unsaved(dirty: bool)`, `set_multi_document_mode(enabled: bool, edited_count: int = 0)`
  - Attributes: `preview_toggle`, `file_name_label`, `serial_chip`, `index_badge`, `unsaved_indicator`, `exit_button`, `save_copy_button`, `save_split`, `save_close_action`, `save_all_action`, `save_copy_action`

- [ ] **Step 1: Write the failing tests** (`tests/test_top_bar.py`)

```python
from PySide6.QtWidgets import QMenu, QPushButton

from brush_watermark.ui.top_bar import TopBar


def test_file_info_toggles_optional_parts(qapp):
    bar = TopBar()
    bar.set_file_info("a.jpg", None, 0, 1)
    assert bar.file_name_label.text() == "a.jpg"
    assert bar.serial_chip.isHidden() and bar.index_badge.isHidden()
    bar.set_file_info("b.jpg", "6022905", 1, 6)
    assert bar.serial_chip.text() == "#6022905" and not bar.serial_chip.isHidden()
    assert bar.index_badge.text() == "2 / 6" and not bar.index_badge.isHidden()


def test_unsaved_indicator(qapp):
    bar = TopBar()
    assert bar.unsaved_indicator.isHidden()
    bar.set_unsaved(True)
    assert not bar.unsaved_indicator.isHidden()


def test_preview_toggle_defaults_to_watermarked_and_emits(qapp):
    bar = TopBar()
    seen = []
    bar.preview_changed.connect(seen.append)
    assert bar.show_original() is False
    bar.preview_toggle.setCurrentIndex(0)
    assert bar.show_original() is True and seen == [True]


def test_save_buttons_and_actions_emit(qapp):
    bar = TopBar()
    seen = []
    bar.save_and_close.connect(lambda: seen.append("save"))
    bar.save_copy_and_close.connect(lambda: seen.append("copy"))
    bar.save_all_and_close.connect(lambda: seen.append("all"))
    bar.exit_without_saving.connect(lambda: seen.append("exit"))
    bar.save_split.main.click()
    bar.save_copy_button.click()
    bar.exit_button.click()
    bar.save_all_action.trigger()
    bar.save_copy_action.trigger()
    bar.save_close_action.trigger()
    assert seen == ["save", "copy", "exit", "all", "copy", "save"]


def test_multi_document_mode_shows_edited_count(qapp):
    bar = TopBar()
    assert not bar.save_all_action.isVisible()
    bar.set_multi_document_mode(True, 3)
    assert bar.save_all_action.isVisible()
    assert bar.save_all_action.text() == "Save all && close (3 edited)"


def test_add_menu_adds_a_menu_button(qapp):
    bar = TopBar()
    menu = bar.add_menu("&File")
    assert isinstance(menu, QMenu)
    buttons = [b for b in bar.findChildren(QPushButton) if b.objectName() == "MenuButton"]
    assert [b.text() for b in buttons] == ["&File"] and buttons[0].menu() is menu
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_top_bar.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'brush_watermark.ui.top_bar'`

- [ ] **Step 3: Create `brush_watermark/ui/top_bar.py`**

```python
"""Top bar: logo and menus, active file info, Original/Watermarked toggle, save actions."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from brush_watermark.ui.controls import SegmentedControl, SplitButton, make_menu
from brush_watermark.ui.design_tokens import ON_ACCENT, TEXT, TEXT_MUTED, TEXT_SECONDARY
from brush_watermark.ui.icons import get_icon, get_pixmap


def _vertical_divider(object_name: str, height: int) -> QFrame:
    divider = QFrame()
    divider.setObjectName(object_name)
    divider.setFixedSize(1, height)
    return divider


class TopBar(QFrame):
    preview_changed = Signal(bool)
    save_and_close = Signal()
    save_copy_and_close = Signal()
    save_all_and_close = Signal()
    exit_without_saving = Signal()

    HEIGHT = 52

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(self.HEIGHT)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 12, 0)
        row.setSpacing(12)

        logo = QLabel()
        logo.setObjectName("LogoMark")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(get_pixmap("paintbrush", 17, ON_ACCENT))
        self._menu_row = QHBoxLayout()
        self._menu_row.setSpacing(2)
        left = QHBoxLayout()
        left.setSpacing(10)
        left.addWidget(logo)
        left.addLayout(self._menu_row)
        row.addLayout(left)
        row.addWidget(_vertical_divider("TopDivider", 22))

        file_icon = QLabel()
        file_icon.setPixmap(get_pixmap("image", 15, TEXT_MUTED))
        self.file_name_label = QLabel()
        self.file_name_label.setObjectName("FileName")
        self.serial_chip = QLabel()
        self.serial_chip.setObjectName("SerialChip")
        self.serial_chip.setToolTip("Image serial")
        self.index_badge = QLabel()
        self.index_badge.setObjectName("CountBadge")
        self.unsaved_indicator = QWidget()
        unsaved_row = QHBoxLayout(self.unsaved_indicator)
        unsaved_row.setContentsMargins(0, 0, 0, 0)
        unsaved_row.setSpacing(5)
        dot = QLabel()
        dot.setObjectName("UnsavedDot")
        dot.setFixedSize(6, 6)
        unsaved_label = QLabel("Unsaved")
        unsaved_label.setObjectName("UnsavedLabel")
        unsaved_row.addWidget(dot)
        unsaved_row.addWidget(unsaved_label)
        self.unsaved_indicator.hide()
        info = QHBoxLayout()
        info.setSpacing(8)
        for widget in (file_icon, self.file_name_label, self.serial_chip, self.index_badge, self.unsaved_indicator):
            info.addWidget(widget)
        row.addLayout(info)

        row.addStretch(1)
        self.preview_toggle = SegmentedControl(["Original", "Watermarked"])
        self.preview_toggle.setCurrentIndex(1)
        self.preview_toggle.setAccessibleName("Preview")
        row.addWidget(self.preview_toggle)
        row.addStretch(1)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setObjectName("GhostButton")
        self.exit_button.setIcon(get_icon("x", 15, TEXT_SECONDARY))
        self.exit_button.setToolTip("Exit without saving")
        self.save_copy_button = QPushButton("Save copy")
        self.save_copy_button.setObjectName("SecondaryButton")
        self.save_copy_button.setIcon(get_icon("copy", 15, TEXT))
        self.save_copy_button.setToolTip("Save a watermarked copy next to the original and close")
        self.save_split = SplitButton("Save && close", "save")
        menu = self.save_split.menu
        self.save_close_action = menu.addAction(get_icon("save", 15, TEXT), "Save && close")
        self.save_all_action = menu.addAction(get_icon("images", 15, TEXT), "Save all && close")
        menu.addSeparator()
        self.save_copy_action = menu.addAction(get_icon("copy", 15, TEXT), "Save copy && close")
        for button in (self.exit_button, self.save_copy_button):
            button.setIconSize(QSize(15, 15))
        right = QHBoxLayout()
        right.setSpacing(8)
        right.addWidget(self.exit_button)
        right.addWidget(self.save_copy_button)
        right.addWidget(self.save_split)
        row.addLayout(right)

        self.preview_toggle.currentChanged.connect(lambda index: self.preview_changed.emit(index == 0))
        self.exit_button.clicked.connect(lambda _checked=False: self.exit_without_saving.emit())
        self.save_copy_button.clicked.connect(lambda _checked=False: self.save_copy_and_close.emit())
        self.save_split.clicked.connect(self.save_and_close.emit)
        self.save_close_action.triggered.connect(lambda _checked=False: self.save_and_close.emit())
        self.save_all_action.triggered.connect(lambda _checked=False: self.save_all_and_close.emit())
        self.save_copy_action.triggered.connect(lambda _checked=False: self.save_copy_and_close.emit())
        self.set_multi_document_mode(False)

    def add_menu(self, title: str) -> QMenu:
        button = QPushButton(title)
        button.setObjectName("MenuButton")
        menu = make_menu(button)
        button.setMenu(menu)
        self._menu_row.addWidget(button)
        return menu

    def show_original(self) -> bool:
        return self.preview_toggle.currentIndex() == 0

    def set_file_info(self, name: str, serial: str | None, index: int, count: int) -> None:
        self.file_name_label.setText(name)
        self.serial_chip.setText(f"#{serial}" if serial else "")
        self.serial_chip.setVisible(bool(serial))
        self.index_badge.setText(f"{index + 1} / {count}")
        self.index_badge.setVisible(count > 1)

    def set_unsaved(self, dirty: bool) -> None:
        self.unsaved_indicator.setVisible(dirty)

    def set_multi_document_mode(self, enabled: bool, edited_count: int = 0) -> None:
        self.save_all_action.setVisible(enabled)
        self.save_all_action.setText(
            f"Save all && close ({edited_count} edited)" if edited_count else "Save all && close"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add brush_watermark/ui/top_bar.py tests/test_top_bar.py
git commit -m "Add the redesigned top bar"
```

---

### Task 7: Tool rail and status footer

**Files:**
- Create: `brush_watermark/ui/tool_rail.py`, `brush_watermark/ui/status_footer.py`, `tests/test_tool_rail.py`, `tests/test_status_footer.py`

**Interfaces:**
- Consumes: `KeyHint` (Task 2), `mono_font` (Task 1), `ToolMode`, `UpdateCheckResult`
- Produces:
  - `ToolRail(QFrame)`: `WIDTH = 60`; signals `tool_changed(object)` (a `ToolMode`) and `auto_place_requested()`; method `set_active_tool(ToolMode)`; attributes `buttons: dict[ToolMode, RailButton]`, `auto_place_btn`, `shortcuts_btn`.
  - Module constant `SHORTCUTS: tuple[tuple[str, str], ...]`.
  - `StatusFooter(QFrame)`: `HEIGHT = 30`; signal `update_now()`; methods `set_version_info(current_version: str, result: UpdateCheckResult | None = None)`, `set_update_progress(percent: int, message: str)`, `clear_update_progress()`; attributes `version_label`, `update_now_button`, `update_link`, `progress_label`.

- [ ] **Step 1: Write the failing tests**

`tests/test_tool_rail.py`:

```python
from brush_watermark.models import ToolMode
from brush_watermark.ui.tool_rail import SHORTCUTS, ToolRail


def test_clicking_a_tool_emits_it(qapp):
    rail = ToolRail()
    seen = []
    rail.tool_changed.connect(seen.append)
    rail.buttons[ToolMode.PATH].click()
    assert seen == [ToolMode.PATH]


def test_set_active_tool_checks_exclusively_without_emitting(qapp):
    rail = ToolRail()
    seen = []
    rail.tool_changed.connect(seen.append)
    rail.set_active_tool(ToolMode.ERASER)
    assert [t for t, b in rail.buttons.items() if b.isChecked()] == [ToolMode.ERASER]
    assert seen == []


def test_brush_is_active_by_default(qapp):
    assert ToolRail().buttons[ToolMode.BRUSH].isChecked()


def test_auto_place_button_emits(qapp):
    rail = ToolRail()
    seen = []
    rail.auto_place_requested.connect(lambda: seen.append(True))
    rail.auto_place_btn.click()
    assert seen == [True]


def test_shortcuts_list_existing_keys_only():
    keys = [k for k, _ in SHORTCUTS]
    assert keys[:4] == ["V", "B", "A", "E"]
    assert "Ctrl+S" not in keys and "H" not in keys and "Z" not in keys
```

`tests/test_status_footer.py`:

```python
from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.status_footer import StatusFooter


def result(**kwargs) -> UpdateCheckResult:
    base = dict(current_version="1.15.0", latest_version="1.15.0", update_available=False, release_url="https://example.invalid/r")
    base.update(kwargs)
    return UpdateCheckResult(**base)


def test_checking_state(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0")
    assert footer.version_label.text() == "v1.15.0 · Checking for updates…"


def test_up_to_date(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0", result())
    assert footer.version_label.text() == "v1.15.0 · Up to date"
    assert footer.update_now_button.isHidden() and footer.update_link.isHidden()


def test_update_with_download_shows_button_that_emits(qapp):
    footer = StatusFooter()
    footer.set_version_info(
        "1.15.0", result(latest_version="1.16.0", update_available=True, download_url="https://example.invalid/z")
    )
    assert not footer.update_now_button.isHidden()
    assert footer.update_now_button.text() == "Update to v1.16.0"
    seen = []
    footer.update_now.connect(lambda: seen.append(True))
    footer.update_now_button.click()
    assert seen == [True]


def test_update_without_download_shows_link(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0", result(latest_version="1.16.0", update_available=True))
    assert not footer.update_link.isHidden() and "https://example.invalid/r" in footer.update_link.text()


def test_failed_check_shows_version_only(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0", result(check_failed=True))
    assert footer.version_label.text() == "v1.15.0"


def test_progress(qapp):
    footer = StatusFooter()
    footer.set_update_progress(40, "Downloading")
    assert footer.progress_label.text() == "Downloading (40%)" and not footer.update_now_button.isEnabled()
    footer.clear_update_progress()
    assert footer.progress_label.isHidden() and footer.update_now_button.isEnabled()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_tool_rail.py tests/test_status_footer.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `brush_watermark/ui/tool_rail.py`**

```python
"""Left tool rail: drawing tools with key letters, auto-place, shortcuts popup."""

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from brush_watermark.models import ToolMode
from brush_watermark.ui.app_fonts import mono_font
from brush_watermark.ui.controls import KeyCombo
from brush_watermark.ui.design_tokens import ACCENT_TEXT, TEXT_LABEL, TEXT_MUTED
from brush_watermark.ui.icons import get_icon_checkable

RAIL_TOOLS = (
    (ToolMode.POINTER, "mouse-pointer-2", "Select", "V"),
    (ToolMode.BRUSH, "paintbrush", "Brush", "B"),
    (ToolMode.PATH, "pen-tool", "Path", "A"),
    (ToolMode.ERASER, "eraser", "Eraser", "E"),
)

# Only shortcuts the app actually handles (MainWindow.keyPressEvent / canvas input).
SHORTCUTS = (
    ("V", "Select tool"),
    ("B", "Brush tool"),
    ("A", "Path tool"),
    ("E", "Eraser tool"),
    ("Wheel", "Strength"),
    ("Alt+Wheel", "Brush size"),
    ("Right-click", "Stop drawing (Brush)"),
    ("Dbl-click", "Add anchor (Path)"),
    ("Del", "Remove anchor (Path)"),
    ("Esc", "Cancel line / deselect anchor"),
)


class RailButton(QToolButton):
    """40×40 rail button; draws its shortcut letter in the bottom-right corner."""

    SIZE = 40

    def __init__(self, icon_name: str, label: str, key: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("RailButton")
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setIcon(get_icon_checkable(icon_name, 19, TEXT_LABEL, ACCENT_TEXT))
        self.setIconSize(QSize(19, 19))
        self.setToolTip(f"{label} ({key})" if key else label)
        self.setAccessibleName(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._key = key

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._key:
            return
        painter = QPainter(self)
        painter.setFont(mono_font(9))
        painter.setPen(QColor(ACCENT_TEXT if self.isChecked() else TEXT_MUTED))
        painter.drawText(
            self.rect().adjusted(0, 0, -4, -2),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            self._key,
        )
        painter.end()


class ShortcutsPopup(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("PopupPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        grid = QGridLayout(self)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        for row, (keys, text) in enumerate(SHORTCUTS):
            grid.addWidget(KeyCombo(keys), row, 0, Qt.AlignmentFlag.AlignLeft)
            label = QLabel(text)
            label.setObjectName("HintText")
            grid.addWidget(label, row, 1)


class ToolRail(QFrame):
    tool_changed = Signal(object)
    auto_place_requested = Signal()

    WIDTH = 60

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ToolRail")
        self.setFixedWidth(self.WIDTH)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 10, 0, 10)
        column.setSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons: dict[ToolMode, RailButton] = {}
        for tool, icon_name, label, key in RAIL_TOOLS:
            button = RailButton(icon_name, label, key)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, t=tool: self.tool_changed.emit(t))
            self._group.addButton(button)
            self.buttons[tool] = button
            column.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)

        column.addWidget(self._divider(), 0, Qt.AlignmentFlag.AlignHCenter)
        self.auto_place_btn = RailButton("wand-2", "Auto-place watermarks")
        self.auto_place_btn.clicked.connect(lambda _checked=False: self.auto_place_requested.emit())
        column.addWidget(self.auto_place_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addStretch(1)
        self.shortcuts_btn = RailButton("keyboard", "Keyboard shortcuts")
        self.shortcuts_btn.clicked.connect(lambda _checked=False: self._show_shortcuts())
        column.addWidget(self.shortcuts_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.set_active_tool(ToolMode.BRUSH)

    @staticmethod
    def _divider() -> QFrame:
        divider = QFrame()
        divider.setObjectName("RailDivider")
        divider.setFixedSize(24, 1)
        return divider

    def set_active_tool(self, tool: ToolMode) -> None:
        for mode, button in self.buttons.items():
            button.blockSignals(True)
            button.setChecked(mode == tool)
            button.blockSignals(False)

    def _show_shortcuts(self) -> None:
        popup = ShortcutsPopup(self)
        popup.adjustSize()
        anchor = self.shortcuts_btn.mapToGlobal(QPoint(self.shortcuts_btn.width() + 8, self.shortcuts_btn.height()))
        popup.move(anchor.x(), anchor.y() - popup.height())
        popup.show()
```

- [ ] **Step 4: Create `brush_watermark/ui/status_footer.py`**

```python
"""Bottom status bar: key hints, the edit-target note, version and update status."""

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.controls import KeyHint
from brush_watermark.ui.design_tokens import ON_ACCENT, SUCCESS, TEXT_MUTED, WARNING
from brush_watermark.ui.icons import get_icon

FOOTER_HINTS = (
    ("Wheel", "Strength"),
    ("Alt+Wheel", "Brush size"),
    ("Dbl-click", "Add anchor"),
    ("Del", "Remove anchor"),
)


class StatusFooter(QFrame):
    update_now = Signal()

    HEIGHT = 30

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatusFooter")
        self.setFixedHeight(self.HEIGHT)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(18)
        for keys, text in FOOTER_HINTS:
            row.addWidget(KeyHint(keys, text, text_object_name="FooterText"))
        row.addStretch(1)
        note = QLabel("Controls edit the selected layer, or tool defaults when nothing is selected")
        note.setObjectName("FooterText")
        row.addWidget(note)
        divider = QFrame()
        divider.setObjectName("FooterDivider")
        divider.setFixedSize(1, 12)
        row.addWidget(divider)

        status = QHBoxLayout()
        status.setSpacing(6)
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(6, 6)
        self.version_label = QLabel()
        self.version_label.setObjectName("FooterText")
        self.update_link = QLabel()
        self.update_link.setObjectName("FooterText")
        self.update_link.setOpenExternalLinks(True)
        self.update_link.hide()
        self.update_now_button = QPushButton()
        self.update_now_button.setObjectName("FooterUpdateButton")
        self.update_now_button.setIcon(get_icon("download", 11, ON_ACCENT))
        self.update_now_button.setIconSize(QSize(11, 11))
        self.update_now_button.hide()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("FooterText")
        self.progress_label.hide()
        for widget in (self._status_dot, self.version_label, self.update_link, self.update_now_button, self.progress_label):
            status.addWidget(widget)
        row.addLayout(status)

        self.update_now_button.clicked.connect(lambda _checked=False: self.update_now.emit())
        self._set_dot(TEXT_MUTED)

    def _set_dot(self, color: str) -> None:
        self._status_dot.setStyleSheet(f"background: {color}; border-radius: 3px;")

    def set_version_info(self, current_version: str, result: UpdateCheckResult | None = None) -> None:
        self.update_now_button.hide()
        self.update_link.hide()
        if result is None:
            self.version_label.setText(f"v{current_version} · Checking for updates…")
            self._set_dot(TEXT_MUTED)
            return
        if result.check_failed:
            self.version_label.setText(f"v{current_version}")
            self._set_dot(TEXT_MUTED)
            return
        if result.update_available and result.latest_version:
            self.version_label.setText(f"v{current_version}")
            self._set_dot(WARNING)
            if result.download_url:
                self.update_now_button.setText(f"Update to v{result.latest_version}")
                self.update_now_button.show()
            else:
                self.update_link.setText(
                    f'<a href="{result.release_url}">v{result.latest_version} available — open release page</a>'
                )
                self.update_link.show()
            return
        self.version_label.setText(f"v{current_version} · Up to date")
        self._set_dot(SUCCESS)

    def set_update_progress(self, percent: int, message: str) -> None:
        self.update_now_button.setEnabled(False)
        self.progress_label.setText(message if percent >= 100 else f"{message} ({percent}%)")
        self.progress_label.show()

    def clear_update_progress(self) -> None:
        self.update_now_button.setEnabled(True)
        self.progress_label.hide()
        self.progress_label.setText("")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add brush_watermark/ui/tool_rail.py brush_watermark/ui/status_footer.py tests/test_tool_rail.py tests/test_status_footer.py
git commit -m "Add the tool rail and status footer"
```

---

### Task 8: Canvas overlays and canvas restyle

**Files:**
- Create: `brush_watermark/ui/canvas_overlays.py`, `tests/test_canvas_overlays.py`
- Modify: `brush_watermark/ui/canvas.py` (imports, `__init__`, `paintEvent`, `_draw_anchor_handles`), `brush_watermark/ui/design_tokens.py` (remove `CANVAS_ANCHOR_OUTLINE`)

**Interfaces:**
- Consumes: `KeyHint` (Task 2), tokens
- Produces:
  - `tool_hint(tool: ToolMode) -> tuple[str, tuple[tuple[str, str], ...]]`
  - `HintPill.set_tool(ToolMode)`; attribute `tool_label`
  - `ZoomPill`: signal `zoom_mode_changed(bool)` (True = 100 %), `set_zoom_percent(int)`; attributes `fit_btn`, `one_to_one_btn`, `percent_label`
  - `BrushReadout.set_values(color: str, size_px: int, strength_text: str, blend_label: str)`; attributes `size_label`, `strength_label`, `blend_label`
  - `CanvasArea(scroll_area: QScrollArea)`: attributes `hint_pill`, `zoom_pill`, `brush_readout`, `scroll_area`; method `refresh_overlays()`; `MARGIN = 16`
  - `canvas.make_dot_tile(spacing: int = 20) -> QPixmap`

- [ ] **Step 1: Write the failing tests** (`tests/test_canvas_overlays.py`)

```python
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QScrollArea

from brush_watermark.models import ToolMode
from brush_watermark.ui.canvas import make_dot_tile
from brush_watermark.ui.canvas_overlays import CanvasArea, tool_hint
from brush_watermark.ui.design_tokens import CANVAS_BG, CANVAS_DOT


def test_every_tool_has_a_hint():
    for tool in ToolMode:
        name, hints = tool_hint(tool)
        assert name and hints


def test_hint_pill_follows_tool(qapp):
    area = CanvasArea(QScrollArea())
    area.hint_pill.set_tool(ToolMode.PATH)
    assert area.hint_pill.tool_label.text() == "Path"


def test_zoom_pill_emits_mode(qapp):
    area = CanvasArea(QScrollArea())
    seen = []
    area.zoom_pill.zoom_mode_changed.connect(seen.append)
    area.zoom_pill.one_to_one_btn.click()
    area.zoom_pill.fit_btn.click()
    assert seen == [True, False]
    area.zoom_pill.set_zoom_percent(62)
    assert area.zoom_pill.percent_label.text() == "62%"


def test_brush_readout_values(qapp):
    area = CanvasArea(QScrollArea())
    area.brush_readout.set_values("#FFFFFF", 41, "19%", "Hard light")
    texts = (area.brush_readout.size_label.text(), area.brush_readout.strength_label.text(), area.brush_readout.blend_label.text())
    assert texts == ("41 px", "19%", "Hard light")


def test_overlays_are_positioned_on_resize(qapp):
    area = CanvasArea(QScrollArea())
    area.resize(800, 600)
    area.show()
    qapp.processEvents()
    m = CanvasArea.MARGIN
    assert area.scroll_area.geometry() == area.rect()
    assert area.hint_pill.y() == m
    assert abs(area.hint_pill.x() + area.hint_pill.width() / 2 - 400) <= 1
    assert area.zoom_pill.x() == m and area.zoom_pill.geometry().bottom() == 600 - m - 1
    assert area.brush_readout.geometry().right() == 800 - m - 1


def test_dot_tile(qapp):
    image = make_dot_tile().toImage()
    assert (image.width(), image.height()) == (20, 20)
    assert image.pixelColor(0, 0) == QColor(CANVAS_DOT)
    assert image.pixelColor(10, 10) == QColor(CANVAS_BG)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_canvas_overlays.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'brush_watermark.ui.canvas_overlays'`

- [ ] **Step 3: Create `brush_watermark/ui/canvas_overlays.py`**

```python
"""Floating panels over the canvas: tool hints, zoom, brush readout."""

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
)

from brush_watermark.models import ToolMode
from brush_watermark.ui.controls import KeyHint
from brush_watermark.ui.design_tokens import SHADOW, TEXT, TEXT_SECONDARY, rgba
from brush_watermark.ui.icons import get_icon

# Per-tool hints, matching what MainWindow/CanvasWidget actually handle.
TOOL_HINTS: dict[ToolMode, tuple[str, tuple[tuple[str, str], ...]]] = {
    ToolMode.POINTER: ("Select", (("Click", "Select / deselect"),)),
    ToolMode.BRUSH: (
        "Brush",
        (("Drag", "Freehand"), ("Click", "Straight line"), ("Click end", "Resume"), ("Right-click", "Stop")),
    ),
    ToolMode.PATH: ("Path", (("Drag", "Move anchor"), ("Dbl-click", "Add anchor"), ("Del", "Remove anchor"))),
    ToolMode.ERASER: ("Eraser", (("Drag", "Erase"), ("Alt+Wheel", "Size"))),
}


def tool_hint(tool: ToolMode) -> tuple[str, tuple[tuple[str, str], ...]]:
    return TOOL_HINTS[tool]


def _pill_divider() -> QFrame:
    divider = QFrame()
    divider.setObjectName("PillDivider")
    divider.setFixedSize(1, 16)
    return divider


class FloatingPanel(QFrame):
    """Rounded translucent panel with a soft drop shadow."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FloatingPanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        color = QColor(SHADOW)
        color.setAlphaF(0.35)
        shadow.setColor(color)
        self.setGraphicsEffect(shadow)
        self.row = QHBoxLayout(self)


class HintPill(FloatingPanel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.row.setContentsMargins(14, 0, 14, 0)
        self.row.setSpacing(10)
        self.tool_label = QLabel()
        self.tool_label.setObjectName("HintTool")
        self.row.addWidget(self.tool_label)
        self.row.addWidget(_pill_divider())
        self._hints: list[QWidget] = []

    def set_tool(self, tool: ToolMode) -> None:
        name, hints = tool_hint(tool)
        self.tool_label.setText(name)
        for widget in self._hints:
            widget.setParent(None)
            widget.deleteLater()
        self._hints = [KeyHint(keys, text) for keys, text in hints]
        for widget in self._hints:
            self.row.addWidget(widget)
        self.adjustSize()


class ZoomPill(FloatingPanel):
    zoom_mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.row.setContentsMargins(4, 3, 4, 3)
        self.row.setSpacing(2)
        self.percent_label = QLabel("100%")
        self.percent_label.setObjectName("ZoomPercent")
        self.percent_label.setFixedWidth(46)
        self.percent_label.setToolTip("Current preview zoom")
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setObjectName("PillButton")
        self.fit_btn.setIcon(get_icon("maximize", 14, TEXT_SECONDARY))
        self.fit_btn.setIconSize(QSize(14, 14))
        self.fit_btn.setToolTip("Fit the image to the window")
        self.one_to_one_btn = QPushButton("1:1")
        self.one_to_one_btn.setObjectName("PillButtonMono")
        self.one_to_one_btn.setToolTip("Actual size (100%)")
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for button in (self.fit_btn, self.one_to_one_btn):
            button.setCheckable(True)
            self._group.addButton(button)
        self.fit_btn.setChecked(True)
        self.row.addWidget(self.percent_label)
        self.row.addWidget(_pill_divider())
        self.row.addWidget(self.fit_btn)
        self.row.addWidget(self.one_to_one_btn)
        self._group.buttonToggled.connect(self._on_toggled)

    def _on_toggled(self, button: QPushButton, checked: bool) -> None:
        if checked:
            self.zoom_mode_changed.emit(button is self.one_to_one_btn)

    def set_zoom_percent(self, percent: int) -> None:
        self.percent_label.setText(f"{percent}%")


class BrushReadout(FloatingPanel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.row.setContentsMargins(14, 0, 14, 0)
        self.row.setSpacing(12)
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(14, 14)
        self.size_label = QLabel()
        self.strength_label = QLabel()
        for label in (self.size_label, self.strength_label):
            label.setObjectName("ReadoutText")
        self.blend_label = QLabel()
        self.blend_label.setObjectName("HintText")
        self.row.addWidget(self.color_dot)
        self.row.addWidget(self.size_label)
        self.row.addWidget(self._slash())
        self.row.addWidget(self.strength_label)
        self.row.addWidget(self._slash())
        self.row.addWidget(self.blend_label)

    @staticmethod
    def _slash() -> QLabel:
        label = QLabel("/")
        label.setObjectName("ReadoutSlash")
        return label

    def set_values(self, color: str, size_px: int, strength_text: str, blend_label: str) -> None:
        # `color` is the stroke's data colour, not a UI token.
        self.color_dot.setStyleSheet(
            f"background: {color}; border: 1px solid {rgba(TEXT, 0.25)}; border-radius: 7px;"
        )
        self.size_label.setText(f"{size_px} px")
        self.strength_label.setText(strength_text)
        self.blend_label.setText(blend_label)
        self.adjustSize()


class CanvasArea(QWidget):
    """Holds the canvas scroll area and floats the overlay panels above it."""

    MARGIN = 16

    def __init__(self, scroll_area: QScrollArea, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.scroll_area = scroll_area
        scroll_area.setParent(self)
        self.hint_pill = HintPill(self)
        self.zoom_pill = ZoomPill(self)
        self.brush_readout = BrushReadout(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scroll_area.setGeometry(self.rect())
        self.refresh_overlays()

    def refresh_overlays(self) -> None:
        m = self.MARGIN
        for panel in (self.hint_pill, self.zoom_pill, self.brush_readout):
            panel.adjustSize()
            panel.raise_()
        self.hint_pill.move((self.width() - self.hint_pill.width()) // 2, m)
        self.zoom_pill.move(m, self.height() - self.zoom_pill.height() - m)
        self.brush_readout.move(
            self.width() - self.brush_readout.width() - m,
            self.height() - self.brush_readout.height() - m,
        )
```

- [ ] **Step 4: Restyle the canvas (`brush_watermark/ui/canvas.py`)**

Replace the imports block:

```python
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from brush_watermark.geometry.path_text import point_at_distance, smooth_path_for_text
from brush_watermark.geometry.points import normalize_text_direction
from brush_watermark.models import CanvasView, ToolMode
from brush_watermark.ui.design_tokens import (
    ACCENT,
    ACCENT_BRIGHT,
    ANCHOR_FILL,
    CANVAS_BG,
    CANVAS_DOT,
    CANVAS_DRAWING,
    CANVAS_ERASER,
    CANVAS_SPAN_END,
    CANVAS_SPAN_START,
    CANVAS_SPAN_TRACK,
    HANDLE,
)

DOT_SPACING = 20


def make_dot_tile(spacing: int = DOT_SPACING) -> QPixmap:
    """One tile of the dotted canvas background (a 2 px dot at the top-left)."""
    tile = QPixmap(spacing, spacing)
    tile.fill(QColor(CANVAS_BG))
    painter = QPainter(tile)
    painter.fillRect(0, 0, 2, 2, QColor(CANVAS_DOT))
    painter.end()
    return tile
```

Keep the existing `QRectF` import only if `canvas.py` still uses it elsewhere. Check with `grep -n "QRectF" brush_watermark/ui/canvas.py` and drop it from the import if the only use was in `_draw_anchor_handles`.

In `CanvasWidget.__init__`, after `self.preview_pixmap = preview_pixmap` add:

```python
        self._background = QBrush(make_dot_tile())
```

In `paintEvent`, replace `p.fillRect(self.rect(), QColor(CANVAS_BG))` with:

```python
        p.fillRect(self.rect(), self._background)
```

Replace `_draw_anchor_handles` with:

```python
    def _draw_anchor_handles(self, p: QPainter, view: CanvasView, stroke):
        """Draw the smooth curve plus round white handles (blue ring) at the editable anchors."""
        if len(stroke.points) >= 2 and not view.suppress_guides:
            self._draw_polyline(p, stroke.points, ACCENT_BRIGHT, 1.0, dashed=True, alpha=220)

        anchors = stroke.anchors if stroke.anchors else stroke.points
        p.setPen(QPen(QColor(ACCENT), 1.5))
        for i, (px, py) in enumerate(anchors):
            cx, cy = self._image_to_canvas(px, py)
            is_selected = i == view.selected_anchor_index
            radius = 6.0 if is_selected else 4.0
            p.setBrush(QColor(CANVAS_DRAWING) if is_selected else QColor(ANCHOR_FILL))
            p.drawEllipse(QPointF(cx, cy), radius, radius)
```

In `brush_watermark/ui/design_tokens.py`, delete the `CANVAS_ANCHOR_OUTLINE = "#000000"` line; nothing uses it any more. Confirm with `grep -rn CANVAS_ANCHOR_OUTLINE brush_watermark tests`, which should print nothing.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add brush_watermark/ui/canvas_overlays.py brush_watermark/ui/canvas.py brush_watermark/ui/design_tokens.py tests/test_canvas_overlays.py
git commit -m "Add canvas overlay panels, dotted canvas background and new anchor handles"
```

---

### Task 9: Filmstrip restyle

**Files:**
- Rewrite: `brush_watermark/ui/filmstrip.py`
- Modify: `brush_watermark/ui/main_window.py` (the `filmstrip` import and `_build_filmstrip_thumbnails`)
- Create: `tests/test_filmstrip.py`

**Interfaces:**
- Consumes: tokens, `mono_font`, `get_pixmap`
- Produces:
  - Constants `THUMB_W = 98`, `THUMB_H = 66`, `FILMSTRIP_HEIGHT = 100`
  - `FilmstripWidget(QFrame)`: signal `imageSelected(int)`; methods `set_thumbnails(list[QPixmap])`, `set_active_index(int)`, `set_dirty_flags(list[bool])`, `items() -> list`. Each item has `_active`, `_dirty` and `_number`.
  - This replaces `THUMB_SIZE`.

- [ ] **Step 1: Write the failing tests** (`tests/test_filmstrip.py`)

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest

from brush_watermark.ui.filmstrip import FILMSTRIP_HEIGHT, FilmstripWidget


def make_strip(count: int) -> FilmstripWidget:
    strip = FilmstripWidget()
    pixmaps = []
    for _ in range(count):
        pixmap = QPixmap(98, 66)
        pixmap.fill(Qt.GlobalColor.gray)
        pixmaps.append(pixmap)
    strip.set_thumbnails(pixmaps)
    return strip


def test_items_are_numbered(qapp):
    strip = make_strip(3)
    assert [item._number for item in strip.items()] == [1, 2, 3]
    assert strip.height() == FILMSTRIP_HEIGHT


def test_active_and_dirty_flags(qapp):
    strip = make_strip(3)
    strip.set_active_index(1)
    strip.set_dirty_flags([False, True, False])
    assert [i._active for i in strip.items()] == [False, True, False]
    assert [i._dirty for i in strip.items()] == [False, True, False]


def test_click_emits_index(qapp):
    strip = make_strip(2)
    strip.show()
    seen = []
    strip.imageSelected.connect(seen.append)
    QTest.mouseClick(strip.items()[1], Qt.MouseButton.LeftButton)
    assert seen == [1]


def test_set_thumbnails_replaces_items(qapp):
    strip = make_strip(3)
    strip.set_thumbnails([QPixmap(98, 66)])
    assert len(strip.items()) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_filmstrip.py`
Expected: FAIL (`FILMSTRIP_HEIGHT` / `items` don't exist).

- [ ] **Step 3: Rewrite `brush_watermark/ui/filmstrip.py`**

```python
"""Bottom strip for switching between open images (shown with 2+ images)."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QWidget

from brush_watermark.ui.app_fonts import mono_font
from brush_watermark.ui.design_tokens import ACCENT_BRIGHT, ACCENT_TEXT, BORDER, BORDER_HOVER, SHADOW, TEXT, WARNING
from brush_watermark.ui.icons import get_pixmap

THUMB_W = 98
THUMB_H = 66
RING = 4  # room around each thumbnail for the active ring
FILMSTRIP_HEIGHT = 100


class _FilmstripItem(QWidget):
    clicked = Signal()

    def __init__(self, pixmap, number: int, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._number = number
        self._active = False
        self._dirty = False
        self._hover = False
        self.setFixedSize(THUMB_W + 2 * RING, THUMB_H + 2 * RING)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Image {number}")

    def set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self.update()

    def set_dirty(self, dirty: bool) -> None:
        if dirty != self._dirty:
            self._dirty = dirty
            self.setToolTip(f"Image {self._number}" + (" · unsaved changes" if dirty else ""))
            self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _badge_brush(self) -> QColor:
        color = QColor(SHADOW)
        color.setAlphaF(0.7)
        return color

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        thumb = QRectF(RING, RING, THUMB_W, THUMB_H)

        clip = QPainterPath()
        clip.addRoundedRect(thumb, 8, 8)
        painter.save()
        painter.setClipPath(clip)
        ratio = self._pixmap.devicePixelRatio() or 1.0
        pw, ph = self._pixmap.width() / ratio, self._pixmap.height() / ratio
        painter.drawPixmap(int(RING + (THUMB_W - pw) / 2), int(RING + (THUMB_H - ph) / 2), self._pixmap)
        painter.restore()

        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._active:
            painter.setPen(QPen(QColor(ACCENT_BRIGHT), 2))
            painter.drawRoundedRect(thumb.adjusted(-2, -2, 2, 2), 10, 10)
        else:
            painter.setPen(QPen(QColor(BORDER_HOVER if self._hover else BORDER), 1))
            painter.drawRoundedRect(thumb.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._badge_brush())
        label = str(self._number)
        badge = QRectF(RING + 4, RING + THUMB_H - 20, 16 if len(label) < 2 else 22, 16)
        painter.drawRoundedRect(badge, 4, 4)
        painter.setPen(QColor(TEXT))
        painter.setFont(mono_font(10))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)

        if self._dirty:
            dot_badge = QRectF(RING + THUMB_W - 20, RING + 4, 16, 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._badge_brush())
            painter.drawRoundedRect(dot_badge, 4, 4)
            painter.setBrush(QColor(WARNING))
            painter.drawEllipse(dot_badge.center(), 3, 3)
        painter.end()


class FilmstripWidget(QFrame):
    """Images title plus a horizontally scrolling row of thumbnails."""

    imageSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Filmstrip")
        self.setFixedHeight(FILMSTRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(14)

        title = QWidget()
        title.setFixedWidth(92)
        title_row = QHBoxLayout(title)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(7)
        icon = QLabel()
        icon.setPixmap(get_pixmap("images", 14, ACCENT_TEXT))
        text = QLabel("Images")
        text.setObjectName("FilmstripTitle")
        title_row.addWidget(icon)
        title_row.addWidget(text)
        title_row.addStretch(1)
        row.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("FilmstripScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self._layout = QHBoxLayout(container)
        self._layout.setContentsMargins(4, 0, 4, 0)
        self._layout.setSpacing(10)
        self._layout.addStretch(1)
        self._scroll.setWidget(container)
        row.addWidget(self._scroll, 1)

        self._items: list[_FilmstripItem] = []

    def items(self) -> list[_FilmstripItem]:
        return list(self._items)

    def set_thumbnails(self, pixmaps: list) -> None:
        for item in self._items:
            item.setParent(None)
            item.deleteLater()
        self._items = []
        for idx, pixmap in enumerate(pixmaps):
            item = _FilmstripItem(pixmap, idx + 1)
            item.clicked.connect(lambda i=idx: self.imageSelected.emit(i))
            self._layout.insertWidget(idx, item)
            self._items.append(item)

    def set_active_index(self, index: int) -> None:
        for i, item in enumerate(self._items):
            item.set_active(i == index)

    def set_dirty_flags(self, flags: list) -> None:
        for item, dirty in zip(self._items, flags):
            item.set_dirty(dirty)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y() or event.angleDelta().x()
        bar = self._scroll.horizontalScrollBar()
        bar.setValue(bar.value() - delta)
        event.accept()
```

- [ ] **Step 4: Update the thumbnail builder in `main_window.py`**

Change the import `from brush_watermark.ui.filmstrip import THUMB_SIZE, FilmstripWidget` to:

```python
from brush_watermark.ui.filmstrip import THUMB_H, THUMB_W, FilmstripWidget
```

and in `_build_filmstrip_thumbnails` replace the `.scaled(...)` call with:

```python
            pixmap = pil_to_qpixmap(doc.original).scaled(
                THUMB_W,
                THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add brush_watermark/ui/filmstrip.py brush_watermark/ui/main_window.py tests/test_filmstrip.py
git commit -m "Restyle the filmstrip"
```

---

### Task 10: Wire everything into MainWindow and remove the old sidebar

**Files:**
- Modify: `brush_watermark/ui/main_window.py`, `brush_watermark/services/document.py`, `brush_watermark/ui/design_tokens.py`
- Delete: `brush_watermark/ui/sidebar.py`, `brush_watermark/ui/lightroom_controls.py`
- Create: `tests/test_main_window.py`, `tests/test_design_rules.py`

**Interfaces:**
- Consumes everything from Tasks 1–9. The exact names are listed in each task's Interfaces block.
- Produces `MainWindow` attributes `top_bar`, `tool_rail`, `canvas_area`, `inspector`, `inspector_scroll`, `footer` (plus the existing `canvas`, `canvas_scroll`, `filmstrip`, `save_all_action`), and the method `on_layer_visibility_toggled(index: int)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_design_rules.py`:

```python
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
```

`tests/test_main_window.py`:

```python
"""Offscreen smoke tests for the redesigned MainWindow wiring."""
import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenuBar

from brush_watermark.models import Settings, Stroke, ToolMode
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.document import load_documents
from brush_watermark.ui.main_window import MainWindow


@pytest.fixture
def make_window(qapp, tmp_path, monkeypatch):
    # Never touch the real settings file or the network from tests.
    monkeypatch.setattr("brush_watermark.ui.main_window.save_settings", lambda *_a, **_k: None)
    monkeypatch.setattr(MainWindow, "_start_update_check", lambda self: None)
    windows = []

    def _make(count: int = 1) -> MainWindow:
        paths = []
        for i in range(count):
            path = tmp_path / f"img{i}.jpg"
            Image.new("RGB", (320, 200), (90 + i * 20, 120, 150)).save(path)
            paths.append(path)
        docs, errors = load_documents(paths, Settings())
        assert errors == []
        window = MainWindow(docs)
        window.resize(1440, 960)
        window.show()
        qapp.processEvents()
        windows.append(window)
        return window

    yield _make
    for window in windows:
        window.close()


def add_stroke(window: MainWindow) -> None:
    points = [(20.0, 20.0), (250.0, 150.0)]
    window.doc.strokes.append(
        Stroke(name="Stroke 1", points=list(points), anchors=list(points), brush_size=40, opacity=50)
    )
    window.refresh_stroke_list()


def test_single_image_layout(make_window):
    window = make_window()
    assert window.findChild(QMenuBar) is None
    assert window.filmstrip.isHidden()
    assert window.top_bar.index_badge.isHidden()
    assert not window.top_bar.save_all_action.isVisible()
    assert window.top_bar.file_name_label.text() == "img0.jpg"


def test_multi_image_layout(make_window):
    window = make_window(3)
    assert not window.filmstrip.isHidden()
    assert len(window.filmstrip.items()) == 3
    assert window.top_bar.index_badge.text() == "1 / 3"
    assert window.top_bar.save_all_action.isVisible()


def test_tool_rail_and_keys_switch_tools(make_window):
    window = make_window()
    window.tool_rail.buttons[ToolMode.PATH].click()
    assert window.active_tool == ToolMode.PATH
    assert window.canvas_area.hint_pill.tool_label.text() == "Path"
    QTest.keyClick(window, Qt.Key.Key_V)
    assert window.active_tool == ToolMode.POINTER
    assert window.tool_rail.buttons[ToolMode.POINTER].isChecked()


def test_preview_toggle_shows_original(make_window):
    window = make_window()
    window.top_bar.preview_toggle.setCurrentIndex(0)
    assert window.get_canvas_view().show_original is True


def test_zoom_pill_switches_to_actual_size(make_window):
    window = make_window()
    window.canvas_area.zoom_pill.one_to_one_btn.click()
    assert window.zoom_is_fit is False


def test_eye_toggle_hides_layer(make_window):
    window = make_window()
    add_stroke(window)
    window.doc.dirty = False
    window.inspector.layer_list.rows()[0].eye.click()
    assert window.doc.strokes[0].visible is False
    assert window.doc.dirty is True
    assert window.inspector.layer_list.rows()[0].eye.toolTip() == "Show layer"


def test_layer_click_selects_and_badge_counts(make_window):
    window = make_window()
    add_stroke(window)
    assert window.inspector.layer_count_badge.text() == "1"
    window.inspector.layer_item_clicked.emit(0)
    assert window.doc.selected_stroke_index == 0
    assert window.inspector.layer_list.rows()[0].property("selected") is True


def test_labels_follow_brush_size(make_window):
    window = make_window()
    window.inspector.brush_row.slider.setValue(80)
    assert window.canvas_area.brush_readout.size_label.text() == "80 px"
    assert window.inspector.font_px_chip.text() == f"{font_size_from_brush(80)} px"


def test_unsaved_indicator_follows_dirty(make_window):
    window = make_window()
    add_stroke(window)
    window.doc.dirty = True
    window.schedule_preview(1)
    assert not window.top_bar.unsaved_indicator.isHidden()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_main_window.py tests/test_design_rules.py`
Expected: FAIL. `MainWindow` has no `top_bar`, and `sidebar.py` still exists.

- [ ] **Step 3: Update imports in `main_window.py`**

- Remove `QListWidgetItem` from the `PySide6.QtWidgets` import.
- Remove the `sidebar` import.
- Add `from brush_watermark.rendering.blend import blend_mode_label`.
- Add the new widget imports:

```python
from brush_watermark.ui.canvas_overlays import CanvasArea
from brush_watermark.ui.inspector import INSPECTOR_WIDTH, InspectorPanel
from brush_watermark.ui.layer_list import LayerItem
from brush_watermark.ui.status_footer import StatusFooter
from brush_watermark.ui.tool_rail import ToolRail
from brush_watermark.ui.top_bar import TopBar
```

In `__init__`, change the two build calls so the top bar exists before the menus are added:

```python
        self._build_ui()
        self._build_menu_bar()
        self._connect_signals()
```

- [ ] **Step 4: Replace `self.menuBar().addMenu(` with the top bar**

In `_build_menu_bar`, replace each of the three calls:

```python
        file_menu = self.top_bar.add_menu("&File")
        ...
        tools_menu = self.top_bar.add_menu("&Tools")
        ...
        help_menu = self.top_bar.add_menu("&Help")
```

Everything else in `_build_menu_bar` stays the same.

- [ ] **Step 5: Replace `_build_ui` and `_connect_signals`**

```python
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("AppRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        self.tool_rail = ToolRail()
        body.addWidget(self.tool_rail)

        self.canvas = CanvasWidget(
            get_view=self.get_canvas_view,
            image_to_canvas=self.image_to_canvas_xy,
            inside_image=self.inside_image_canvas,
            on_left_press=self.start_left_interaction,
            on_left_move=self.continue_left_interaction,
            on_left_release=self.finish_left_interaction,
            on_right_press=self.start_right_interaction,
            on_right_move=self.continue_right_interaction,
            on_right_release=self.finish_right_interaction,
            on_wheel=self.handle_wheel,
            on_pointer_move=self._on_pointer_move,
            on_pointer_leave=self._on_pointer_leave,
            text_span_info=self.doc.text_span_info,
            on_double_click=self.handle_double_click,
        )
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setObjectName("CanvasScrollArea")
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_area = CanvasArea(self.canvas_scroll)
        self.canvas_area.hint_pill.set_tool(self.active_tool)

        self.filmstrip = FilmstripWidget()
        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(0)
        center.addWidget(self.canvas_area, 1)
        center.addWidget(self.filmstrip)
        body.addLayout(center, 1)

        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setObjectName("InspectorScroll")
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inspector_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.inspector_scroll.setFixedWidth(INSPECTOR_WIDTH)
        self.inspector = InspectorPanel(self.doc.settings, self.swatch_colors)
        self.inspector_scroll.setWidget(self.inspector)
        body.addWidget(self.inspector_scroll)

        self.footer = StatusFooter()
        root.addWidget(self.footer)

    def _connect_signals(self):
        ins = self.inspector
        ins.document_settings_changed.connect(self.document_settings_changed)
        ins.stroke_controls_changed.connect(self.stroke_controls_changed)
        ins.layer_item_clicked.connect(self.on_layer_item_clicked)
        ins.layer_visibility_toggled.connect(self.on_layer_visibility_toggled)
        ins.delete_selected.connect(self.delete_selected_stroke)
        ins.delete_all.connect(self.clear_all)
        ins.guide_suppress_changed.connect(self.set_guide_suppressed)
        ins.auto_place_requested.connect(self.start_auto_watermark)
        self.top_bar.save_and_close.connect(self.save_and_close)
        self.top_bar.save_copy_and_close.connect(self.save_copy_and_close)
        self.top_bar.save_all_and_close.connect(self.save_all_and_close)
        self.top_bar.exit_without_saving.connect(self.exit_without_saving)
        self.top_bar.preview_changed.connect(lambda _original: self.on_preview_mode_changed())
        self.tool_rail.tool_changed.connect(self.set_active_tool)
        self.tool_rail.auto_place_requested.connect(lambda: self.start_auto_watermark(ins.density()))
        self.canvas_area.zoom_pill.zoom_mode_changed.connect(self.on_zoom_mode_changed)
        self.footer.update_now.connect(self.start_auto_update)
        self.filmstrip.imageSelected.connect(self.switch_active_document)
```

- [ ] **Step 6: Replace the list/label/document-UI methods**

Replace `update_labels`, `sync_list_selection` and `refresh_stroke_list` with:

```python
    def update_labels(self):
        ins = self.inspector
        controls = ins.read_stroke_controls()
        brush = controls["brush_size"]
        strength = f"{controls['opacity']}%"
        ins.opacity_row.set_value_text(strength)
        ins.brush_row.set_value_text(f"{brush} px")
        ins.softness_row.set_value_text(f"{controls['mask_softness']} px")
        ins.set_font_px(font_size_from_brush(brush))
        ins.set_delete_enabled(self._layer_selected())
        self.canvas_area.brush_readout.set_values(
            controls["text_color"], brush, strength, blend_mode_label(controls["blend_mode"])
        )
        self.canvas_area.refresh_overlays()

    def sync_list_selection(self):
        self.inspector.set_selected_layer(self.doc.selected_stroke_index if self._layer_selected() else -1)

    def refresh_stroke_list(self):
        items = [
            LayerItem(stroke.name, self.doc.stroke_meta_text(stroke), stroke.visible)
            for stroke in self.doc.strokes
        ]
        selected = self.doc.selected_stroke_index if self._layer_selected() else -1
        self.inspector.set_layers(items, selected)

    def on_layer_visibility_toggled(self, index: int) -> None:
        if not 0 <= index < len(self.doc.strokes):
            return
        stroke = self.doc.strokes[index]
        self.doc.set_stroke_visible(index, not stroke.visible)
        self.refresh_stroke_list()
        if index == self.doc.selected_stroke_index:
            self.inspector.set_brush_context(layer_name=stroke.name, visible=stroke.visible)
        self.schedule_preview()
```

Replace `_update_filmstrip_dirty_flags` with the method below, and rename its one caller in `schedule_preview` to match:

```python
    def _update_dirty_indicators(self) -> None:
        flags = [doc.dirty for doc in self.docs]
        self.filmstrip.set_dirty_flags(flags)
        self.top_bar.set_unsaved(self.doc.dirty)
        self.top_bar.set_multi_document_mode(len(self.docs) > 1, sum(flags))
```

Replace `_refresh_document_list_ui` and `_load_active_document_into_ui` with:

```python
    def _refresh_document_list_ui(self) -> None:
        """Rebuild the filmstrip and toggle the multi-image-only UI after docs change."""
        multi = len(self.docs) > 1
        self.filmstrip.set_thumbnails(self._build_filmstrip_thumbnails())
        self.filmstrip.setVisible(multi)
        self.filmstrip.set_active_index(self.active_index)
        self.save_all_action.setVisible(multi)
        self._refresh_file_info()
        self._update_dirty_indicators()

    def _refresh_file_info(self) -> None:
        doc = self.doc
        self.top_bar.set_file_info(doc.image_path.name, doc.metadata.serial, self.active_index, len(self.docs))

    def _load_active_document_into_ui(self) -> None:
        """Point the title, swatches, stroke list and controls at the active doc."""
        doc = self.doc
        self.setWindowTitle(f"{APP_NAME} - {doc.image_path.name}")
        self.swatch_colors = build_swatch_palette(doc.original)
        self.inspector.set_swatches(self.swatch_colors, doc.settings.text_color)
        self._refresh_file_info()
        self.selected_anchor_index = -1
        self.anchor_drag_active = False
        self.refresh_stroke_list()
        if self._layer_selected():
            self.inspector.load_stroke_controls(doc.strokes[doc.selected_stroke_index])
        else:
            self.inspector.load_tool_defaults(doc.settings)
        self.update_labels()
        self.schedule_preview(1)
```

`_refresh_document_list_ui` runs in `__init__` after `_build_menu_bar`, so `self.save_all_action` exists by then. In `switch_active_document`, the `self.filmstrip.set_active_index(index)` line stays. After it, `_load_active_document_into_ui()` refreshes the file info.

- [ ] **Step 7: Replace the remaining `sidebar` references**

Apply each replacement below, then run `grep -n "sidebar" brush_watermark/ui/main_window.py`. It must print nothing.

| Find | Replace with |
|---|---|
| `self.sidebar.show_original_preview()` (3×) | `self.top_bar.show_original()` |
| `self.sidebar.set_version_info(` | `self.footer.set_version_info(` |
| `self.sidebar.set_update_progress(` | `self.footer.set_update_progress(` |
| `self.sidebar.clear_update_progress(` | `self.footer.clear_update_progress(` |
| `self.sidebar.set_auto_watermark_running(` / `set_auto_watermark_status(` | `self.inspector.` (same method) |
| `self.sidebar.load_tool_defaults(` / `load_stroke_controls(` / `read_stroke_controls(` / `read_tool_defaults(` / `read_document_settings(` | `self.inspector.` (same method) |
| `self.sidebar.brush_row.slider` | `self.inspector.brush_row.slider` |
| `self.sidebar.reveal_in_explorer_check.isChecked()` | `self.inspector.reveal_in_explorer_check.isChecked()` |
| `sb = self.sidebar` (in `handle_wheel`) | `sb = self.inspector` |
| `def _sync_document_settings_from_sidebar` / `_sync_tool_defaults_from_sidebar` (definitions and the calls in `_commit_sidebar_settings`) | `_sync_document_settings_from_inspector` / `_sync_tool_defaults_from_inspector` |
| `_commit_sidebar_settings` (definition and every call) | `_commit_inspector_settings` |

In `set_active_tool`, replace `self.sidebar.set_active_tool(self.active_tool)` with:

```python
        self.tool_rail.set_active_tool(self.active_tool)
        self.canvas_area.hint_pill.set_tool(self.active_tool)
        self.canvas_area.refresh_overlays()
```

In `refresh_preview`, after the `if self.zoom_is_fit: ... else: self.scale = 1.0` block, add:

```python
        self.canvas_area.zoom_pill.set_zoom_percent(round(self.scale * 100))
```

In `switch_active_document`, remove any leftover `self.sidebar.set_image_context(...)`: `_load_active_document_into_ui` now covers it.

- [ ] **Step 8: Remove the old modules and leftovers**

```bash
git rm brush_watermark/ui/sidebar.py brush_watermark/ui/lightroom_controls.py
```

- In `brush_watermark/services/document.py`, delete `stroke_list_text`.
- Then run `grep -n "color_short\|blend_mode_short" brush_watermark/services/document.py`, and remove either name from the imports if it's no longer used in that file.
- In `brush_watermark/ui/design_tokens.py`, delete the whole "Legacy names…" block (`PANEL` … `TRACK`).
- Then run `grep -rnE "\b(PANEL|INPUT|BUTTON_HOVER|ACCENT_PRESSED|SELECTION|SELECTION_BORDER|LINK|SLIDER_HANDLE|TRACK)\b" brush_watermark --include=*.py`. It must print nothing.

- [ ] **Step 9: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass, including `test_main_window.py` (9 tests) and `test_design_rules.py` (2 tests).

- [ ] **Step 10: Commit**

```bash
git add -A brush_watermark tests
git commit -m "Switch MainWindow to the redesigned layout and remove the old sidebar"
```

---

### Task 11: Docs, TODO list and manual verification

**Files:**
- Rewrite: `brush_watermark/ui/DESIGN.md`
- Modify: `CLAUDE.md`, `README.md`
- Create: `docs/TODO-ui.md`

- [ ] **Step 1: Write `docs/TODO-ui.md`**

```markdown
# UI redesign — deferred features

The redesign (docs/superpowers/specs/2026-09-24-ui-redesign-design.md) shows these controls, but the app has no feature behind them yet. They were left out of the UI rather than drawn as dead buttons. Decide per item whether to build it.

| Control in the design | Where it would go | What's missing |
|---|---|---|
| Undo / Redo | Top bar, centre-left | No edit history in `Document` |
| Pan tool (H), Space-to-pan | Tool rail | No free panning; the canvas is fit or 1:1 with scrollbars |
| Zoom tool (Z), zoom −/+, editable % | Tool rail; zoom pill | Only Fit / 1:1 exist; % is read-only |
| Pick colour from image (I) | Brush swatches, dashed "+" swatch | No eyedropper on the canvas |
| Add images tile | Filmstrip, after the thumbnails | Images only arrive via CLI/Explorer/picker at launch |
| Prev / next image buttons, Ctrl+←/→ | Filmstrip title column; footer hint | Only clicking a thumbnail switches images |
| Copy serial button | Top bar serial chip | Serial is display-only |
| Edit menu | Top bar menus | Nothing to put in it until undo/redo exists |
| Ctrl+S shortcut | Save menu "Ctrl S" badge | No keyboard shortcut for saving |
| Del deletes the selected layer | Layers "Delete" button badge; footer hint | Del only removes a Path anchor |
```

- [ ] **Step 2: Rewrite `brush_watermark/ui/DESIGN.md`**

````markdown
# Brush Watermark — UI design

A modern dark editor (spec: `docs/superpowers/specs/2026-09-24-ui-redesign-design.md`). The layout has five parts:
- a top bar with menus, file info, the Original/Watermarked toggle and save actions
- a left tool rail
- the canvas with floating panels
- a filmstrip, shown with 2+ images
- a right inspector and a status footer

## Color palette

All UI colours live in `design_tokens.py`; use tokens only, never hex literals (enforced by `tests/test_design_rules.py`). `rgba(token, alpha)` builds translucent QSS colours (accent tints, the floating panel background).

| Token | Hex | Use |
|---|---|---|
| `CANVAS_BG` / `CANVAS_DOT` | `#0E0F11` / `#1C1E22` | Canvas background and its 20 px dot grid |
| `CHROME` | `#17181B` | Top bar, tool rail, inspector, filmstrip; floating panels at 92 % |
| `FOOTER_BG` | `#131416` | Status footer |
| `SURFACE_INPUT` | `#1F2125` | Text fields, combos, stepper, value chip, layer-row hover |
| `SURFACE_RAISED` / `_HOVER` | `#23252A` / `#2A2D33` | Secondary buttons, badges, layer icon tile, rail hover / menu hover |
| `SURFACE_MENU` | `#1D1F23` | Menus, popups, tooltips, key badges |
| `SURFACE_SEGMENT` / `_ON` | `#111214` / `#2E3137` | Segmented control track / checked segment |
| `BORDER` | `#2C2F35` | Field and panel borders, scrollbar handles |
| `BORDER_STRONG` | `#33363C` | Secondary buttons, chips, menu borders, slider track |
| `BORDER_HOVER` | `#44474E` | Hovered thumbnail border |
| `DIVIDER` | `#25272C` | Area separators, section dividers, ghost-button hover |
| `KEY_BADGE_BORDER` | `#34373D` | Key badge border |
| `SWITCH_OFF` | `#3A3D44` | Toggle switch track when off |
| `TEXT` | `#ECEDEF` | Primary text and values |
| `TEXT_BODY` | `#D5D7DB` | Switch labels |
| `TEXT_SECONDARY` | `#B4B7BE` | Menu buttons, hints, readout |
| `TEXT_LABEL` | `#A1A4AB` | Control names, layer meta, footer text, unchecked icons |
| `TEXT_MUTED` | `#80848C` | Chevrons, muted icons, disabled text |
| `TEXT_FAINT` | `#4A4E55` | Readout slashes, hidden-layer text |
| `ICON_DISABLED` | `#6E727A` | Hidden-layer eye icon |
| `ACCENT` / `ACCENT_HOVER` | `#3563E9` / `#2C56D4` | Primary/split buttons, logo, switch on, slider thumb ring, anchor ring |
| `ACCENT_BRIGHT` | `#5B8CFF` | Slider fill, focus border, active thumbnail ring, selection guide; tints at 10–50 % |
| `ACCENT_TEXT` | `#9DBBFF` | Checked rail/chip/pill text & icons, section icons, hint tool name |
| `ON_ACCENT` / `SLIDER_THUMB` | `#FFFFFF` | Text/icons on accent fills / slider thumb |
| `WARNING` | `#E0B25C` | Unsaved indicator, filmstrip unsaved dot, "update available" dot |
| `SUCCESS` | `#4CC38A` | "Up to date" dot |
| `DANGER_TEXT` | `#F2A7A0` | "Clear all" |
| `SHADOW` | `#000000` | Drop shadows, thumbnail badges |
| `HANDLE`, `ANCHOR_FILL`, `CANVAS_*` | — | Canvas overlays drawn over photos (guides, anchors, brush cursor, span markers) |

## Type

Geist (UI) and Geist Mono (values, badges, key hints), bundled in `assets/fonts/` under the SIL OFL 1.1 (`OFL.txt`) and registered by `app_fonts.register_app_fonts()` at startup. Body 13 px; labels 11–12 px; section titles and the hint tool name are 600, buttons 500.

## Controls (`controls.py`)

- **`SliderRow`**: the name sits at the left and the mono value at the right, with an optional header widget (e.g. the Strength **Auto** chip) just before the value. Below them is an `AccentSlider` (4 px track, `ACCENT_BRIGHT` fill, white thumb with an `ACCENT` ring).
- **`SwitchRow`**: a label plus a painted `ToggleSwitch`, and clicking the label toggles it. Use it for on/off settings instead of checkboxes.
- **`SegmentedControl`**: an exclusive pill of buttons (Original | Watermarked).
- **`Chip`**: a small checkable pill. **`Stepper`**: a −/value/+ integer control. **`SplitButton`**: a primary button with a menu chevron.
- **`KeyBadge` / `KeyCombo` / `KeyHint`**: keyboard-key badges (`"Alt+Wheel"` → [Alt] + [Wheel]).
- **`CollapsibleSection`**: an inspector section (accent icon, bold title, optional header widget such as a count badge, chevron at the right). Every section starts expanded except **Export**. Collapse state isn't persisted.
- **`make_menu()`**: every `QMenu` must come from this so its rounded corners render.

## Icons

Lucide (ISC, `assets/icons/LICENSE-ICONS.txt`), shipped with `stroke="currentColor"` and recoloured by `icons.py` (`get_icon`, `get_pixmap`, `get_icon_checkable` for checked/unchecked colours). `chevron-down-static.png` is a pre-rendered PNG for the `QComboBox::down-arrow` rule. QSS can't recolour SVGs, and the packaged build drops the `qsvg` plugin.

## Do not

- Hard-code hex colours in widgets, or use accent colours for static chrome, panel backgrounds or body text.
- Draw a control whose feature doesn't exist. Add it to `docs/TODO-ui.md` instead.
- Create a `QMenu` without `make_menu()`, or write a literal `&` in button/action text: use `&&`.
- Put a slider's value in the same label as its name.
- Use heavy card borders. Sections are separated by a single `DIVIDER` line.

## Files

| File | Role |
|---|---|
| `design_tokens.py` | Colours + `rgba()` |
| `app_fonts.py` | Bundled font registration and font helpers |
| `styles.py` | Global Qt stylesheet (object-name based) |
| `controls.py` | Shared custom controls (above) |
| `top_bar.py`, `tool_rail.py`, `inspector.py`, `layer_list.py`, `canvas_overlays.py`, `filmstrip.py`, `status_footer.py` | The window's areas |
| `icons.py` | SVG icon loading, recolouring, caching |
````

- [ ] **Step 3: Update `CLAUDE.md`**

In the `brush_watermark/ui/` bullet, replace the text from ``wires `CanvasWidget` `` up to ``no MVVM/MVC framework.`` with:

```markdown
wires `CanvasWidget` (image preview + overlay painting, `canvas.py`) into a layout of `TopBar` (menus, file info, Original/Watermarked toggle, save actions — `top_bar.py`), `ToolRail` (`tool_rail.py`), `CanvasArea` with floating hint/zoom/brush panels (`canvas_overlays.py`), `FilmstripWidget` (`filmstrip.py`), `InspectorPanel` (settings and the layer list — `inspector.py`, `layer_list.py`) and `StatusFooter` (`status_footer.py`) via plain Qt signals — there's no MVVM/MVC framework.
```

In the **UI design system** paragraph:
- Replace ``lightroom_controls.py` holds shared custom-painted widgets (`CollapsibleSection` accordion, `LightroomSlider`, `BoxCheckBox`, `SliderRow`)`` with ``controls.py` holds shared custom controls (`CollapsibleSection`, `SliderRow`/`AccentSlider`, `SwitchRow`, `SegmentedControl`, `Chip`, `Stepper`, `SplitButton`, key badges, `make_menu`); `app_fonts.py` registers the bundled Geist fonts (`assets/fonts/`, SIL OFL)``.
- Add after the `DESIGN.md` sentence: `Design controls with no feature behind them are tracked in `docs/TODO-ui.md` rather than drawn.`

- [ ] **Step 4: Update `README.md`**

- Replace the Features bullet `- **Menu bar** — File, Tools (Windows Explorer shortcut), and Help actions` with `- **Modern dark editor** — top bar with File/Tools/Help menus and save actions, tool rail, floating tool hints and zoom controls, collapsible inspector, and a shortcut footer`.
- Also add `- **Layer visibility** — hide or show individual watermark strokes from the layer list (hidden strokes aren't saved)`.
- Rename `### Menu bar` to `### Menus`. Keep its bullets, but change the File bullet to `- **File** — Save & Close, Save Copy & Close, Save All & Close (with several images), Exit Without Saving (also available from the top bar's Exit, Save copy and Save & close buttons)`.
- Replace the whole `### Sidebar` section, up to but not including `### Settings file`, with:

```markdown
### Window layout

A modern dark editor — see [`brush_watermark/ui/DESIGN.md`](brush_watermark/ui/DESIGN.md) for the full UI spec.

- **Top bar** — menus, the current file name, camera serial and image index, an **Unsaved** indicator, the **Original | Watermarked** preview toggle, and **Exit**, **Save copy** and **Save & close** (its menu adds **Save all & close** when several images are open)
- **Tool rail** — Select (V), Brush (B), Path (A), Eraser (E), **Auto-place watermarks**, and a keyboard-shortcuts popup
- **Canvas** — floating hints for the current tool, **Fit / 1:1** zoom with the current zoom %, and a readout of the brush colour, size, strength and blend mode
- **Inspector**
  - **Watermark** — text, font (its size follows the brush), auto-fit, and repeat along stroke with a gap
  - **Brush** — colour, blend mode, strength (with **Auto** strength, which computes opacity from the underlying pixels), size and softness. These set **tool defaults** when nothing is selected, or edit the **selected layer** (the section title shows `Layer · …`)
  - **Auto watermark** — density and **Auto-place**
  - **Layers** — each stroke with an eye toggle to hide it; **Delete** or **Clear all**
  - **Export** — visible metadata strip, extra copy text, and **Show in Explorer after save**
- **Filmstrip** — with several images, numbered thumbnails with an unsaved marker
- **Footer** — common shortcuts, and the version with update status (an **Update to vX** button appears when a new release is available)

**Save & close** overwrites the opened image (JPEG quality 95). **Save copy** writes a new file next to the original, named from the serial and capture date in EXIF when available. **Show in Explorer after save** opens the file's location when done. **Original** shows a clean preview without watermarks or guides. **Exit** discards changes to the image; tool defaults and watermark text are still saved to settings.
```

- [ ] **Step 5: Manual verification against the design**

Run the app with several sample images and compare it with the design (1440×960 artboard, https://claude.ai/artifact/LcCaSKBhuxm4LgMQHQcCjm):

```powershell
.venv\Scripts\python.exe -m brush_watermark (Get-ChildItem C:\Users\erik\Desktop\ExportedImages\FB\*.jpg | Select-Object -First 6 | ForEach-Object FullName)
```

Check the following:
- **Chrome:** the top bar, rail, inspector and footer use the new colours and Geist fonts.
- **Tools:** the tool rail highlights the active tool, and V/B/A/E switch it. The hint pill text changes with the tool.
- **Preview toggle:** Original/Watermarked toggles the preview.
- **Zoom:** Fit/1:1 zoom works, and the % updates.
- **Brush readout:** it tracks the Strength/Size sliders and the mouse wheel.
- **Layers:** draw a stroke. It shows up in Layers; the eye hides and shows it; Delete and Clear all work.
- **Save menu:** the save split-button menu opens right-aligned under the chevron, with rounded corners.
- **Filmstrip:** it shows 6 numbered thumbnails. Clicking one switches the image, and edited images get the amber dot.
- **Footer:** it shows the version or update status.
- **Min size:** at 1180×780 nothing is clipped, and the inspector scrolls.

Fix any visual issue in the relevant task's file, then rerun the tests. Take a screenshot for the record.

- [ ] **Step 6: Run the full suite and commit**

Run: `.venv/Scripts/python.exe -m pytest -q` → all pass.

```bash
git add brush_watermark/ui/DESIGN.md CLAUDE.md README.md docs/TODO-ui.md
git commit -m "Document the redesigned UI and list deferred design features"
```

Leave the branch unpushed; merging into `main` (which releases) is the user's call.
