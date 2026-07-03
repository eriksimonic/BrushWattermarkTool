# Brush Watermark Tool

Paint subtle, brush-shaped text watermarks directly onto JPG photos. Designed for a Lightroom-style workflow: open an image, draw along the area where the watermark should follow, and save the result back to the same file.

## What it does

Brush Watermark Tool overlays your watermark text along a painted stroke path. The text follows the curve of your brush line, rotates with the path, and can be blended into the image pixels so the mark is harder to notice and remove than a flat semi-transparent overlay.

Each watermark is saved into the image file itself (JPEG). Settings such as default text, font, and tool options are remembered between sessions.

## Features

- **Brush strokes** — paint watermark paths with the mouse; text is laid out along the stroke
- **Per-layer control** — each stroke has its own color, blend mode, strength, brush size, angle, and edge softness
- **Blend modes** — Normal, Soft light, Lighten, Darken, Difference, Overlay, Screen, Multiply, Hard light
- **Image color picker** — 8 colors sampled from the photo, plus white, 50% gray, and black
- **Erase mask** — right-click paint to hide watermark areas without deleting strokes
- **Auto update check** — compares your version to the latest release on GitHub

## Requirements

- Windows (standalone `.exe` or run from source)
- Python 3.13+ when running from source
- JPG or JPEG input files only

## Run from source

```powershell
pip install -r requirements.txt
python brush_watermark.py path\to\image.jpg
```

If you omit the file path, a file picker opens.

## Run the executable

Download `BrushWatermark.exe` from [Releases](https://github.com/eriksimonic/BrushWattermarkTool/releases/latest), then:

```powershell
BrushWatermark.exe path\to\image.jpg
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

- **Watermark** — text, font, and auto-fit (apply to all strokes)
- **Layers** — list of strokes; delete or clear all
- **Controls** — when nothing is selected, these set **tool defaults** for the next stroke; when a layer is selected, they edit **that layer**
- **Help** — shortcuts, current version, and link to a newer release if one is available

Click **Save and close** to write the watermarked image (quality 95, same path). **Exit without saving** discards changes to the image.

### Settings file

Tool defaults and watermark text are stored in:

`%USERPROFILE%\.lightroom_brush_watermark\settings.json`

## Build the executable

```powershell
.\build.ps1
```

Output: `dist\BrushWatermark.exe`

## Tests

```powershell
pytest
```

## Releases

Pushing to `main` triggers the GitHub Actions release workflow: tests, build, publish `BrushWatermark.exe`, and bump the version in the repository. The app checks the `VERSION` file on GitHub at startup to notify you when a newer release is available.

---

*This project was created with the assistance of AI and is released under the [MIT License](LICENSE).*
