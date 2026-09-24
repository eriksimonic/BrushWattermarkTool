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
