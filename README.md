# Brush Watermark Tool

Paint subtle, brush-shaped text watermarks directly onto JPG photos. Designed for a Lightroom-style workflow: open an image, draw along the area where the watermark should follow, and save the result back to the same file or as a copy.

**Current version:** 1.11.0

## What it does

Brush Watermark Tool overlays your watermark text along a painted stroke path. The text follows the curve of your brush line, rotates with the path, and can be blended into the image pixels so the mark is harder to notice and remove than a flat semi-transparent overlay.

Each watermark is saved into the image file itself (JPEG). Original EXIF metadata is preserved on save. Settings such as default text, font, and tool options are remembered between sessions.

## Features

- **Four editing tools** — Pointer (select), Brush (draw strokes), Path (edit anchors), and Eraser (remove watermark pixels)
- **Brush strokes** — freehand drag or click-to-place straight segments; snap to stroke endpoints to resume a line; right-click stops drawing
- **Path editing** — drag anchors on the selected stroke, double-click a segment to add an anchor, Delete to remove one
- **Per-layer control** — each stroke has its own color, blend mode, strength, brush size, softness, and repeat settings
- **Repeat text** — optionally tile watermark text along long strokes, with adjustable gap
- **Blend modes** — Normal, Soft light, Lighten, Darken, Difference, Overlay, Screen, Multiply, Hard light
- **Image color picker** — 8 colors sampled from the photo, plus white, 50% gray, and black
- **Eraser tool** — paint away watermark pixels without deleting strokes
- **Metadata strip** — optional footer with camera, lens, exposure, serial number, and custom copy text (read from EXIF)
- **Save copy** — export a watermarked copy with an auto-generated filename (`{name}_{serial}_{datetime}_watermarked.jpg`) without overwriting the original
- **EXIF preservation** — camera metadata is carried through when saving
- **Menu bar** — File, Tools (Windows Explorer shortcut), and Help actions
- **Auto update check** — compares your version to the latest release on GitHub
- **One-click update** — packaged Windows builds can download and install the latest release automatically
- **Cross-platform** — Windows, macOS, and Linux builds plus run-from-source support

## Requirements

- Windows, macOS, or Linux (standalone build or run from source)
- Python 3.13+ when running from source
- JPG or JPEG input files only

## Run from source

```bash
pip install -r requirements.txt
python -m brush_watermark path/to/image.jpg
```

(`python brush_watermark.py path/to/image.jpg` also works — it is a thin wrapper around the same entry point.)

If you omit the file path, a file picker opens.

## Run the executable

Download the build for your platform from [Releases](https://github.com/eriksimonic/BrushWattermarkTool/releases/latest).

### Windows

Extract `BrushWatermark.zip`, then:

```powershell
BrushWatermark\BrushWatermark.exe path\to\image.jpg
```

### macOS

Extract `BrushWatermark-macOS.zip`, then open `BrushWatermark.app`. If Gatekeeper blocks the unsigned app on first launch, right-click the app and choose **Open**.

You can also pass an image path from Terminal:

```bash
open dist/BrushWatermark.app --args path/to/image.jpg
```

### Linux

Extract `BrushWatermark-Linux.tar.gz`, then:

```bash
chmod +x BrushWatermark/BrushWatermark   # if needed
./BrushWatermark/BrushWatermark path/to/image.jpg
```

## Using the app

### Tools and shortcuts

| Tool | Key | Actions |
|------|-----|---------|
| **Pointer** | V | Click a stroke to select; click again to deselect |
| **Brush** | B | Left-drag = freehand · left-click = straight-line points · left-click a line end = resume (snap) · right-click = stop drawing |
| **Path** | A | Drag anchor · double-click segment = add anchor · Del = remove anchor |
| **Eraser** | E | Drag to erase watermark pixels |

| Adjustment | Control |
|------------|---------|
| Change strength | Mouse wheel |
| Change brush / font size | Alt + mouse wheel |
| Cancel line / deselect anchor | Escape |

### Menu bar

- **File** — Save & Close, Save Copy & Close, Exit Without Saving
- **Tools** — Install or remove the Windows Explorer right-click shortcut for JPG/JPEG files
- **Help** — About (version and usage)

### Sidebar

Lightroom-style panels on the right: section dividers, label-left / value-right sliders with teardrop handles, and neutral gray chrome (`#3B3B3B` panel, `#2A2A2A` canvas surround). See [`brush_watermark/ui/DESIGN.md`](brush_watermark/ui/DESIGN.md) for the full UI spec.

- **Image** — camera serial from EXIF; optional **Add visible metadata strip** and custom copy text for the footer
- **Tools** — Pointer, Brush, Path, and Eraser buttons
- **Watermark** — text, font, and auto-fit (applies to all strokes)
- **Brush** — color, blend mode, strength, brush size, softness, and repeat along stroke; sets **tool defaults** when nothing is selected, or edits the **selected layer** (section title shows `Layer · …`)
- **Layers** — stroke list; **Delete** or **Clear all**
- **Help** — shortcuts, current version, and link to a newer release if one is available

**Save and close** overwrites the opened image (JPEG quality 95). **Save copy and close** writes a new file next to the original using serial and capture date from EXIF when available. Enable **Show in Explorer after save** to open the file location when done. **Show original (before preview)** toggles a clean preview without watermarks or guides. **Exit without saving** discards changes to the image (tool defaults and watermark text are still saved to settings).

### Settings file

Tool defaults and watermark text are stored in:

`~/.lightroom_brush_watermark/settings.json`

(On Windows this is `%USERPROFILE%\.lightroom_brush_watermark\settings.json`.)

## Build the executable

### Windows

```powershell
.\build.ps1
```

Output: `dist\BrushWatermark\` (folder) and `dist\BrushWatermark.zip`

### macOS / Linux

```bash
chmod +x build.sh
./build.sh
```

Output:

- **macOS:** `dist/BrushWatermark.app` and `dist/BrushWatermark-macOS.zip`
- **Linux:** `dist/BrushWatermark/` and `dist/BrushWatermark-Linux.tar.gz`

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Releases

Pushing Python changes (`.py` files) to `main` triggers the GitHub Actions release workflow: tests, bump the minor version, build platform packages (`BrushWatermark.zip`, `BrushWatermark-macOS.zip`, `BrushWatermark-Linux.tar.gz`) with that version embedded, publish the GitHub release, then commit the version back to `main`. Pushes that only change other files (docs, config, assets, etc.) do not create a release. The app checks GitHub at startup; packaged Windows builds also offer a **Download and install update** button when a newer release is available.

---

*This project was created with the assistance of AI and is released under the [MIT License](LICENSE).*
