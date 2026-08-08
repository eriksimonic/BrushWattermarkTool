# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Brush Watermark Tool — a PySide6 (Qt for Python) desktop app that paints brush-shaped text watermarks along a hand-drawn stroke path on JPG photos, styled after Adobe Lightroom Classic's dark UI. Each watermark is baked into the saved JPEG; original EXIF is preserved. Settings persist at `~/.lightroom_brush_watermark/settings.json`.

## Commands

Run from source (Windows uses the venv at `.venv`; see `run.ps1`):

```bash
pip install -r requirements-dev.txt   # includes requirements.txt + pytest
python -m brush_watermark path/to/image.jpg   # or: python brush_watermark.py path/to/image.jpg
```

Tests:

```bash
pytest                       # full suite (tests/, configured via pytest.ini)
pytest tests/test_curve.py   # single file
pytest tests/test_curve.py::TestName::test_case  # single test
```

There is no lint/format command configured in this repo.

Build a standalone executable (PyInstaller, `BrushWatermark.spec`):

```powershell
.\build.ps1        # Windows -> dist\BrushWatermark\, dist\BrushWatermark.zip
```

```bash
./build.sh         # macOS/Linux -> dist/BrushWatermark.app or dist/BrushWatermark/
```

## Architecture

The codebase is split into four layers with a one-directional dependency flow: `geometry` → `rendering` → `services` → `ui`. Lower layers have no Qt dependency and are the bulk of what's unit-tested in `tests/`.

- **`brush_watermark/geometry/`** — pure math on point lists: Catmull-Rom curve smoothing (`curve.py`), simplification/distance/clamping helpers (`points.py`), and laying text out along a curved path (`path_text.py`).
- **`brush_watermark/rendering/`** — Pillow-based pixel work: blend modes (`blend.py`), color helpers (`colors.py`), font loading (`fonts.py`), stroke masks (`masks.py`), the EXIF metadata footer strip (`metadata_footer.py`), and compositing a stroke's text onto the image (`watermark.py`).
- **`brush_watermark/services/`** — stateful/IO logic with no Qt dependency: `document.py` (see below), EXIF reading (`exif_metadata.py`), save/export (`export.py`), auto-watermark placement (`auto_watermark.py`, `busy_area_detection.py`, `subject_detection.py` — the last uses the bundled ONNX salient-object model), adaptive per-stroke strength (`adaptive_strength.py`), GitHub-release update checks (`update_check.py`, `auto_update.py`), and Explorer/Finder integration (`explorer_context.py`).
- **`brush_watermark/ui/`** — all PySide6 widgets. `main_window.py` (`MainWindow`) is the orchestrator: it owns the `Document`, wires `CanvasWidget` (image preview + overlay painting, `canvas.py`) and `SidebarPanel` (right-hand controls, `sidebar.py`) together via plain Qt signals — there's no MVVM/MVC framework. Long-running work (auto-watermark placement, update checks/downloads) runs on `QThread` workers (`auto_watermark_worker.py`, `auto_updater.py`, `update_checker.py`) to keep the UI responsive.

**`Document`** (`services/document.py`) is the core state object: the loaded image, the list of `Stroke`s, the erase mask, and preview rendering. Each `Stroke` stores sparse editable `anchors` (what the Path tool drags/inserts/deletes) separately from the dense `points` curve derived from them via Catmull-Rom (used for actual text rendering) — anchors and the rendered curve are always kept in sync through `Document._rebuild_curve`. Preview compositing is incremental: `_composite_preview` caches each stroke's rendered layer keyed by a content signature (`_stroke_layer_signature`) and only re-renders strokes whose signature changed, so editing one stroke doesn't re-render all of them.

**Models** (`models.py`): `Settings` (dataclass, persisted to `~/.lightroom_brush_watermark/settings.json` via `config.py`, doubles as both current-tool defaults and the source of truth when nothing is selected), `Stroke`, `TextSpan`, and `CanvasView` (a read-only per-frame snapshot passed to `CanvasWidget.paintEvent` for overlay drawing — guides, anchor handles, brush cursor).

**UI design system**: `brush_watermark/ui/design_tokens.py` is the single source of truth for colors (import tokens, never hard-code hex values in widgets); `styles.py` builds the global QSS stylesheet from those tokens; `lightroom_controls.py` holds shared custom-painted widgets (`CollapsibleSection` accordion, `LightroomSlider`, `BoxCheckBox`, `SliderRow`); `icons.py` loads/recolors/rasterizes the bundled Lucide SVG icon set (`assets/icons/`, ISC-licensed) into cached `QPixmap`/`QIcon`s. Full spec and "do not" rules in `brush_watermark/ui/DESIGN.md` — read it before touching UI styling.

**Entry points**: `brush_watermark.py` (repo-root thin wrapper) and `python -m brush_watermark` both resolve to `brush_watermark/main.py:main()`, which resolves the image path (CLI arg or file picker), loads `Settings`, and constructs `MainWindow`.

## CI / release flow

`.github/workflows/release.yml`: pushing changes to any `.py` file on `main` (unless the commit message contains `[skip ci]`) runs the test suite, bumps the minor version in `brush_watermark/__init__.py` and `VERSION`, builds Windows/macOS/Linux packages via `BrushWatermark.spec`, publishes a GitHub release, then commits the version bump back to `main` as `github-actions[bot]`. Non-`.py` changes (docs, config, assets) don't trigger a release. When pulling/pushing, expect `main` to sometimes be ahead due to this bot commit — rebase rather than force-push over it.

## Third-party assets

`brush_watermark/assets/salient_object.onnx` is the U^2-Netp model from [danielgatis/rembg](https://github.com/danielgatis/rembg) (Apache 2.0), used offline for auto-watermark subject detection — no network calls. `brush_watermark/assets/icons/*.svg` are from [Lucide](https://lucide.dev) (ISC), see `LICENSE-ICONS.txt`.
