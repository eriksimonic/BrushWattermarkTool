from dataclasses import dataclass, field
from typing import Optional

from brush_watermark.geometry.points import Point


DEFAULT_BLEND_MODE = "soft_light"
DEFAULT_TEXT_COLOR = "#ffffff"


@dataclass
class Settings:
    watermark_text: str = "Erik Simonič"
    opacity: int = 22
    font_name: str = "Arial"
    brush_size: int = 120
    angle_offset: int = 0
    mask_softness: int = 1
    text_color: str = DEFAULT_TEXT_COLOR
    auto_fit_text: bool = True
    blend_mode: str = DEFAULT_BLEND_MODE

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        from brush_watermark.rendering.blend import normalize_blend_mode
        from brush_watermark.rendering.colors import normalize_text_color

        return cls(
            watermark_text=str(data.get("watermark_text", cls.watermark_text)),
            opacity=int(data.get("opacity", cls.opacity)),
            font_name=str(data.get("font_name", cls.font_name)),
            brush_size=int(data.get("brush_size", cls.brush_size)),
            angle_offset=int(data.get("angle_offset", cls.angle_offset)),
            mask_softness=int(data.get("mask_softness", cls.mask_softness)),
            text_color=normalize_text_color(data.get("text_color"), cls.text_color),
            auto_fit_text=bool(data.get("auto_fit_text", cls.auto_fit_text)),
            blend_mode=normalize_blend_mode(data.get("blend_mode"), cls.blend_mode),
        )

    def to_dict(self) -> dict:
        return {
            "watermark_text": self.watermark_text,
            "opacity": self.opacity,
            "font_name": self.font_name,
            "brush_size": self.brush_size,
            "angle_offset": self.angle_offset,
            "mask_softness": self.mask_softness,
            "text_color": self.text_color,
            "auto_fit_text": self.auto_fit_text,
            "blend_mode": self.blend_mode,
        }


@dataclass
class Stroke:
    name: str
    points: list[Point]
    brush_size: int
    opacity: int
    blend_mode: str = DEFAULT_BLEND_MODE
    text_color: str = DEFAULT_TEXT_COLOR
    angle_offset: int = 0
    mask_softness: int = 1
    visible: bool = True


@dataclass
class TextSpan:
    points: list[Point]
    font_size: int
    base_width: float
    used_span: float
    start_d: float
    end_d: float
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]


@dataclass
class CanvasView:
    """Read-only snapshot for painting the canvas overlay."""

    strokes: list[Stroke]
    selected_stroke_index: int
    current_points: list[Point]
    current_brush_size: int
    scale: float
    offset_x: float
    offset_y: float
    last_pointer: Optional[tuple[float, float]] = None
    brush_size: int = 120
