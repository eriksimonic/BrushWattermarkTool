# Brush Watermark — UI design

The interface follows **Adobe Lightroom Classic** dark panels: neutral gray chrome, label-left / value-right controls, and off-white slider handles — with a blue accent layer for interactive/active states (buttons, checked controls, slider fill, focus rings) and a bundled line-icon set.

## Color palette

All UI colors live in `design_tokens.py`. Use these tokens only — no hard-coded hex values in widgets.

| Token | Hex | Use |
|-------|-----|-----|
| `CANVAS_BG` | `#2A2A2A` | Image preview surround (dark gray) |
| `CHROME` | `#333333` | Window chrome |
| `PANEL` | `#3B3B3B` | Right sidebar background (Lightroom panel gray) |
| `INPUT` | `#454545` | Text fields, combos, layer list |
| `BORDER` | `#505050` | Control borders |
| `DIVIDER` | `#555555` | Unused by current widgets; reserved for future dividers |
| `TEXT` | `#D4D4D4` | Primary labels and values |
| `TEXT_SECONDARY` | `#A8A8A8` | Control names, section titles, section icons |
| `TEXT_MUTED` | `#808080` | Hints, version, help |
| `SLIDER_HANDLE` | `#F0F0F0` | Slider thumb (off-white circle) |
| `HANDLE` | `#C8C8C8` | Unused by current widgets |
| `TRACK` | `#606060` | Slider track (unfilled portion) |
| `SELECTION` | `#565656` | Selected list row |
| `SELECTION_BORDER` | `#909090` | List-row selection border |
| `LINK` | `#A8C4DC` | Update links (muted, not bright blue) |
| `ACCENT` | `#3D7FFF` | Primary buttons, checked checkboxes/tool buttons, slider fill, focus rings |
| `ACCENT_HOVER` | `#5C93FF` | Hover state for accent-filled controls |
| `ACCENT_PRESSED` | `#2E63CC` | Pressed state for accent-filled controls |
| `ON_ACCENT` | `#FFFFFF` | Text/icon color drawn on top of an accent-filled surface |

## Control layout (Lightroom copy)

Each numeric control uses the **SliderRow** pattern from `lightroom_controls.py`:

```
Strength                         100%
━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━
```

- **Row 1:** control name left-aligned, formatted value right-aligned
- **Row 2:** full-width slider (`LightroomSlider`) — `ACCENT`-filled from the left edge to the handle, `TRACK` gray for the remainder, off-white circular handle

Form fields (text, font, blend) keep a single row: label left, control right.

## Sections

Sidebar sections use **CollapsibleSection** (`lightroom_controls.py`): a clickable header row (chevron icon that flips `chevron-right`/`chevron-down`, an optional leading section icon, left-aligned title) above a `body_layout` that callers populate. Clicking the header toggles the body's visibility. All sections default to expanded; collapse state is not persisted between sessions. The **Actions** block (Save/Save copy/Exit, preview checkboxes) is a plain, non-collapsible block — it was never a labeled section and holds primary save actions that shouldn't be hidden behind a toggle.

## Icons

Icons are vendored from [Lucide](https://lucide.dev) (ISC license, see `assets/icons/LICENSE-ICONS.txt`) as raw SVG files under `brush_watermark/assets/icons/`, shipped with `stroke="currentColor"` left in place.

`brush_watermark/ui/icons.py` loads an SVG, substitutes `currentColor` for a real hex color, and rasterizes it via `QSvgRenderer` into a cached `QPixmap`/`QIcon`:

- `get_icon(name, size, color)` / `get_pixmap(name, size, color)` — single-color icon.
- `get_icon_checkable(name, size, off_color, on_color)` — a `QIcon` with distinct `Off`/`On` state pixmaps, for checkable buttons (e.g. the tool buttons swap to `ON_ACCENT` when checked).

One icon, `chevron-down-static.png`, is pre-rendered and committed as a static PNG for the `QComboBox::down-arrow` QSS rule — Qt's stylesheet `image:` property can't recolor an SVG via `currentColor`, and the packaged build drops the `qsvg` imageformat plugin, so a plain PNG is required there specifically.

## Do not

- Use `ACCENT` for static chrome, panel backgrounds, or body text — it's for interactive/active affordances only (primary buttons, checked checkboxes/tool buttons, slider fill, focus rings)
- Use `ACCENT` for list-row selection — keep that neutral (`SELECTION`/`SELECTION_BORDER`)
- Put values in the same label as the control name for sliders
- Use card boxes with heavy borders; rely on the accordion header + spacing instead

## Files

| File | Role |
|------|------|
| `design_tokens.py` | Single source of truth for colors |
| `styles.py` | Global Qt stylesheet |
| `lightroom_controls.py` | CollapsibleSection, SliderRow, LightroomSlider, BoxCheckBox |
| `icons.py` | SVG icon loading, recoloring, rasterizing, caching |
| `sidebar.py` | Panel layout and wiring |
| `canvas.py` | Preview background and overlay colors |
| `color_picker.py` | Swatch picker, accent selection ring |
