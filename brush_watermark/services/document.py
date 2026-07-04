from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from brush_watermark.config import SUPPORTED_EXTENSIONS
from brush_watermark.geometry.points import (
    Point,
    chaikin_smooth,
    dist,
    path_length,
    point_segment_distance,
    simplify_points,
)
from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.blend import blend_mode_short
from brush_watermark.rendering.colors import color_short
from brush_watermark.rendering.watermark import composite_watermark, compute_text_span, make_preview_image


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

        self.strokes: list[Stroke] = []
        self.selected_stroke_index = -1
        self.stroke_counter = 1

        self.erase_mask = Image.new("L", (self.full_w, self.full_h), 0)
        self._erase_draw = ImageDraw.Draw(self.erase_mask)

        self.current_points: list[Point] = []
        self.current_brush_size = settings.brush_size

    def visible_strokes(self) -> list[Stroke]:
        return [s for s in self.strokes if s.visible]

    def stroke_list_text(self, idx: int, stroke: Stroke) -> str:
        eye = "👁" if stroke.visible else "🚫"
        length = int(path_length(stroke.points))
        color = color_short(stroke.text_color)
        return (
            f"{eye}  {stroke.name}  |  len {length}px  |  "
            f"b{stroke.brush_size}  |  s{stroke.opacity}%  |  "
            f"{blend_mode_short(stroke.blend_mode)}  |  #{color}  |  "
            f"{'repeat' if stroke.repeat_text else 'stretch'}"
            f"{f' +{stroke.repeat_spacing}' if stroke.repeat_text else ''}"
        )

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
            scaled.append(
                Stroke(
                    name=stroke.name,
                    visible=stroke.visible,
                    points=pts,
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

    def make_full_composited_image(self) -> Image.Image:
        return composite_watermark(self.original, self.strokes, self.settings, self.erase_mask)

    def make_preview_image(self, display_w: int, display_h: int, scale_factor: float) -> Image.Image:
        preview_strokes = self.scaled_strokes(scale_factor)
        return make_preview_image(
            self.original,
            display_w,
            display_h,
            preview_strokes,
            self.settings,
            self.erase_mask,
            scale_factor,
        )

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

    def point_near_stroke(self, index: int, img_x: int, img_y: int, extra_tol: float = 0.0) -> bool:
        if index < 0 or index >= len(self.strokes):
            return False
        stroke = self.strokes[index]
        if not stroke.visible:
            return False
        min_d = self.stroke_hit_distance(stroke, img_x, img_y)
        if min_d is None:
            return False
        tol = max(14.0, float(stroke.brush_size) * 0.60) + extra_tol
        return min_d <= tol

    def find_stroke_at_point(self, img_x: int, img_y: int, extra_tol: float = 24.0) -> int:
        best_idx = -1
        best_dist = None
        for idx, stroke in enumerate(self.strokes):
            if not stroke.visible:
                continue
            min_d = self.stroke_hit_distance(stroke, img_x, img_y)
            if min_d is None:
                continue
            tol = max(14.0, float(stroke.brush_size) * 0.60) + extra_tol
            if min_d <= tol and (best_dist is None or min_d < best_dist):
                best_dist = min_d
                best_idx = idx
        return best_idx

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
        stroke = Stroke(
            name=f"Stroke {self.stroke_counter}",
            visible=True,
            points=points,
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
        return stroke

    def finalize_stroke_points(self, raw_points: list[Point], brush_size: int) -> list[Point]:
        cleaned = simplify_points(raw_points, min_dist=max(2.0, brush_size * 0.010))
        return chaikin_smooth(cleaned, iterations=3)

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

    def delete_selected_stroke(self) -> None:
        if 0 <= self.selected_stroke_index < len(self.strokes):
            del self.strokes[self.selected_stroke_index]
            if self.strokes:
                self.selected_stroke_index = min(self.selected_stroke_index, len(self.strokes) - 1)
            else:
                self.selected_stroke_index = -1

    def clear_all(self) -> None:
        self.strokes = []
        self.current_points = []
        self.selected_stroke_index = -1
        self.erase_mask = Image.new("L", (self.full_w, self.full_h), 0)
        self._erase_draw = ImageDraw.Draw(self.erase_mask)

    def add_erase_to_mask(self, img_x: int, img_y: int) -> None:
        size = self.settings.brush_size
        r = size // 2
        self._erase_draw.ellipse((img_x - r, img_y - r, img_x + r, img_y + r), fill=255)

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
        from brush_watermark.geometry.points import clamp

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
