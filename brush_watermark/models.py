from dataclasses import dataclass
from typing import Literal, Optional

from brush_watermark.geometry.points import Point


DEFAULT_BLEND_MODE = "soft_light"
DEFAULT_TEXT_COLOR = "#ffffff"
ToolMode = Literal["paint", "stamp"]
LayerKind = Literal["stroke", "stamp"]


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
    repeat_text: bool = False
    repeat_spacing: int = 5
    blend_mode: str = DEFAULT_BLEND_MODE
    tool_mode: ToolMode = "paint"
    stamp_name: str = ""
    stamp_size: int = 120
    use_svg_colors: bool = True

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
            repeat_text=bool(data.get("repeat_text", cls.repeat_text)),
            repeat_spacing=max(0, int(data.get("repeat_spacing", cls.repeat_spacing))),
            blend_mode=normalize_blend_mode(data.get("blend_mode"), cls.blend_mode),
            tool_mode=_normalize_tool_mode(data.get("tool_mode"), cls.tool_mode),
            stamp_name=str(data.get("stamp_name", cls.stamp_name)),
            stamp_size=int(data.get("stamp_size", cls.stamp_size)),
            use_svg_colors=bool(data.get("use_svg_colors", cls.use_svg_colors)),
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
            "repeat_text": self.repeat_text,
            "repeat_spacing": self.repeat_spacing,
            "blend_mode": self.blend_mode,
            "tool_mode": self.tool_mode,
            "stamp_name": self.stamp_name,
            "stamp_size": self.stamp_size,
            "use_svg_colors": self.use_svg_colors,
        }


def _normalize_tool_mode(value: object, fallback: ToolMode) -> ToolMode:
    mode = str(value or fallback).strip().lower()
    if mode in ("paint", "stamp"):
        return mode  # type: ignore[return-value]
    return fallback


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
    repeat_text: bool = False
    repeat_spacing: int = 5
    visible: bool = True


@dataclass
class Stamp:
    name: str
    svg_name: str
    x: int
    y: int
    size: int
    opacity: int
    blend_mode: str = DEFAULT_BLEND_MODE
    tint_color: str | None = None
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
    stamps: list[Stamp]
    selected_stroke_index: int
    selected_stamp_index: int
    tool_mode: ToolMode
    current_points: list[Point]
    current_brush_size: int
    scale: float
    offset_x: float
    offset_y: float
    last_pointer: Optional[tuple[float, float]] = None
    brush_size: int = 120
    stamp_size: int = 120
    selected_stamp_svg: str = ""
    stamp_preview_svg: str = ""
    dragging_stamp: bool = False
