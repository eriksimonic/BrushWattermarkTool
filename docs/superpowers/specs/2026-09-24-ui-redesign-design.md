# UI redesign — "modern dark" editor

Date: 2026-09-24
Source design: Claude Design canvas "Brush Watermark redesign", artboard "Editor — modern dark" (1440×960), https://claude.ai/artifact/LcCaSKBhuxm4LgMQHQcCjm

## Goal and scope

Rebuild the PySide6 UI to match the design, **for features the app already has**. Controls in the design that need a feature the app doesn't have are left out (not drawn as dead buttons) and listed in `docs/TODO-ui.md` for a later decision. One small addition is in scope: a per-layer visibility (eye) toggle, which only sets the existing `Stroke.visible` field that rendering already honours.

Approach: keep Qt widgets and all canvas/editing logic; replace the design tokens and stylesheet; split today's single `SidebarPanel` into dedicated widgets. No QML, no web view.

## 1. Layout

```
┌ Top bar 52px ─────────────────────────────────────────────────────────────┐
│ logo File Tools Help │ file.jpg #serial 2/6 •Unsaved   [Original|Watermarked]   Exit  Save copy  [Save & close|v] │
├──────┬───────────────────────────────────────────────────┬────────────────┤
│ Tool │ Canvas (dotted bg)                                │ Inspector 340px│
│ rail │            ┌ hint pill: tool · key hints ┐        │  Watermark     │
│ 60px │                                                   │  Brush         │
│  V   │                 [ photo ]                         │  Auto watermark│
│  B   │                                                   │  Layers        │
│  A   │ [Fit 1:1 62%]                [● 41px / 19% / Normal] │  Export (closed)│
│  E   ├───────────────────────────────────────────────────┤                │
│ auto │ Filmstrip 100px (only with 2+ images)             │                │
│  ⌨   │                                                   │                │
├──────┴───────────────────────────────────────────────────┴────────────────┤
│ Footer 30px: shortcut hints · "controls edit the selected layer…" · ● v1.x · status │
└───────────────────────────────────────────────────────────────────────────┘
```

- **Top bar** (replaces the native `QMenuBar`):
  - **Left:** a logo mark, then flat File / Tools / Help menus with the same actions as today (no Edit menu), then the file name, a serial chip, an "n / N" index (only with 2+ images) and an amber "Unsaved" dot when the active doc is dirty.
  - **Centre:** an Original | Watermarked segmented control, which replaces the "Show original" checkbox.
  - **Right:** Exit (ghost), Save copy (secondary), and a Save & close split button (primary). Its menu holds Save & close, Save all & close with an "N edited" count (only with 2+ images), and Save copy & close.
- **Tool rail:**
  - Select V, Brush B, Path A and Eraser E, each with its key letter in the corner.
  - An Auto-place button that runs auto-place at the inspector's density.
  - At the bottom, a keyboard button that pops up the shortcut list (today's Help text).
- **Canvas:** the existing `CanvasWidget` on a dotted `#0E0F11` background, with three floating overlay panels:
  - **Top centre:** a hint pill with the tool name and per-tool key hints.
  - **Bottom left:** a zoom pill with Fit / 1:1 (the existing toggle) and a read-only zoom %.
  - **Bottom right:** a brush readout with the colour dot, size, strength and blend.
  - Anchor handles become white with a blue ring.
- **Filmstrip** (shown only with 2+ images): an "Images" label and 98×66 thumbnails with a number badge and an unsaved-dot badge. The active one gets a blue ring.
- **Inspector** (scrollable, collapsible sections):
  - **Watermark:** text field; font combo plus a read-only "N px" chip (the font follows the brush); an Auto-fit switch; a Repeat switch with a gap stepper.
  - **Brush:** swatches; blend combo; Strength slider with an "Auto" chip (replaces the auto-strength checkbox); Size; Softness.
  - **Auto watermark:** density slider plus an Auto-place button, and a status line.
  - **Layers:** a count badge; rows with an eye toggle, type icon, name and details line; Delete and Clear all.
  - **Export** (collapsed by default): visible metadata strip switch, additional copy info field, "Show in Explorer after save" switch.
- **Footer:** key hints (Wheel = strength, Alt+Wheel = brush size, Dbl-click = add anchor, Del = remove anchor) and the "controls edit the selected layer…" note on the left. The version and update status sit on the right with a green or amber dot; when an update is available the status becomes an "Update to vX" button, and download progress shows there too.

## 2. Visual system

- **Tokens** (`design_tokens.py`, still the only place hex values live):

  | Role | Hex |
  |---|---|
  | Canvas background, dot grid | `#0E0F11`, `#1C1E22` |
  | Chrome (bars, rail, inspector) | `#17181B`; footer `#131416` |
  | Surfaces: field, secondary button, menu | `#1F2125`, `#23252A`, `#1D1F23` |
  | Borders / dividers | `#2C2F35`, `#25272C`, `#33363C` |
  | Text: primary, secondary, label, muted | `#ECEDEF`, `#B4B7BE`, `#A1A4AB`, `#80848C` |
  | Accent: fill, hover, bright, text | `#3563E9`, `#2C56D4`, `#5B8CFF`, `#9DBBFF`; plus a 16 % tint for "on" states |
  | Status: unsaved, up to date, danger text | `#E0B25C`, `#4CC38A`, `#F2A7A0` |

  The canvas overlay colours stay unchanged.
- **Type:** Geist and Geist Mono (SIL OFL 1.1) are bundled in `assets/fonts/` with their licence and registered at startup. Mono is used for values, badges and key hints. Body text is 13 px, labels 11–12 px. If loading fails, the UI falls back to Segoe UI or the system font.
- **Controls:** where QSS can't match the design, the control is custom-painted: toggle switch, slider (4 px track, white thumb with a blue ring), segmented control, chip, key badge, split button, stepper, layer row, and the floating panels (rounded, translucent, shadow). Buttons, fields, combos, menus and scrollbars come from the rewritten `styles.py`, with 8 px corners and 32–34 px heights.
- **Icons:** Lucide as today, adding `eye`, `eye-off`, `keyboard` and `images`.
- `DESIGN.md` is rewritten for the new system.

## 3. Code structure and testing

New or replaced modules in `brush_watermark/ui/`:

| Module | Contents |
|---|---|
| `controls.py` | Replaces `lightroom_controls.py`: `CollapsibleSection`, `SliderRow`/slider, `ToggleSwitch`, `SegmentedControl`, `Chip`, `KeyBadge`, `SplitButton`, `Stepper` |
| `top_bar.py` | `TopBar`: menus, file info, preview toggle, save buttons; emits the save/exit/preview signals |
| `tool_rail.py` | `ToolRail`: `tool_changed(ToolMode)`, `auto_place_requested`, the shortcuts popup |
| `inspector.py` | `InspectorPanel`: replaces `SidebarPanel` and keeps its public API (`load_tool_defaults`, `load_stroke_controls`, `read_document_settings`, `read_stroke_controls`, slider rows, signals) so `MainWindow` logic changes little |
| `layer_list.py` | `LayerList`/`LayerRow`: `layer_clicked(int)`, `visibility_toggled(int)` |
| `canvas_overlays.py` | `HintPill`, `ZoomPill`, `BrushReadout`: children of the canvas viewport, repositioned on resize |
| `status_footer.py` | `StatusFooter`: key hints, version/update status, `update_now` |
| `app_fonts.py` | Registers the bundled fonts |

`filmstrip.py`, `canvas.py`, `styles.py`, `design_tokens.py` and `icons.py` are updated. `sidebar.py` and `lightroom_controls.py` are removed.

- `MainWindow` composes the new widgets. The signal wiring that pointed at `sidebar` moves to the new widgets, and editing/rendering logic is unchanged.
- `Document` gains `set_stroke_visible(idx, visible)`, which marks the doc dirty. The preview cache signature already includes `visible`.
- **Tests:**
  - A unit test for `set_stroke_visible`.
  - Offscreen Qt smoke tests (`QT_QPA_PLATFORM=offscreen`, a tmp JPEG) that build `MainWindow` and check the tool rail, the preview toggle, the eye toggle, and the multi-image extras (filmstrip, Save all, index).
  - A manual run with the sample JPGs, compared against the design by screenshot.
- **Docs:** `CLAUDE.md`, `README.md` and `DESIGN.md` are updated, and `docs/TODO-ui.md` is added.

## Out of scope (→ `docs/TODO-ui.md`)

- Undo/redo
- Pan and Zoom tools (H / Z)
- Zoom −/+ buttons and editable zoom %
- Colour picker that samples the image
- "Add images" tile
- Prev/next image buttons and Ctrl+←/→
- Copy-serial button
- Edit menu
- Ctrl+S shortcut (the design's save menu shows a "Ctrl S" badge)
- Del deletes the selected layer (today Del only removes a Path anchor)
