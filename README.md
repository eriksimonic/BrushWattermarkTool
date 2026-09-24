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
- **Auto strength** — optionally compute each new stroke's strength from the pixels underneath it, so flat areas get a fainter mark and busy/textured areas can hide a stronger one
- **Auto-place watermarks** — finds busy, detail-rich areas that avoid the photo's focal subject and drops several faint, low-opacity watermarks there, with an adjustable density
- **Blend modes** — Normal, Soft light, Lighten, Darken, Difference, Overlay, Screen, Multiply, Hard light
- **Image color picker** — 8 colors sampled from the photo, plus white, 50% gray, and black
- **Eraser tool** — paint away watermark pixels without deleting strokes
- **Metadata strip** — optional footer with camera, lens, exposure, serial number, and custom copy text (read from EXIF)
- **Save copy** — export a watermarked copy with an auto-generated filename (`{name}_{serial}_{datetime}_watermarked.jpg`) without overwriting the original
- **EXIF preservation** — camera metadata is carried through when saving
- **Modern dark editor** — top bar with File/Tools/Help menus and save actions, tool rail, floating tool hints and zoom controls, collapsible inspector, and a shortcut footer
- **Layer visibility** — hide or show individual watermark strokes from the layer list (hidden strokes aren't saved)
- **Auto update check** — compares your version to the latest release on GitHub
- **One-click update** — packaged Windows builds can download and install the latest release automatically
- **Cross-platform** — Windows, macOS, and Linux builds plus run-from-source support
- **Multi-image editing** — open several JPGs at once (multiple CLI args, or Lightroom's "Edit In" with multiple selected photos) and switch between them with a filmstrip; each image keeps its own edits in memory until saved

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

If you omit the file path, a file picker opens — you can select multiple JPGs at once to load them into the filmstrip.

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

### Menus

- **File** — Save & Close, Save Copy & Close, Save All & Close (with several images), Exit Without Saving (also available from the top bar's Exit, Save copy and Save & close buttons)
- **Tools** — Install or remove the Windows Explorer right-click shortcut for JPG/JPEG files; multi-selecting files and choosing it opens them all in one window with a filmstrip to switch between them (files that can't be opened are skipped with a warning)
- **Help** — About (version and usage)

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

**Save & close** overwrites the opened image (JPEG quality 95). **Save copy** writes a new file next to the original, named from the serial and capture date in EXIF when available, then closes the image. **Show in Explorer after save** opens the file's location when done. **Original** shows a clean preview without watermarks or guides. **Exit** discards changes to the image; tool defaults and watermark text are still saved to settings.

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

## Third-party assets

`brush_watermark/assets/salient_object.onnx` is the U^2-Netp model from
[danielgatis/rembg](https://github.com/danielgatis/rembg)
(originally [xuebinqin/U-2-Net](https://github.com/xuebinqin/U-2-Net)),
licensed under [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
It is used locally and offline to find each photo's focal subject for the
auto-watermark feature — no image data or network calls are involved.

## Releases

Pushing Python changes (`.py` files) to `main` triggers the GitHub Actions release workflow: tests, bump the minor version, build platform packages (`BrushWatermark.zip`, `BrushWatermark-macOS.zip`, `BrushWatermark-Linux.tar.gz`) with that version embedded, publish the GitHub release, then commit the version back to `main`. Pushes that only change other files (docs, config, assets, etc.) do not create a release. The app checks GitHub at startup; packaged Windows builds also offer a **Download and install update** button when a newer release is available.

---

*This project was created with the assistance of AI and is released under the [MIT License](LICENSE).*
