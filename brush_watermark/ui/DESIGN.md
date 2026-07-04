# Brush Watermark — UI design

The interface follows **Adobe Lightroom Classic** dark panels: neutral gray chrome, label-left / value-right controls, and teardrop slider handles. Do not use navy or blue-gray palette colors anywhere in the UI.

## Color palette

All UI colors live in `design_tokens.py`. Use these tokens only — no hard-coded hex values in widgets.

| Token | Hex | Use |
|-------|-----|-----|
| `CANVAS_BG` | `#2A2A2A` | Image preview surround (dark gray) |
| `CHROME` | `#333333` | Window chrome |
| `PANEL` | `#3B3B3B` | Right sidebar background (Lightroom panel gray) |
| `INPUT` | `#454545` | Text fields, combos, layer list |
| `BORDER` | `#505050` | Control borders |
| `DIVIDER` | `#555555` | Section divider lines |
| `TEXT` | `#D4D4D4` | Primary labels and values |
| `TEXT_SECONDARY` | `#A8A8A8` | Control names, section titles |
| `TEXT_MUTED` | `#808080` | Hints, version, help |
| `SLIDER_HANDLE` | `#F0F0F0` | Slider thumb (off-white circle) |
| `HANDLE` | `#C8C8C8` | Checked checkbox |
| `TRACK` | `#606060` | Slider track |
| `SELECTION` | `#565656` | Selected list row, primary buttons |
| `SELECTION_BORDER` | `#909090` | Focus rings, selection accent |
| `LINK` | `#A8C4DC` | Update links (muted, not bright blue) |

## Control layout (Lightroom copy)

Each numeric control uses the **SliderRow** pattern from `lightroom_controls.py`:

```
Strength                         100%
━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━
```

- **Row 1:** control name left-aligned, formatted value right-aligned
- **Row 2:** full-width slider with off-white circular handle (`LightroomSlider`)
- Sliders are 2px neutral gray tracks; handles are 10px off-white circles

Sections use **SectionHeader**: a centered title with horizontal divider lines on both sides (e.g. `Tone`, `Presence` in Lightroom).

Form fields (text, font, blend) keep a single row: label left, control right.

## Structure

- **Canvas:** `CANVAS_BG` fill; image centered on the matte
- **Sidebar:** fixed width (~320px), `PANEL` background, scrollable
- **Sections:** Watermark → Layers → Brush → actions → footer (version/help)
- **Selection on canvas:** light gray guides (`HANDLE`), not blue

## Do not

- Use navy blues (`#0f172a`, `#111827`, `#2563eb`, `#60a5fa`, etc.)
- Use bright blue primary buttons or list selection
- Put values in the same label as the control name for sliders
- Use card boxes with heavy borders; rely on section dividers instead

## Files

| File | Role |
|------|------|
| `design_tokens.py` | Single source of truth for colors |
| `styles.py` | Global Qt stylesheet |
| `lightroom_controls.py` | SectionHeader, SliderRow, LightroomSlider |
| `sidebar.py` | Panel layout and wiring |
| `canvas.py` | Preview background and overlay colors |
