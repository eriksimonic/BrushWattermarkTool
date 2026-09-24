import dataclasses
import threading
import time
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from brush_watermark.config import SUPPORTED_EXTENSIONS
from brush_watermark.geometry.curve import (
    anchors_from_points,
    catmull_rom_curve,
)
from brush_watermark.geometry.points import (
    Point,
    clamp,
    dist,
    path_length,
    point_segment_distance,
    simplify_points,
)
from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.blend import blend_mode_label, composite_watermark_layer, normalize_blend_mode
from brush_watermark.rendering.metadata_footer import append_metadata_footer, estimate_footer_height
from brush_watermark.rendering.watermark import composite_watermark, compute_text_span, render_stroke_layer
from brush_watermark.services.exif_metadata import read_exif_bytes, read_image_metadata


# Render caches keep entries for this many display sizes: the full preview and
# the low-res one shown while dragging.
_CACHED_SIZES = 2


def _keep_recent(cache: dict, key, value) -> dict:
    """Return cache with key set to value as the newest entry, oldest dropped."""
    updated = {k: v for k, v in cache.items() if k != key}
    updated[key] = value
    while len(updated) > _CACHED_SIZES:
        del updated[next(iter(updated))]
    return updated


@dataclasses.dataclass(frozen=True)
class PreviewRequest:
    """Immutable snapshot of what one preview render needs (see Document.preview_request)."""

    display_w: int
    display_h: int
    scale_factor: float
    strokes: tuple[Stroke, ...]
    settings: Settings
    erase_mask: Optional[Image.Image]  # full-resolution copy; None when nothing is erased
    erase_version: int
    original: bool = False


class Document:
    """Application state: image, strokes, erase mask, and rendering logic."""

    def __init__(self, image_path: Path, settings: Settings):
        self.image_path = Path(image_path)
        if not self.image_path.exists():
            raise FileNotFoundError(f"File not found: {self.image_path}")
        if self.image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Input must be a JPG or JPEG file.")

        self.settings = settings
        self.original = Image.open(self.image_path).convert("RGB")
        self.full_w, self.full_h = self.original.size
        self.exif_bytes = read_exif_bytes(self.image_path)
        self.metadata = read_image_metadata(self.image_path)

        self.strokes: list[Stroke] = []
        self.selected_stroke_index = -1
        self.stroke_counter = 1
        self.dirty = False

        self.erase_mask = Image.new("L", (self.full_w, self.full_h), 0)
        self._erase_draw = ImageDraw.Draw(self.erase_mask)
        self._erase_version = 0

        self.current_points: list[Point] = []
        self.current_brush_size = settings.brush_size

        # Preview render caches, per display size: rendered per-stroke layers
        # (cropped to their bounding box) keyed by a content signature, plus the
        # resized base image. Only render_preview touches them, under the lock,
        # so a worker thread can render while the GUI thread edits.
        self._render_lock = threading.Lock()
        self._layer_caches: dict[tuple[int, int], dict[tuple, tuple]] = {}
        self._base_previews: dict[tuple[int, int], Image.Image] = {}
        self._erase_preview: Optional[Image.Image] = None
        self._erase_preview_key: Optional[tuple[int, int, int]] = None
        self._empty_erase_mask = Image.new("L", (1, 1), 0)
        # Copy of erase_mask handed to preview requests, refreshed when it changes.
        self._erase_snapshot: Optional[Image.Image] = None
        self._erase_snapshot_version = -1

    def visible_strokes(self) -> list[Stroke]:
        return [s for s in self.strokes if s.visible]

    def stroke_meta_text(self, stroke: Stroke) -> str:
        """One-line layer summary for the inspector's layer list."""
        length = int(path_length(stroke.points))
        text = f"{length} px · {blend_mode_label(stroke.blend_mode)} · {stroke.opacity}%"
        if stroke.repeat_text:
            text += " · repeat"
        return text

    def set_stroke_visible(self, index: int, visible: bool) -> None:
        if not 0 <= index < len(self.strokes):
            return
        stroke = self.strokes[index]
        if stroke.visible == visible:
            return
        stroke.visible = visible
        self.dirty = True

    def text_span_info(self, points: list[Point], brush_size: int):
        return compute_text_span(
            points,
            brush_size,
            self.settings.watermark_text,
            self.settings.font_name,
            self.settings.auto_fit_text,
            self.settings.repeat_text,
        )

    def scaled_strokes(self, scale_factor: float) -> list[Stroke]:
        if abs(scale_factor - 1.0) < 0.0001:
            return list(self.strokes)
        scaled = []
        for stroke in self.strokes:
            pts = [
                (int(round(x * scale_factor)), int(round(y * scale_factor)))
                for x, y in stroke.points
            ]
            anchors = [
                (int(round(x * scale_factor)), int(round(y * scale_factor)))
                for x, y in stroke.anchors
            ]
            scaled.append(
                Stroke(
                    name=stroke.name,
                    visible=stroke.visible,
                    points=pts,
                    anchors=anchors,
                    brush_size=max(1, int(round(stroke.brush_size * scale_factor))),
                    opacity=stroke.opacity,
                    blend_mode=stroke.blend_mode,
                    text_color=stroke.text_color,
                    angle_offset=stroke.angle_offset,
                    mask_softness=stroke.mask_softness,
                    repeat_text=stroke.repeat_text,
                    repeat_spacing=stroke.repeat_spacing,
                )
            )
        return scaled

    def metadata_footer_height(self) -> int:
        if not self.settings.add_visible_metadata:
            return 0
        return estimate_footer_height(
            self.full_w,
            self.full_h,
            self.metadata,
            self.settings.metadata_copy_text,
        )

    def preview_content_size(self, *, include_metadata: bool) -> tuple[int, int]:
        height = self.full_h
        if include_metadata and self.settings.add_visible_metadata:
            height += self.metadata_footer_height()
        return self.full_w, height

    def _maybe_append_metadata_footer(self, image: Image.Image) -> Image.Image:
        if not self.settings.add_visible_metadata:
            return image
        return append_metadata_footer(
            image,
            self.metadata,
            self.settings.metadata_copy_text,
        )

    def make_full_composited_image(self) -> Image.Image:
        result = composite_watermark(self.original, self.strokes, self.settings, self.erase_mask)
        return self._maybe_append_metadata_footer(result)

    def _preview_base_image(self, display_w: int, display_h: int) -> Image.Image:
        """LANCZOS-resized copy of the original, cached for the last few display sizes."""
        size = (display_w, display_h)
        base = self._base_previews.get(size)
        if base is None:
            base = self.original.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
        self._base_previews = _keep_recent(self._base_previews, size, base)
        return base.copy()

    @staticmethod
    def _stroke_layer_signature(
        stroke: Stroke, settings: Settings, display_w: int, display_h: int, erase_version: int
    ) -> tuple:
        """Everything that affects a stroke's rendered (pre-blend) layer."""
        return (
            tuple(stroke.points),
            stroke.brush_size,
            stroke.mask_softness,
            stroke.angle_offset,
            stroke.text_color,
            stroke.repeat_text,
            stroke.repeat_spacing,
            stroke.visible,
            settings.watermark_text,
            settings.font_name,
            settings.auto_fit_text,
            display_w,
            display_h,
            erase_version,
        )

    def _composite_preview(
        self,
        base_rgba: Image.Image,
        request: "PreviewRequest",
        erase_mask: Image.Image,
    ) -> Image.Image:
        """Composite strokes onto base, reusing cached per-stroke layers.

        Unchanged strokes are not re-rendered; blending only touches each
        stroke's bounding box, so cost scales with edited/added strokes rather
        than the total number of strokes. Layers are cached per display size
        (the last few), so alternating a low-res drag preview with the full
        one doesn't throw the other size's layers away.
        """
        size = (request.display_w, request.display_h)
        old_cache = self._layer_caches.get(size, {})
        result = base_rgba
        new_cache: dict[tuple, tuple] = {}
        for stroke in request.strokes:
            if not stroke.visible:
                continue
            sig = self._stroke_layer_signature(
                stroke, request.settings, request.display_w, request.display_h, request.erase_version
            )
            cached = old_cache.get(sig)
            if cached is None:
                cached = render_stroke_layer(
                    request.display_w, request.display_h, stroke, request.settings, erase_mask, request.scale_factor
                )
            new_cache[sig] = cached
            layer_crop, box = cached
            if layer_crop is None:
                continue
            strength = clamp(stroke.opacity, 1, 100) / 100.0
            region = result.crop(box)
            blended = composite_watermark_layer(
                region,
                layer_crop,
                stroke.text_color,
                normalize_blend_mode(stroke.blend_mode, request.settings.blend_mode),
                strength,
            )
            result.paste(blended, box)
        self._layer_caches = _keep_recent(self._layer_caches, size, new_cache)
        return result

    def _preview_erase_mask(self, request: "PreviewRequest") -> Image.Image:
        """The erase mask at display size, resized once per erase version and size.

        Rendering resizes the erase mask to the layer size when scaling; handing
        it an already-resized mask makes that a plain copy, with identical output.
        """
        if request.erase_mask is None:
            return self._empty_erase_mask
        if abs(request.scale_factor - 1.0) < 0.0001:
            return request.erase_mask
        key = (request.erase_version, request.display_w, request.display_h)
        if self._erase_preview_key != key:
            self._erase_preview = request.erase_mask.resize(
                (request.display_w, request.display_h), Image.Resampling.BILINEAR
            )
            self._erase_preview_key = key
        return self._erase_preview

    def preview_request(
        self, display_w: int, display_h: int, scale_factor: float, *, original: bool = False
    ) -> "PreviewRequest":
        """Snapshot everything a preview render needs (GUI thread).

        The request owns copies of the strokes, settings and erase mask, so
        `render_preview` can run on a worker thread while the document keeps
        being edited.
        """
        if self._erase_snapshot_version != self._erase_version:
            self._erase_snapshot = self.erase_mask.copy() if self.erase_mask.getbbox() else None
            self._erase_snapshot_version = self._erase_version
        strokes = tuple(
            dataclasses.replace(s, points=list(s.points), anchors=list(s.anchors))
            for s in self.scaled_strokes(scale_factor)
        )
        return PreviewRequest(
            display_w=max(1, int(display_w)),
            display_h=max(1, int(display_h)),
            scale_factor=scale_factor,
            strokes=strokes,
            settings=dataclasses.replace(self.settings),
            erase_mask=self._erase_snapshot,
            erase_version=self._erase_version,
            original=original,
        )

    def render_preview(self, request: "PreviewRequest") -> Image.Image:
        """Render a preview from a snapshot; safe to call from a worker thread.

        Only the render caches are touched (under a lock), never the live
        strokes or erase mask.
        """
        return self.render_preview_timed(request)[0]

    def render_preview_timed(self, request: "PreviewRequest") -> tuple[Image.Image, float]:
        """render_preview, plus how long the strokes took in ms.

        The timing leaves out the one-off resize of the original for a new
        display size, so it reflects what re-rendering after an edit costs.
        """
        with self._render_lock:
            base = self._preview_base_image(request.display_w, request.display_h)
            if request.original:
                return base, 0.0
            started = time.perf_counter()
            preview = self._composite_preview(base, request, self._preview_erase_mask(request))
            if request.settings.add_visible_metadata:
                preview = append_metadata_footer(
                    preview.convert("RGB"),
                    self.metadata,
                    request.settings.metadata_copy_text,
                ).convert("RGBA")
            return preview, (time.perf_counter() - started) * 1000

    def make_preview_image(self, display_w: int, display_h: int, scale_factor: float) -> Image.Image:
        return self.render_preview(self.preview_request(display_w, display_h, scale_factor))

    def make_original_preview_image(self, display_w: int, display_h: int) -> Image.Image:
        return self.render_preview(self.preview_request(display_w, display_h, 1.0, original=True))

    def stroke_hit_distance(self, stroke: Stroke, img_x: int, img_y: int) -> Optional[float]:
        points = stroke.points
        if len(points) < 2:
            return None
        min_d = None
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            d = point_segment_distance(img_x, img_y, ax, ay, bx, by)
            if min_d is None or d < min_d:
                min_d = d
        return min_d

    @staticmethod
    def _hit_tolerance(brush_size: int, extra_tol: float) -> float:
        return max(14.0, float(brush_size) * 0.60) + extra_tol

    def point_near_stroke(self, index: int, img_x: int, img_y: int, extra_tol: float = 0.0) -> bool:
        if index < 0 or index >= len(self.strokes):
            return False
        stroke = self.strokes[index]
        if not stroke.visible:
            return False
        min_d = self.stroke_hit_distance(stroke, img_x, img_y)
        if min_d is None:
            return False
        return min_d <= self._hit_tolerance(stroke.brush_size, extra_tol)

    def find_stroke_at_point(self, img_x: int, img_y: int, extra_tol: float = 24.0) -> int:
        best_idx = -1
        best_dist = None
        for idx, stroke in enumerate(self.strokes):
            if not stroke.visible:
                continue
            min_d = self.stroke_hit_distance(stroke, img_x, img_y)
            if min_d is None:
                continue
            tol = self._hit_tolerance(stroke.brush_size, extra_tol)
            if min_d <= tol and (best_dist is None or min_d < best_dist):
                best_dist = min_d
                best_idx = idx
        return best_idx

    def _anchor_epsilon(self, brush_size: int) -> float:
        """Simplification tolerance that yields a handful of Illustrator-style anchors."""
        return max(6.0, brush_size * 0.35)

    def _rebuild_curve(self, stroke: Stroke) -> None:
        """Recompute the dense render curve from the stroke's anchors."""
        if len(stroke.anchors) >= 2:
            stroke.points = catmull_rom_curve(stroke.anchors)
        else:
            stroke.points = list(stroke.anchors)

    def add_stroke(
        self,
        points: list[Point],
        brush_size: int,
        opacity: int,
        blend_mode: str,
        text_color: str,
        angle_offset: int,
        mask_softness: int,
        repeat_text: bool,
        repeat_spacing: int,
    ) -> Stroke:
        anchors = anchors_from_points(points, self._anchor_epsilon(brush_size))
        curve = catmull_rom_curve(anchors) if len(anchors) >= 2 else list(anchors)
        stroke = Stroke(
            name=f"Stroke {self.stroke_counter}",
            visible=True,
            points=curve,
            anchors=anchors,
            brush_size=brush_size,
            opacity=opacity,
            blend_mode=blend_mode,
            text_color=text_color,
            angle_offset=angle_offset,
            mask_softness=mask_softness,
            repeat_text=repeat_text,
            repeat_spacing=repeat_spacing,
        )
        self.stroke_counter += 1
        self.strokes.append(stroke)
        self.dirty = True
        return stroke

    def finalize_stroke_points(self, raw_points: list[Point], brush_size: int) -> list[Point]:
        # Store only simplified anchor points; smooth_path_for_text handles smoothing at render time.
        return simplify_points(raw_points, min_dist=max(2.0, brush_size * 0.010))

    def append_to_stroke(self, index: int, new_points: list[Point]) -> None:
        """Append new_points to an existing stroke, extending its anchors."""
        if index < 0 or index >= len(self.strokes):
            return
        stroke = self.strokes[index]
        new_anchors = anchors_from_points(new_points, self._anchor_epsilon(stroke.brush_size))
        combined = list(stroke.anchors) + new_anchors
        deduped: list[Point] = []
        for pt in combined:
            if not deduped or deduped[-1] != pt:
                deduped.append(pt)
        stroke.anchors = deduped
        self._rebuild_curve(stroke)
        self.dirty = True

    def move_anchor(self, stroke_index: int, anchor_index: int, xy: Point) -> None:
        if 0 <= stroke_index < len(self.strokes):
            stroke = self.strokes[stroke_index]
            if 0 <= anchor_index < len(stroke.anchors):
                stroke.anchors[anchor_index] = xy
                self._rebuild_curve(stroke)
                self.dirty = True

    def insert_anchor(self, stroke_index: int, segment_index: int, xy: Point) -> None:
        if 0 <= stroke_index < len(self.strokes):
            stroke = self.strokes[stroke_index]
            if 0 <= segment_index < len(stroke.anchors) - 1:
                stroke.anchors.insert(segment_index + 1, xy)
                self._rebuild_curve(stroke)
                self.dirty = True

    def delete_anchor(self, stroke_index: int, anchor_index: int) -> None:
        if 0 <= stroke_index < len(self.strokes):
            stroke = self.strokes[stroke_index]
            if len(stroke.anchors) > 2 and 0 <= anchor_index < len(stroke.anchors):
                del stroke.anchors[anchor_index]
                self._rebuild_curve(stroke)
                self.dirty = True

    def select_stroke(self, index: int) -> None:
        if index < 0 or index >= len(self.strokes):
            self.selected_stroke_index = -1
            return
        self.selected_stroke_index = index

    def update_selected_stroke(
        self,
        brush_size: int,
        opacity: int,
        blend_mode: str,
        text_color: str,
        angle_offset: int,
        mask_softness: int,
        repeat_text: bool,
        repeat_spacing: int,
    ) -> None:
        if 0 <= self.selected_stroke_index < len(self.strokes):
            stroke = self.strokes[self.selected_stroke_index]
            stroke.brush_size = brush_size
            stroke.opacity = opacity
            stroke.blend_mode = blend_mode
            stroke.text_color = text_color
            stroke.angle_offset = angle_offset
            stroke.mask_softness = mask_softness
            stroke.repeat_text = repeat_text
            stroke.repeat_spacing = repeat_spacing
            self.dirty = True

    def delete_selected_stroke(self) -> None:
        if 0 <= self.selected_stroke_index < len(self.strokes):
            del self.strokes[self.selected_stroke_index]
            if self.strokes:
                self.selected_stroke_index = min(self.selected_stroke_index, len(self.strokes) - 1)
            else:
                self.selected_stroke_index = -1
            self.dirty = True

    def clear_all(self) -> None:
        had_strokes = bool(self.strokes) or bool(self.erase_mask.getbbox())
        self.strokes = []
        self.current_points = []
        self.selected_stroke_index = -1
        self.erase_mask = Image.new("L", (self.full_w, self.full_h), 0)
        self._erase_draw = ImageDraw.Draw(self.erase_mask)
        self._erase_version += 1
        self._layer_caches = {}
        if had_strokes:
            self.dirty = True

    def add_erase_to_mask(self, img_x: int, img_y: int) -> None:
        size = self.settings.brush_size
        r = size // 2
        self._erase_draw.ellipse((img_x - r, img_y - r, img_x + r, img_y + r), fill=255)
        self._erase_version += 1
        self.dirty = True

    def add_erase_line_to_mask(self, x0: int, y0: int, x1: int, y1: int) -> None:
        size = self.settings.brush_size
        self._erase_draw.line((x0, y0, x1, y1), fill=255, width=size)
        self.add_erase_to_mask(x1, y1)

    def is_click_release(self, press_xy: Optional[Point], release_xy: Point, brush_size: int) -> bool:
        if press_xy is None:
            return True
        click_threshold = max(10, int(brush_size * 0.12))
        return dist(press_xy, release_xy) < click_threshold

    def canvas_to_image_xy(
        self, canvas_x: float, canvas_y: float, scale: float, offset_x: float, offset_y: float
    ) -> Point:
        x = (canvas_x - offset_x) / scale
        y = (canvas_y - offset_y) / scale
        return int(clamp(x, 0, self.full_w - 1)), int(clamp(y, 0, self.full_h - 1))

    def image_to_canvas_xy(
        self, x: float, y: float, scale: float, offset_x: float, offset_y: float
    ) -> tuple[float, float]:
        return offset_x + x * scale, offset_y + y * scale

    def inside_image_canvas(
        self,
        canvas_x: float,
        canvas_y: float,
        display_w: float,
        display_h: float,
        offset_x: float,
        offset_y: float,
    ) -> bool:
        return (
            offset_x <= canvas_x <= offset_x + display_w
            and offset_y <= canvas_y <= offset_y + display_h
        )


def load_documents(paths: list[Path], settings: Settings) -> tuple[list[Document], list[str]]:
    """Open each image as its own Document, collecting per-file errors instead of raising.

    Each Document gets its own Settings copy so switching between images
    doesn't leak in-progress edits from one to another. Duplicate paths
    are opened once.
    """
    docs: list[Document] = []
    errors: list[str] = []
    seen: set[Path] = set()
    for path in paths:
        key = Path(path).resolve()
        if key in seen:
            continue
        seen.add(key)
        try:
            docs.append(Document(path, dataclasses.replace(settings)))
        except (FileNotFoundError, ValueError, OSError) as exc:
            errors.append(f"{Path(path).name}: {exc}")
    return docs, errors


def format_load_errors(errors: list[str]) -> str:
    return "Could not open:\n\n" + "\n".join(errors)
