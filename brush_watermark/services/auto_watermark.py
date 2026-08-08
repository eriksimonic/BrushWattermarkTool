"""Auto-places barely-visible watermark strokes in busy, subject-safe regions.

Combines subject_detection (find + protect the photo's focal subject) and
busy_area_detection (grow longer, gently curved paths through detail-rich
areas) to synthesize a handful of stroke paths, then adds them through the
existing Document.add_stroke pipeline. Each stroke's opacity is computed
per-stroke from the pixels it actually covers (adaptive_strength), not a
flat constant, so it reads as consistently faint whatever it's placed on.
The resulting strokes are ordinary strokes afterward — editable, visible in
the layer list, rendered by the unmodified compositing pipeline — nothing
about auto-placement is special-cased there.
"""

from PIL import Image

from brush_watermark.models import Stroke
from brush_watermark.services.adaptive_strength import opacity_for_path
from brush_watermark.services.busy_area_detection import BusyPath, find_busy_paths
from brush_watermark.services.document import Document
from brush_watermark.services.subject_detection import subject_protect_mask

MIN_DENSITY = 1
MAX_DENSITY = 12
DEFAULT_DENSITY = 6


def clamp_density(density: int) -> int:
    return max(MIN_DENSITY, min(MAX_DENSITY, density))


def find_auto_watermark_paths(image: Image.Image, density: int = DEFAULT_DENSITY) -> list[BusyPath]:
    """Analyze `image` for subject-safe busy paths.

    Only reads `image` — safe to call off the GUI thread (e.g. from a
    QThread worker), unlike add_paths_as_strokes below which mutates a
    Document.
    """
    protect_mask = subject_protect_mask(image)
    return find_busy_paths(image, protect_mask, count=clamp_density(density))


def add_paths_as_strokes(document: Document, paths: list[BusyPath]) -> list[Stroke]:
    """Add one auto-placed stroke per path to `document`.

    Mutates `document.strokes` — must run on the same thread that owns the
    Document (the GUI thread), not inside a background worker.
    """
    settings = document.settings
    added: list[Stroke] = []
    for path in paths:
        opacity = opacity_for_path(
            document.original, path.points, path.brush_size, settings.mask_softness
        )
        stroke = document.add_stroke(
            points=path.points,
            brush_size=path.brush_size,
            opacity=opacity,
            blend_mode=settings.blend_mode,
            text_color=settings.text_color,
            angle_offset=settings.angle_offset,
            mask_softness=settings.mask_softness,
            repeat_text=settings.repeat_text,
            repeat_spacing=settings.repeat_spacing,
        )
        added.append(stroke)
    return added


def place_auto_watermarks(document: Document, density: int = DEFAULT_DENSITY) -> list[Stroke]:
    """Analyze the document's image and add auto-placed strokes (synchronous).

    Convenience wrapper combining find_auto_watermark_paths and
    add_paths_as_strokes for callers that don't need to split the work
    across threads (tests, scripts). The UI instead runs the analysis half
    in AutoWatermarkWorker and applies the result on the GUI thread.
    """
    paths = find_auto_watermark_paths(document.original, density)
    return add_paths_as_strokes(document, paths)
