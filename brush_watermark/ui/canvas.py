from typing import TYPE_CHECKING, Any, Callable, Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from brush_watermark.geometry.path_text import point_at_distance, smooth_path_for_text
from brush_watermark.geometry.points import normalize_text_direction
from brush_watermark.models import CanvasView
from brush_watermark.services.stamps import render_stamp_rgba, stamp_bounds
from brush_watermark.ui.design_tokens import CANVAS_BG, HANDLE

if TYPE_CHECKING:
    pass


class CanvasWidget(QWidget):
    def __init__(
        self,
        get_view: Callable[[], CanvasView],
        image_to_canvas: Callable[[float, float], tuple[float, float]],
        inside_image: Callable[[float, float], bool],
        on_left_press: Callable[[float, float], None],
        on_left_move: Callable[[float, float], None],
        on_left_release: Callable[[float, float], None],
        on_right_press: Callable[[float, float], None],
        on_right_move: Callable[[float, float], None],
        on_right_release: Callable[[float, float], None],
        on_wheel: Callable[[int, bool], None],
        on_pointer_move: Callable[[float, float], None],
        on_pointer_leave: Callable[[], None],
        text_span_info: Callable[[list, int], Optional[Any]],
        preview_pixmap=None,
    ):
        super().__init__()
        self._get_view = get_view
        self._image_to_canvas = image_to_canvas
        self._inside_image = inside_image
        self._on_left_press = on_left_press
        self._on_left_move = on_left_move
        self._on_left_release = on_left_release
        self._on_right_press = on_right_press
        self._on_right_move = on_right_move
        self._on_right_release = on_right_release
        self._on_wheel = on_wheel
        self._on_pointer_move = on_pointer_move
        self._on_pointer_leave = on_pointer_leave
        self._text_span_info = text_span_info
        self.preview_pixmap = preview_pixmap

        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        view = self._get_view()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(CANVAS_BG))

        if self.preview_pixmap is not None:
            p.drawPixmap(int(view.offset_x), int(view.offset_y), self.preview_pixmap)

        self._draw_overlay(p, view)
        self._draw_cursor(p, view)

    def _draw_polyline(
        self,
        p: QPainter,
        points: list,
        color: str,
        width: float,
        dashed: bool = False,
        alpha: int = 255,
    ):
        if len(points) < 2:
            return
        path = QPainterPath()
        x0, y0 = self._image_to_canvas(points[0][0], points[0][1])
        path.moveTo(x0, y0)
        for x, y in points[1:]:
            cx, cy = self._image_to_canvas(x, y)
            path.lineTo(cx, cy)
        qc = QColor(color)
        qc.setAlpha(alpha)
        pen = QPen(qc, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        if dashed:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawPath(path)

    def _draw_stroke_selection_guide(self, p: QPainter, points: list, label: str):
        if len(points) < 2:
            return
        guide_alpha = 128
        guide_color = QColor(HANDLE)
        guide_color.setAlpha(guide_alpha)
        self._draw_polyline(p, points, HANDLE, 1.0, dashed=True, alpha=guide_alpha)

        sx, sy = points[0]
        ex, ey = points[-1]
        scx, scy = self._image_to_canvas(sx, sy)
        ecx, ecy = self._image_to_canvas(ex, ey)

        p.setPen(QPen(guide_color, 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(scx, scy), 4, 4)
        p.drawEllipse(QPointF(ecx, ecy), 4, 4)
        p.setPen(guide_color)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(QPointF(scx + 6, scy - 8), label)

    def _draw_stamp_selection_guide(self, p: QPainter, stamp, label: str):
        left, top, right, bottom = stamp_bounds(stamp.svg_name, stamp.x, stamp.y, stamp.size)
        x0, y0 = self._image_to_canvas(left, top)
        x1, y1 = self._image_to_canvas(right, bottom)
        guide_color = QColor(HANDLE)
        guide_color.setAlpha(180)
        p.setPen(QPen(guide_color, 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(int(min(x0, x1)), int(min(y0, y1)), int(abs(x1 - x0)), int(abs(y1 - y0)))
        p.setPen(guide_color)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(QPointF(x0 + 4, y0 - 4), label)

    def _draw_stamp_preview(self, p: QPainter, view: CanvasView, svg_name: str, img_x: int, img_y: int, size: int, alpha: int = 120):
        if not svg_name:
            return
        stamp_image = render_stamp_rgba(svg_name, size, None)
        if stamp_image.getbbox() is None:
            return
        left = img_x
        top = img_y - stamp_image.height
        cx, cy = self._image_to_canvas(left, top)
        width = max(1, int(stamp_image.width * view.scale))
        height = max(1, int(stamp_image.height * view.scale))
        from PIL.ImageQt import ImageQt
        from PySide6.QtGui import QPixmap

        qimage = ImageQt(stamp_image)
        pixmap = QPixmap.fromImage(qimage).scaled(
            width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        p.setOpacity(alpha / 255.0)
        p.drawPixmap(int(cx), int(cy), pixmap)
        p.setOpacity(1.0)

    def _draw_span_guide(self, p: QPainter, span_info):
        points = span_info.points
        start_d = span_info.start_d
        end_d = span_info.end_d
        font_size = span_info.font_size

        sampled = []
        d = start_d
        step = max(8.0, font_size / 4.0)
        while d <= end_d:
            x, y, _ = point_at_distance(points, d)
            sampled.append((int(x), int(y)))
            d += step
        x, y, _ = point_at_distance(points, end_d)
        sampled.append((int(x), int(y)))

        self._draw_polyline(p, sampled, "#86efac", 2.0, dashed=True)

        sx, sy = span_info.start_xy
        ex, ey = span_info.end_xy
        scx, scy = self._image_to_canvas(sx, sy)
        ecx, ecy = self._image_to_canvas(ex, ey)

        p.setPen(QPen(QColor("#22c55e"), 2))
        p.drawEllipse(QPointF(scx, scy), 6, 6)
        p.setPen(QPen(QColor("#f59e0b"), 3))
        p.drawEllipse(QPointF(ecx, ecy), 8, 8)

    def _draw_overlay(self, p: QPainter, view: CanvasView):
        if 0 <= view.selected_stroke_index < len(view.strokes):
            stroke = view.strokes[view.selected_stroke_index]
            self._draw_stroke_selection_guide(p, stroke.points, stroke.name)

        if 0 <= view.selected_stamp_index < len(view.stamps):
            stamp = view.stamps[view.selected_stamp_index]
            self._draw_stamp_selection_guide(p, stamp, stamp.name)

        if len(view.current_points) >= 2:
            smooth = smooth_path_for_text(view.current_points)
            smooth = normalize_text_direction(smooth)
            width = max(2.0, view.current_brush_size * max(view.scale, 0.0001) * 0.08)
            self._draw_polyline(p, smooth, "#facc15", width)
            span_info = self._text_span_info(smooth, view.current_brush_size)
            if span_info:
                self._draw_span_guide(p, span_info)

    def _draw_cursor(self, p: QPainter, view: CanvasView):
        if view.last_pointer is None:
            return
        x, y = view.last_pointer
        if not self._inside_image(x, y):
            return
        if view.tool_mode == "stamp" and view.selected_stamp_index < 0 and view.stamp_preview_svg:
            img_x = int((x - view.offset_x) / max(view.scale, 0.0001))
            img_y = int((y - view.offset_y) / max(view.scale, 0.0001))
            self._draw_stamp_preview(p, view, view.stamp_preview_svg, img_x, img_y, view.stamp_size)
            return
        radius = max(1.0, int(view.brush_size) * max(view.scale, 0.0001) / 2)
        p.setPen(QPen(QColor("#facc15"), 2))
        p.drawEllipse(QPointF(x, y), radius, radius)
        p.setPen(QPen(QColor("#facc15"), 1))
        p.drawLine(int(x - 8), int(y), int(x + 8), int(y))
        p.drawLine(int(x), int(y - 8), int(x), int(y + 8))

    def mousePressEvent(self, event: QMouseEvent):
        x, y = event.position().x(), event.position().y()
        if event.button() == Qt.LeftButton:
            self._on_left_press(x, y)
        elif event.button() == Qt.RightButton:
            self._on_right_press(x, y)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        x, y = event.position().x(), event.position().y()
        self._on_pointer_move(x, y)
        if event.buttons() & Qt.LeftButton:
            self._on_left_move(x, y)
        elif event.buttons() & Qt.RightButton:
            self._on_right_move(x, y)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        x, y = event.position().x(), event.position().y()
        if event.button() == Qt.LeftButton:
            self._on_left_release(x, y)
        elif event.button() == Qt.RightButton:
            self._on_right_release(x, y)
        self.update()

    def leaveEvent(self, event):
        self._on_pointer_leave()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta()
        scroll_delta = delta.y() if delta.y() != 0 else delta.x()
        if scroll_delta == 0:
            return
        step = 1 if scroll_delta > 0 else -1
        alt = bool(event.modifiers() & Qt.AltModifier)
        self._on_wheel(step, alt)
        event.accept()
        self.update()
