# Brush Watermark Tool

Paint subtle, brush-shaped text watermarks directly onto JPG photos. Designed for a Lightroom-style workflow: open an image, draw along the area where the watermark should follow, and save the result back to the same file.

## What it does

Brush Watermark Tool overlays your watermark text along a painted stroke path. The text follows the curve of your brush line, rotates with the path, and can be blended into the image pixels so the mark is harder to notice and remove than a flat semi-transparent overlay.

Each watermark is saved into the image file itself (JPEG). Settings such as default text, font, and tool options are remembered between sessions.

## Features

- **Brush strokes** — paint watermark paths with the mouse; text is laid out along the stroke
- **Per-layer control** — each stroke has its own color, blend mode, strength, brush size, softness, and repeat settings
- **Repeat text** — optionally tile watermark text along long strokes, with adjustable gap
- **Blend modes** — Normal, Soft light, Lighten, Darken, Difference, Overlay, Screen, Multiply, Hard light
- **Image color picker** — 8 colors sampled from the photo, plus white, 50% gray, and black
- **Erase mask** — right-click paint to hide watermark areas without deleting strokes
- **Auto update check** — compares your version to the latest release on GitHub
- **One-click update** — packaged Windows builds can download and install the latest release automatically

## Requirements

- Windows (standalone `.exe` or run from source)
- Python 3.13+ when running from source
- JPG or JPEG input files only

## Run from source

```powershell
pip install -r requirements.txt
python -m brush_watermark path\to\image.jpg
```

(`python brush_watermark.py path\to\image.jpg` also works — it is a thin wrapper around the same entry point.)

If you omit the file path, a file picker opens.

## Run the executable

Download `BrushWatermark.zip` from [Releases](https://github.com/eriksimonic/BrushWattermarkTool/releases/latest), extract it, then:

```powershell
BrushWatermark\BrushWatermark.exe path\to\image.jpg
```

## Using the app

### Painting and selecting

| Action | Control |
|--------|---------|
| Paint a new watermark stroke | Left mouse drag |
| Select a stroke | Click the stroke (or pick it in the layer list) |
| Deselect | Click the selected stroke again |
| Erase watermark from an area | Right mouse drag |
| Change strength | Mouse wheel |
| Change brush / font size | Alt + mouse wheel |

### Sidebar

Lightroom-style panels on the right: section dividers, label-left / value-right sliders with teardrop handles, and neutral gray chrome (`#3B3B3B` panel, `#2A2A2A` canvas surround). See [`brush_watermark/ui/DESIGN.md`](brush_watermark/ui/DESIGN.md) for the full UI spec.

- **Watermark** — text, font, and auto-fit (applies to all strokes)
- **Brush** — color, blend mode, strength, brush size, softness, and repeat along stroke; sets **tool defaults** when nothing is selected, or edits the **selected layer** (section title shows `Layer · …`)
- **Layers** — stroke list; **Delete** or **Clear all**
- **Help** — shortcuts, current version, and link to a newer release if one is available

**Save and close** writes the watermarked image back to the same file (JPEG quality 95). Enable **Show in Explorer after save** to open the file location when done. **Exit without saving** discards changes to the image (tool defaults and watermark text are still saved to settings).

### Settings file

Tool defaults and watermark text are stored in:

`%USERPROFILE%\.lightroom_brush_watermark\settings.json`

## Build the executable

```powershell
.\build.ps1
```

Output: `dist\BrushWatermark\` (folder) and `dist\BrushWatermark.zip` (for distribution)

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

## Releases

Pushing Python changes (`.py` files) to `main` triggers the GitHub Actions release workflow: tests, bump the minor version, build `BrushWatermark.zip` with that version embedded, publish the GitHub release, then commit the version back to `main`. Pushes that only change other files (docs, config, assets, etc.) do not create a release. The app checks GitHub at startup; packaged Windows builds also offer a **Download and install update** button when a newer release is available.

---

*This project was created with the assistance of AI and is released under the [MIT License](LICENSE).*
