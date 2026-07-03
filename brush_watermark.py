import sys
import os
import json
import math
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from PIL.ImageQt import ImageQt

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Lightroom Brush Watermark"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}
CONFIG_DIR = Path.home() / ".lightroom_brush_watermark"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "watermark_text": "Erik Simonič",
    "opacity": 22,
    "font_name": "Arial",
    "brush_size": 120,
    "angle_offset": 0,
    "mask_softness": 1,
    "text_color": "white",
    "auto_fit_text": True,
}

FONT_SIZE_RATIO = 0.52
TEXT_SPAN_FILL = 0.85
Point = Tuple[int, int]


def clamp(value, low, high):
    return max(low, min(high, value))


def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                settings.update(saved)
    except Exception:
        pass
    return settings


def save_settings(settings):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def reveal_in_explorer(path: Path):
    resolved = path.resolve()
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(resolved)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(resolved)])
    else:
        subprocess.Popen(["xdg-open", str(resolved.parent)])


def font_candidates():
    return {
        "Arial": [
            r"C:\Windows\Fonts\arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "Arial Bold": [
            r"C:\Windows\Fonts\arialbd.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "Segoe UI": [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ],
        "Verdana": [
            r"C:\Windows\Fonts\verdana.ttf",
            "/System/Library/Fonts/Supplemental/Verdana.ttf",
        ],
        "Tahoma": [r"C:\Windows\Fonts\tahoma.ttf"],
        "DejaVu Sans": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    }


def find_font_path(font_name: str) -> Optional[str]:
    for path in font_candidates().get(font_name, []):
        if os.path.exists(path):
            return path

    win_fonts = Path(r"C:\Windows\Fonts")
    if win_fonts.exists():
        normalized = font_name.lower().replace(" ", "")
        for item in win_fonts.glob("*.ttf"):
            if normalized in item.stem.lower().replace(" ", ""):
                return str(item)
    return None


def load_font(font_name: str, size: int):
    path = find_font_path(font_name)
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx = ax + t * dx
    qy = ay + t * dy
    return math.hypot(px - qx, py - qy)


def path_length(points: List[Point]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def simplify_points(points: List[Point], min_dist: float = 3.0) -> List[Point]:
    if not points:
        return []
    out = [points[0]]
    for pt in points[1:]:
        if dist(out[-1], pt) >= min_dist:
            out.append(pt)
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def chaikin_smooth(points: List[Point], iterations: int = 3) -> List[Point]:
    if len(points) < 3:
        return points
    smoothed = [(float(x), float(y)) for x, y in points]
    for _ in range(iterations):
        new_points = [smoothed[0]]
        for i in range(len(smoothed) - 1):
            x0, y0 = smoothed[i]
            x1, y1 = smoothed[i + 1]
            q = (0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1)
            r = (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)
            new_points.extend([q, r])
        new_points.append(smoothed[-1])
        smoothed = new_points
    return [(int(round(x)), int(round(y))) for x, y in smoothed]


def normalize_text_direction(points: List[Point]) -> List[Point]:
    if len(points) < 2:
        return points
    start = points[0]
    end = points[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if abs(dx) >= abs(dy):
        return points if dx >= 0 else list(reversed(points))
    return points if dy <= 0 else list(reversed(points))


def point_at_distance(points: List[Point], target: float):
    if len(points) < 2:
        x, y = points[0]
        return x, y, 0.0
    remaining = target
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        seg = dist(p0, p1)
        if seg <= 0:
            continue
        if remaining <= seg:
            t = remaining / seg
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            return x, y, angle
        remaining -= seg
    p0 = points[-2]
    p1 = points[-1]
    angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return p1[0], p1[1], angle


def averaged_angle(points: List[Point], center_d: float, window: float):
    d0 = max(0.0, center_d - window)
    d1 = center_d + window
    x0, y0, _ = point_at_distance(points, d0)
    x1, y1, _ = point_at_distance(points, d1)
    return math.atan2(y1 - y0, x1 - x0)


def angle_unwrap(reference: float, angle: float) -> float:
    while angle - reference > math.pi:
        angle -= 2 * math.pi
    while angle - reference < -math.pi:
        angle += 2 * math.pi
    return angle


def blend_angles(a: float, b: float, amount: float) -> float:
    b = angle_unwrap(a, b)
    return a + (b - a) * amount


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    return QPixmap.fromImage(ImageQt(image))


class CanvasWidget(QWidget):
    def __init__(self, app_window: "BrushWatermarkQtPolished"):
        super().__init__()
        self.app = app_window
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#0f172a"))

        if self.app.preview_pixmap is not None:
            p.drawPixmap(self.app.offset_x, self.app.offset_y, self.app.preview_pixmap)

        self.draw_overlay(p)
        self.draw_cursor(p)

    def draw_polyline(self, p: QPainter, points: List[Point], color: str, width: float, dashed: bool = False, alpha: int = 255):
        if len(points) < 2:
            return
        path = QPainterPath()
        x0, y0 = self.app.image_to_canvas_xy(points[0][0], points[0][1])
        path.moveTo(x0, y0)
        for x, y in points[1:]:
            cx, cy = self.app.image_to_canvas_xy(x, y)
            path.lineTo(cx, cy)
        qc = QColor(color)
        qc.setAlpha(alpha)
        pen = QPen(qc, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        if dashed:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawPath(path)

    def draw_stroke_selection_guide(self, p: QPainter, points: List[Point], label: str):
        if len(points) < 2:
            return

        guide_alpha = 128  # ~50% — visible enough to select, faint enough for opacity tuning
        guide_color = QColor("#38bdf8")
        guide_color.setAlpha(guide_alpha)

        self.draw_polyline(p, points, "#38bdf8", 1.0, dashed=True, alpha=guide_alpha)

        sx, sy = points[0]
        ex, ey = points[-1]
        scx, scy = self.app.image_to_canvas_xy(sx, sy)
        ecx, ecy = self.app.image_to_canvas_xy(ex, ey)

        p.setPen(QPen(guide_color, 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(scx, scy), 4, 4)
        p.drawEllipse(QPointF(ecx, ecy), 4, 4)

        p.setPen(guide_color)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(QPointF(scx + 6, scy - 8), label)

    def draw_span_guide(self, p: QPainter, span_info: Dict[str, Any]):
        points = span_info["points"]
        start_d = span_info["start_d"]
        end_d = span_info["end_d"]
        font_size = span_info["font_size"]

        sampled: List[Point] = []
        d = start_d
        step = max(8.0, font_size / 4.0)
        while d <= end_d:
            x, y, _ = point_at_distance(points, d)
            sampled.append((int(x), int(y)))
            d += step
        x, y, _ = point_at_distance(points, end_d)
        sampled.append((int(x), int(y)))

        self.draw_polyline(p, sampled, "#86efac", 2.0, dashed=True)

        sx, sy = span_info["start_xy"]
        ex, ey = span_info["end_xy"]
        scx, scy = self.app.image_to_canvas_xy(sx, sy)
        ecx, ecy = self.app.image_to_canvas_xy(ex, ey)

        p.setPen(QPen(QColor("#22c55e"), 2))
        p.drawEllipse(QPointF(scx, scy), 6, 6)
        p.setPen(QPen(QColor("#f59e0b"), 3))
        p.drawEllipse(QPointF(ecx, ecy), 8, 8)

    def draw_overlay(self, p: QPainter):
        if 0 <= self.app.selected_stroke_index < len(self.app.strokes):
            stroke = self.app.strokes[self.app.selected_stroke_index]
            pts = stroke.get("points", [])
            label = stroke.get("name", f"Stroke {self.app.selected_stroke_index + 1}")
            self.draw_stroke_selection_guide(p, pts, label)

        if len(self.app.current_points) >= 2:
            smooth = chaikin_smooth(simplify_points(self.app.current_points, min_dist=3.0), iterations=3)
            smooth = normalize_text_direction(smooth)
            width = max(2.0, self.app.current_brush_size * max(self.app.scale, 0.0001) * 0.08)
            self.draw_polyline(p, smooth, "#facc15", width)
            span_info = self.app.text_span_info(smooth, self.app.current_brush_size)
            if span_info:
                self.draw_span_guide(p, span_info)

    def draw_cursor(self, p: QPainter):
        if self.app.last_pointer is None:
            return
        x, y = self.app.last_pointer
        if not self.app.inside_image_canvas(x, y):
            return
        radius = max(1.0, int(self.app.brush_size_slider.value()) * max(self.app.scale, 0.0001) / 2)
        p.setPen(QPen(QColor("#facc15"), 2))
        p.drawEllipse(QPointF(x, y), radius, radius)
        p.setPen(QPen(QColor("#facc15"), 1))
        p.drawLine(int(x - 8), int(y), int(x + 8), int(y))
        p.drawLine(int(x), int(y - 8), int(x), int(y + 8))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.app.start_left_interaction(event.position().x(), event.position().y())
        elif event.button() == Qt.RightButton:
            self.app.start_erase_interaction(event.position().x(), event.position().y())
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.app.last_pointer = (event.position().x(), event.position().y())
        if event.buttons() & Qt.LeftButton:
            self.app.continue_left_interaction(event.position().x(), event.position().y())
        elif event.buttons() & Qt.RightButton:
            self.app.continue_erase_interaction(event.position().x(), event.position().y())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.app.finish_left_interaction(event.position().x(), event.position().y())
        elif event.button() == Qt.RightButton:
            self.app.finish_erase_interaction(event.position().x(), event.position().y())
        self.update()

    def leaveEvent(self, event):
        self.app.last_pointer = None
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta()
        # Qt maps Alt+wheel to horizontal scroll on Windows, so y is often 0.
        scroll_delta = delta.y() if delta.y() != 0 else delta.x()
        if scroll_delta == 0:
            return
        step = 1 if scroll_delta > 0 else -1
        alt = bool(event.modifiers() & Qt.AltModifier)
        self.app.handle_wheel(step, alt)
        event.accept()
        self.update()


class BrushWatermarkQtPolished(QMainWindow):
    def __init__(self, image_path: Path):
        super().__init__()
        self.image_path = Path(image_path)
        if not self.image_path.exists():
            raise FileNotFoundError(f"File not found: {self.image_path}")
        if self.image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Input must be a JPG or JPEG file.")

        self.settings = load_settings()
        self.original = Image.open(self.image_path).convert("RGB")
        self.full_w, self.full_h = self.original.size

        self.strokes: List[Dict[str, Any]] = []
        self.selected_stroke_index = -1
        self.stroke_counter = 1

        self.erase_mask = Image.new("L", (self.full_w, self.full_h), 0)
        self.erase_draw = ImageDraw.Draw(self.erase_mask)

        self.current_points: List[Point] = []
        self.current_brush_size = int(self.settings.get("brush_size", DEFAULT_SETTINGS["brush_size"]))
        self.is_painting = False
        self.is_erasing = False
        self.last_img_xy = None
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False
        self._list_toggle_row = -1
        self._ignore_list_selection = False

        self.preview_pixmap: Optional[QPixmap] = None
        self.scale = 1.0
        self.display_w = 1
        self.display_h = 1
        self.offset_x = 0
        self.offset_y = 0
        self.last_pointer = None
        self.refresh_pending = False

        self.setWindowTitle(f"{APP_NAME} - {self.image_path.name}")
        self.resize(1560, 980)
        self.setMinimumSize(1180, 780)

        self.build_ui()
        self.apply_styles()
        self.update_labels()
        self.schedule_preview(1)

    def apply_styles(self):
        panel = "#111827"
        border = "#374151"
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
                background: {panel};
                color: #e5e7eb;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
            }}
            QFrame#Card {{
                background: {panel};
                border: none;
            }}
            QLabel {{
                background: transparent;
            }}
            QLabel#SectionTitle {{
                font-size: 11px;
                font-weight: 700;
                color: #d1d5db;
                padding-bottom: 4px;
                border-bottom: 1px solid {border};
            }}
            QLabel#FieldLabel {{
                color: #9ca3af;
                font-size: 11px;
            }}
            QLabel#HintLabel {{
                color: #6b7280;
                font-size: 10px;
            }}
            QLineEdit, QComboBox, QListWidget, QPushButton {{
                background: {panel};
                border: 1px solid {border};
                border-radius: 5px;
                color: #f9fafb;
                font-size: 11px;
            }}
            QLineEdit, QComboBox {{
                padding: 2px 6px;
                min-height: 22px;
                max-height: 22px;
            }}
            QComboBox {{
                padding-right: 4px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 16px;
                background: {panel};
                border-left: 1px solid {border};
            }}
            QComboBox::down-arrow {{
                width: 8px;
                height: 8px;
            }}
            QComboBox QAbstractItemView {{
                background: {panel};
                color: #f9fafb;
                border: 1px solid {border};
                selection-background-color: #2563eb;
                selection-color: white;
            }}
            QLineEdit:focus, QComboBox:focus, QListWidget:focus {{
                border: 1px solid #60a5fa;
            }}
            QListWidget {{
                padding: 4px;
            }}
            QListWidget::item {{
                background: transparent;
                padding: 4px 6px;
                border-radius: 4px;
                font-size: 11px;
            }}
            QListWidget::item:selected {{
                background: #2563eb;
                color: white;
            }}
            QPushButton {{
                padding: 4px 8px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                border-color: #6b7280;
            }}
            QPushButton#PrimaryButton {{
                background: #2563eb;
                color: white;
                border: 1px solid #2563eb;
                font-weight: 600;
            }}
            QPushButton#PrimaryButton:hover {{
                background: #1d4ed8;
                border-color: #1d4ed8;
            }}
            QScrollArea {{
                border: none;
            }}
            QCheckBox {{
                spacing: 6px;
                font-size: 11px;
                background: transparent;
            }}
            QSlider {{
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                border: 0;
                height: 4px;
                background: {border};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #60a5fa;
                border: 0;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            """
        )

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.canvas = CanvasWidget(self)
        root.addWidget(self.canvas, 1)

        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(320)
        root.addWidget(self.sidebar_scroll)

        sidebar = QWidget()
        self.sidebar_scroll.setWidget(sidebar)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 12, 12, 12)
        side.setSpacing(10)

        defaults_card, defaults_layout = self.make_card("New stroke defaults")
        side.addWidget(defaults_card)

        self.watermark_text_edit = QLineEdit(str(self.settings.get("watermark_text", DEFAULT_SETTINGS["watermark_text"])))
        self.font_combo = QComboBox()
        self.font_combo.addItems(list(font_candidates().keys()))
        self.font_combo.setCurrentText(str(self.settings.get("font_name", DEFAULT_SETTINGS["font_name"])))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["white", "black"])
        self.color_combo.setCurrentText(str(self.settings.get("text_color", DEFAULT_SETTINGS["text_color"])))

        self.opacity_value_label = self.make_field_label("Opacity")
        self.opacity_slider = self.make_slider(1, 100, int(self.settings.get("opacity", DEFAULT_SETTINGS["opacity"])))
        self.brush_value_label = self.make_field_label("Brush")
        self.brush_size_slider = self.make_slider(5, 600, int(self.settings.get("brush_size", DEFAULT_SETTINGS["brush_size"])))
        self.font_size_value_label = QLabel()
        self.font_size_value_label.setObjectName("HintLabel")
        self.angle_value_label = self.make_field_label("Angle")
        self.angle_slider = self.make_slider(-20, 20, int(self.settings.get("angle_offset", DEFAULT_SETTINGS["angle_offset"])))
        self.softness_value_label = self.make_field_label("Softness")
        self.softness_slider = self.make_slider(0, 20, int(self.settings.get("mask_softness", DEFAULT_SETTINGS["mask_softness"])))
        self.auto_fit_check = QCheckBox("Auto fit text to stroke")
        self.auto_fit_check.setChecked(bool(self.settings.get("auto_fit_text", DEFAULT_SETTINGS["auto_fit_text"])))

        self.add_form_row(defaults_layout, "Text", self.watermark_text_edit)
        self.add_form_row(defaults_layout, "Font", self.font_combo)
        self.add_form_row(defaults_layout, "Color", self.color_combo)
        self.add_slider_row(defaults_layout, self.opacity_value_label, self.opacity_slider)
        self.add_slider_row(defaults_layout, self.brush_value_label, self.brush_size_slider)
        defaults_layout.addWidget(self.font_size_value_label)
        self.add_slider_row(defaults_layout, self.angle_value_label, self.angle_slider)
        self.add_slider_row(defaults_layout, self.softness_value_label, self.softness_slider)
        defaults_layout.addWidget(self.auto_fit_check)

        stroke_card, stroke_layout = self.make_card("Layers")
        side.addWidget(stroke_card)

        self.stroke_list = QListWidget()
        self.stroke_list.setFixedHeight(96)
        self.stroke_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        stroke_layout.addWidget(self.stroke_list)

        layer_actions = QHBoxLayout()
        layer_actions.setSpacing(6)
        layer_actions.setContentsMargins(0, 8, 0, 0)
        self.delete_selected_btn = QPushButton("Delete")
        self.delete_all_btn = QPushButton("Clear all")
        layer_actions.addWidget(self.delete_selected_btn)
        layer_actions.addWidget(self.delete_all_btn)
        side.addLayout(layer_actions)

        selected_card, selected_layout = self.make_card("Selected layer")
        side.addWidget(selected_card)
        self.selected_info_label = QLabel("No stroke selected")
        self.selected_info_label.setObjectName("HintLabel")
        self.sel_brush_value_label = self.make_field_label("Brush")
        self.sel_brush_slider = self.make_slider(5, 600, 120)
        self.sel_font_value_label = QLabel()
        self.sel_font_value_label.setObjectName("HintLabel")
        self.sel_opacity_value_label = self.make_field_label("Opacity")
        self.sel_opacity_slider = self.make_slider(1, 100, 22)
        selected_layout.addWidget(self.selected_info_label)
        self.add_slider_row(selected_layout, self.sel_brush_value_label, self.sel_brush_slider)
        selected_layout.addWidget(self.sel_font_value_label)
        self.add_slider_row(selected_layout, self.sel_opacity_value_label, self.sel_opacity_slider)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        self.reveal_in_explorer_check = QCheckBox("Show in Explorer after save")
        self.reveal_in_explorer_check.setChecked(True)
        actions.addWidget(self.reveal_in_explorer_check)
        self.ok_button = QPushButton("Save and close")
        self.ok_button.setObjectName("PrimaryButton")
        self.exit_button = QPushButton("Exit without saving")
        actions.addWidget(self.ok_button)
        actions.addWidget(self.exit_button)
        side.addLayout(actions)

        help_card, help_layout = self.make_card("Help")
        side.addWidget(help_card)
        help_text = QLabel(
            "Paint: left mouse · Select: click watermark · Deselect: click again · "
            "Erase: right mouse · Wheel: opacity · Alt+wheel: brush/font size · "
            "Selected layer shows a faint guide."
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("HintLabel")
        help_layout.addWidget(help_text)
        side.addStretch(1)

        self.watermark_text_edit.textChanged.connect(self.schedule_preview)
        self.font_combo.currentTextChanged.connect(self.schedule_preview)
        self.color_combo.currentTextChanged.connect(self.schedule_preview)
        self.opacity_slider.valueChanged.connect(self.global_controls_changed)
        self.brush_size_slider.valueChanged.connect(self.global_controls_changed)
        self.angle_slider.valueChanged.connect(self.schedule_preview)
        self.softness_slider.valueChanged.connect(self.schedule_preview)
        self.auto_fit_check.toggled.connect(self.schedule_preview)

        self.stroke_list.currentRowChanged.connect(self.on_layer_selected)
        self.stroke_list.itemPressed.connect(self.on_layer_item_pressed)
        self.stroke_list.itemClicked.connect(self.on_layer_item_clicked)
        self.delete_selected_btn.clicked.connect(self.delete_selected_stroke)
        self.delete_all_btn.clicked.connect(self.clear_all)
        self.sel_brush_slider.valueChanged.connect(self.selected_stroke_controls_changed)
        self.sel_opacity_slider.valueChanged.connect(self.selected_stroke_controls_changed)
        self.ok_button.clicked.connect(self.save_and_close)
        self.exit_button.clicked.connect(self.exit_without_saving)

    def make_card(self, title: str):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)
        lbl = QLabel(title)
        lbl.setObjectName("SectionTitle")
        layout.addWidget(lbl)
        return card, layout

    def make_field_label(self, prefix: str) -> QLabel:
        label = QLabel(prefix)
        label.setObjectName("FieldLabel")
        label.setProperty("prefix", prefix)
        return label

    def set_field_label_value(self, label: QLabel, value_text: str):
        prefix = label.property("prefix") or ""
        label.setText(f"{prefix}  {value_text}" if prefix else value_text)

    def add_form_row(self, layout: QVBoxLayout, label_text: str, widget: QWidget, label_width: int = 52):
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        label.setFixedWidth(label_width)
        row.addWidget(label)
        row.addWidget(widget, 1)
        layout.addLayout(row)

    def add_slider_row(self, layout: QVBoxLayout, label: QLabel, slider: QSlider):
        block = QVBoxLayout()
        block.setSpacing(2)
        block.addWidget(label)
        block.addWidget(slider)
        layout.addLayout(block)

    def make_slider(self, low: int, high: int, value: int) -> QSlider:
        s = QSlider(Qt.Horizontal)
        s.setRange(low, high)
        s.setValue(value)
        return s

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_preview(1)

    def current_settings(self):
        return {
            "watermark_text": self.watermark_text_edit.text(),
            "opacity": int(self.opacity_slider.value()),
            "font_name": self.font_combo.currentText(),
            "brush_size": int(self.brush_size_slider.value()),
            "angle_offset": int(self.angle_slider.value()),
            "mask_softness": int(self.softness_slider.value()),
            "text_color": self.color_combo.currentText(),
            "auto_fit_text": bool(self.auto_fit_check.isChecked()),
        }

    def font_size_from_brush(self, brush_size: int) -> int:
        return int(clamp(round(brush_size * FONT_SIZE_RATIO), 10, 260))

    def visible_strokes(self):
        return [s for s in self.strokes if s.get("visible", True)]

    def update_labels(self):
        brush = int(self.brush_size_slider.value())
        font = self.font_size_from_brush(brush)
        self.set_field_label_value(self.opacity_value_label, f"{int(self.opacity_slider.value())}%")
        self.set_field_label_value(self.brush_value_label, f"{brush} px")
        self.font_size_value_label.setText(f"Font {font} px (follows brush)")
        self.set_field_label_value(self.angle_value_label, f"{int(self.angle_slider.value())}°")
        self.set_field_label_value(self.softness_value_label, f"{int(self.softness_slider.value())} px")

        enabled = 0 <= self.selected_stroke_index < len(self.strokes)
        self.sel_brush_slider.setEnabled(enabled)
        self.sel_opacity_slider.setEnabled(enabled)
        self.delete_selected_btn.setEnabled(enabled)

        if enabled:
            stroke = self.strokes[self.selected_stroke_index]
            sbrush = int(self.sel_brush_slider.value())
            visibility_text = "visible" if stroke.get("visible", True) else "hidden"
            self.selected_info_label.setText(f"{stroke.get('name', 'Stroke')} · {visibility_text}")
            self.set_field_label_value(self.sel_brush_value_label, f"{sbrush} px")
            self.sel_font_value_label.setText(f"Font {self.font_size_from_brush(sbrush)} px")
            self.set_field_label_value(self.sel_opacity_value_label, f"{int(self.sel_opacity_slider.value())}%")
        else:
            self.selected_info_label.setText("No stroke selected")
            self.set_field_label_value(self.sel_brush_value_label, "—")
            self.sel_font_value_label.setText("")
            self.set_field_label_value(self.sel_opacity_value_label, "—")

    def global_controls_changed(self):
        save_settings(self.current_settings())
        self.update_labels()
        self.canvas.update()
        self.schedule_preview()

    def selected_stroke_controls_changed(self):
        if 0 <= self.selected_stroke_index < len(self.strokes):
            stroke = self.strokes[self.selected_stroke_index]
            stroke["brush_size"] = int(self.sel_brush_slider.value())
            stroke["opacity"] = int(self.sel_opacity_slider.value())
            self.refresh_stroke_list()
            self.update_labels()
            self.schedule_preview()

    def stroke_list_text(self, idx: int, stroke: Dict[str, Any]):
        eye = "👁" if stroke.get("visible", True) else "🚫"
        length = int(path_length(stroke.get("points", [])))
        return f"{eye}  {stroke.get('name', f'Stroke {idx+1}')}  |  len {length}px  |  b{stroke['brush_size']}  |  o{stroke['opacity']}%"

    def sync_list_selection(self):
        self._ignore_list_selection = True
        self.stroke_list.blockSignals(True)
        if 0 <= self.selected_stroke_index < len(self.strokes):
            self.stroke_list.setCurrentRow(self.selected_stroke_index)
        else:
            self.stroke_list.clearSelection()
            self.stroke_list.setCurrentRow(-1)
        self.stroke_list.blockSignals(False)
        self._ignore_list_selection = False

    def refresh_stroke_list(self):
        self.stroke_list.blockSignals(True)
        self.stroke_list.clear()
        for idx, stroke in enumerate(self.strokes):
            item = QListWidgetItem(self.stroke_list_text(idx, stroke))
            self.stroke_list.addItem(item)
        self.stroke_list.blockSignals(False)
        self.sync_list_selection()

    def on_layer_selected(self, index: int):
        if self._ignore_list_selection:
            return
        if index < 0:
            if self.selected_stroke_index >= 0:
                self.select_stroke_by_index(-1)
            return
        if index == self.selected_stroke_index:
            return
        self.select_stroke_by_index(index)

    def on_layer_item_pressed(self, item: QListWidgetItem):
        row = self.stroke_list.row(item)
        if row < 0:
            return
        if row == self.selected_stroke_index:
            self._list_toggle_row = row
            return
        self._list_toggle_row = -1
        self.select_stroke_by_index(row)

    def on_layer_item_clicked(self, item: QListWidgetItem):
        if self._ignore_list_selection:
            return
        row = self.stroke_list.row(item)
        if row >= 0 and row == self._list_toggle_row and row == self.selected_stroke_index:
            self._list_toggle_row = -1
            self.select_stroke_by_index(-1)
            return
        self._list_toggle_row = -1

    def clear_left_interaction(self):
        self.current_points = []
        self.last_img_xy = None
        self.is_painting = False
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False

    def handle_wheel(self, step: int, alt: bool):
        if 0 <= self.selected_stroke_index < len(self.strokes):
            if alt:
                value = clamp(self.sel_brush_slider.value() + step * 12, 5, 600)
                self.sel_brush_slider.setValue(int(value))
            else:
                value = clamp(self.sel_opacity_slider.value() + step * 2, 1, 100)
                self.sel_opacity_slider.setValue(int(value))
        else:
            if alt:
                value = clamp(self.brush_size_slider.value() + step * 12, 5, 600)
                self.brush_size_slider.setValue(int(value))
            else:
                value = clamp(self.opacity_slider.value() + step * 2, 1, 100)
                self.opacity_slider.setValue(int(value))

    def select_stroke_by_index(self, index: int, refresh_preview: bool = True):
        if index < 0 or index >= len(self.strokes):
            self.selected_stroke_index = -1
            self.sync_list_selection()
            self.update_labels()
            if refresh_preview:
                self.schedule_preview()
            return

        self.selected_stroke_index = index
        self.sync_list_selection()
        stroke = self.strokes[index]
        self.sel_brush_slider.blockSignals(True)
        self.sel_opacity_slider.blockSignals(True)
        self.sel_brush_slider.setValue(int(stroke["brush_size"]))
        self.sel_opacity_slider.setValue(int(stroke["opacity"]))
        self.sel_brush_slider.blockSignals(False)
        self.sel_opacity_slider.blockSignals(False)
        self.update_labels()
        if refresh_preview:
            self.schedule_preview()

    def canvas_to_image_xy(self, canvas_x, canvas_y):
        x = (canvas_x - self.offset_x) / self.scale
        y = (canvas_y - self.offset_y) / self.scale
        return int(clamp(x, 0, self.full_w - 1)), int(clamp(y, 0, self.full_h - 1))

    def image_to_canvas_xy(self, x, y):
        return self.offset_x + x * self.scale, self.offset_y + y * self.scale

    def inside_image_canvas(self, canvas_x, canvas_y):
        return (
            self.offset_x <= canvas_x <= self.offset_x + self.display_w
            and self.offset_y <= canvas_y <= self.offset_y + self.display_h
        )

    def schedule_preview(self, delay_ms: int = 50):
        self.update_labels()
        save_settings(self.current_settings())
        if self.refresh_pending:
            return
        self.refresh_pending = True
        QTimer.singleShot(delay_ms, self.refresh_preview)

    def text_dimensions(self, text: str, font_name: str, font_size: int):
        font = load_font(font_name, font_size)
        dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), text, font=font)
        return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1]), bbox

    def fitted_font_size(self, points: List[Point], brush_size: int, text: str):
        if not text.strip():
            return self.font_size_from_brush(brush_size)
        length = path_length(points)
        if length <= 0:
            return self.font_size_from_brush(brush_size)
        size = min(self.font_size_from_brush(brush_size), max(10, int(brush_size * 0.70)))
        if not self.auto_fit_check.isChecked():
            return size
        for candidate in range(size, 9, -1):
            text_w, _, _ = self.text_dimensions(text, self.font_combo.currentText(), candidate)
            if text_w <= length * 0.92:
                return candidate
        return 10

    def make_stroke_mask(self, width: int, height: int, stroke_items: List[Dict[str, Any]]):
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        for item in stroke_items:
            if not item.get("visible", True):
                continue
            points = item.get("points", [])
            brush_size = int(item.get("brush_size", int(self.brush_size_slider.value())))
            if len(points) == 1:
                x, y = points[0]
                r = brush_size // 2
                draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
            elif len(points) > 1:
                draw.line(points, fill=255, width=brush_size, joint="curve")
                r = brush_size // 2
                for x, y in (points[0], points[-1]):
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        soften = int(self.softness_slider.value())
        if soften > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=soften))
        return mask

    def build_glyph_cache(self, text: str, font, fill):
        dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy)
        glyphs = []
        for ch in text:
            bbox = draw.textbbox((0, 0), ch, font=font)
            glyph_w = max(1, bbox[2] - bbox[0])
            glyph_h = max(1, bbox[3] - bbox[1])
            advance = max(1, glyph_w)
            pad = max(4, int(glyph_h * 0.25))
            glyph = Image.new("RGBA", (glyph_w + pad * 2, glyph_h + pad * 2), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glyph)
            gd.text((pad - bbox[0], pad - bbox[1]), ch, font=font, fill=fill)
            glyphs.append((glyph, advance))
        return glyphs

    def text_span_info(self, points: List[Point], brush_size: int):
        text = self.watermark_text_edit.text().strip()
        if not text or len(points) < 2:
            return None
        points = normalize_text_direction(points)
        length = path_length(points)
        if length < 8:
            return None
        font_size = self.fitted_font_size(points, brush_size, text)
        font = load_font(self.font_combo.currentText(), font_size)
        glyphs = self.build_glyph_cache(text, font, (255, 255, 255, 255))
        base_width = sum(g[1] for g in glyphs)
        usable_length = length * 0.92
        used_span = min(usable_length, base_width + max(0.0, (usable_length - base_width) * TEXT_SPAN_FILL))
        start_d = max(0.0, (length - used_span) / 2.0)
        end_d = min(length, start_d + used_span)
        sx, sy, _ = point_at_distance(points, start_d)
        ex, ey, _ = point_at_distance(points, end_d)
        return {
            "points": points,
            "font_size": font_size,
            "base_width": base_width,
            "used_span": used_span,
            "start_d": start_d,
            "end_d": end_d,
            "start_xy": (sx, sy),
            "end_xy": (ex, ey),
        }

    def draw_centered_rotated(self, layer: Image.Image, glyph: Image.Image, x: float, y: float, angle_degrees: float):
        rotated = glyph.rotate(angle_degrees, expand=True, resample=Image.Resampling.BICUBIC)
        px = int(x - rotated.size[0] / 2)
        py = int(y - rotated.size[1] / 2)
        layer.alpha_composite(rotated, (px, py))

    def draw_text_on_path_once(self, layer: Image.Image, item: Dict[str, Any]):
        if not item.get("visible", True):
            return
        raw_points = item.get("points", [])
        if len(raw_points) < 2:
            return
        points = normalize_text_direction(raw_points)
        text = self.watermark_text_edit.text().strip()
        if not text:
            return
        length = path_length(points)
        if length < 8:
            return
        brush_size = int(item.get("brush_size", self.brush_size_slider.value()))
        opacity = int(item.get("opacity", self.opacity_slider.value()))
        font_size = self.fitted_font_size(points, brush_size, text)
        font = load_font(self.font_combo.currentText(), font_size)
        alpha = int(255 * clamp(opacity, 1, 100) / 100)
        fill = (255, 255, 255, alpha) if self.color_combo.currentText() == "white" else (0, 0, 0, alpha)
        glyphs = self.build_glyph_cache(text, font, fill)
        if not glyphs:
            return
        base_width = sum(g[1] for g in glyphs)
        usable_length = length * 0.92
        used_span = min(usable_length, base_width + max(0.0, (usable_length - base_width) * TEXT_SPAN_FILL))
        start = max(0.0, (length - used_span) / 2.0)
        total_extra = max(0.0, used_span - base_width)
        gap_extra = total_extra / max(1, len(glyphs) - 1)

        x0, y0, _ = point_at_distance(points, start)
        x1, y1, _ = point_at_distance(points, start + used_span)
        baseline_angle = math.atan2(y1 - y0, x1 - x0) + math.radians(int(self.angle_slider.value()))

        pos = start
        prev_angle = baseline_angle
        for glyph, advance in glyphs:
            center_d = pos + advance / 2.0
            x, y, _ = point_at_distance(points, center_d)
            local_angle = averaged_angle(points, center_d, max(font_size * 2.4, 40))
            local_angle = angle_unwrap(baseline_angle, local_angle)
            mixed_angle = blend_angles(baseline_angle, local_angle, 0.28)
            mixed_angle = angle_unwrap(prev_angle, mixed_angle)
            max_step = math.radians(10)
            delta = mixed_angle - prev_angle
            if delta > max_step:
                mixed_angle = prev_angle + max_step
            elif delta < -max_step:
                mixed_angle = prev_angle - max_step
            self.draw_centered_rotated(layer, glyph, x, y, math.degrees(mixed_angle))
            prev_angle = mixed_angle
            pos += advance + gap_extra

    def scaled_strokes(self, scale_factor: float):
        if abs(scale_factor - 1.0) < 0.0001:
            return self.strokes
        scaled = []
        for item in self.strokes:
            pts = [(int(round(x * scale_factor)), int(round(y * scale_factor))) for x, y in item.get("points", [])]
            scaled.append({
                "name": item.get("name", "Stroke"),
                "visible": item.get("visible", True),
                "points": pts,
                "brush_size": max(1, int(round(item.get("brush_size", self.brush_size_slider.value()) * scale_factor))),
                "opacity": int(item.get("opacity", self.opacity_slider.value())),
            })
        return scaled

    def make_watermark_layer_for_strokes(self, width: int, height: int, strokes: List[Dict[str, Any]], scale_factor: float = 1.0):
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for item in strokes:
            self.draw_text_on_path_once(layer, item)
        stroke_mask = self.make_stroke_mask(width, height, strokes)
        if self.erase_mask.getbbox():
            if abs(scale_factor - 1.0) < 0.0001:
                erase_mask = self.erase_mask
            else:
                erase_mask = self.erase_mask.resize((width, height), Image.Resampling.BILINEAR)
            erase_blur = erase_mask.filter(ImageFilter.GaussianBlur(radius=max(0, int(self.softness_slider.value() * scale_factor))))
            stroke_mask = Image.composite(Image.new("L", stroke_mask.size, 0), stroke_mask, erase_blur)
        alpha_channel = layer.getchannel("A")
        alpha_channel = Image.composite(alpha_channel, Image.new("L", alpha_channel.size, 0), stroke_mask)
        layer.putalpha(alpha_channel)
        return layer

    def make_full_composited_image(self):
        watermark = self.make_watermark_layer_for_strokes(self.full_w, self.full_h, self.strokes, 1.0)
        base = self.original.convert("RGBA")
        base.alpha_composite(watermark)
        return base.convert("RGB")

    def make_preview_image(self, display_w: int, display_h: int):
        display_w = max(1, int(display_w))
        display_h = max(1, int(display_h))
        scale_factor = min(display_w / self.full_w, display_h / self.full_h)
        preview_base = self.original.resize((display_w, display_h), Image.Resampling.LANCZOS).convert("RGBA")
        preview_strokes = self.scaled_strokes(scale_factor)
        preview_watermark = self.make_watermark_layer_for_strokes(display_w, display_h, preview_strokes, scale_factor)
        preview_base.alpha_composite(preview_watermark)
        return preview_base.convert("RGBA")

    def refresh_preview(self):
        self.refresh_pending = False
        self.update_labels()
        canvas_w = max(1, self.canvas.width())
        canvas_h = max(1, self.canvas.height())
        self.scale = max(0.0001, min(canvas_w / self.full_w, canvas_h / self.full_h))
        self.display_w = max(1, int(self.full_w * self.scale))
        self.display_h = max(1, int(self.full_h * self.scale))
        self.offset_x = (canvas_w - self.display_w) // 2
        self.offset_y = (canvas_h - self.display_h) // 2
        preview_image = self.make_preview_image(self.display_w, self.display_h)
        self.preview_pixmap = pil_to_qpixmap(preview_image)
        self.canvas.update()

    def stroke_hit_distance(self, stroke: Dict[str, Any], img_x: int, img_y: int) -> Optional[float]:
        points = stroke.get("points", [])
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
        if not stroke.get("visible", True):
            return False
        min_d = self.stroke_hit_distance(stroke, img_x, img_y)
        if min_d is None:
            return False
        tol = max(14.0, float(stroke.get("brush_size", 30)) * 0.60) + extra_tol
        return min_d <= tol

    def find_stroke_at_point(self, img_x: int, img_y: int, extra_tol: float = 24.0) -> int:
        best_idx = -1
        best_dist = None
        for idx, stroke in enumerate(self.strokes):
            if not stroke.get("visible", True):
                continue
            min_d = self.stroke_hit_distance(stroke, img_x, img_y)
            if min_d is None:
                continue
            tol = max(14.0, float(stroke.get("brush_size", 30)) * 0.60) + extra_tol
            if min_d <= tol and (best_dist is None or min_d < best_dist):
                best_dist = min_d
                best_idx = idx
        return best_idx

    def is_click_release(self, canvas_x: float, canvas_y: float) -> bool:
        if self.left_press_img_xy is None or not self.inside_image_canvas(canvas_x, canvas_y):
            return True
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        click_threshold = max(10, int(self.current_brush_size * 0.12))
        return dist(self.left_press_img_xy, (img_x, img_y)) < click_threshold

    def add_erase_to_mask(self, img_x, img_y):
        size = int(self.brush_size_slider.value())
        r = size // 2
        self.erase_draw.ellipse((img_x - r, img_y - r, img_x + r, img_y + r), fill=255)

    def add_erase_line_to_mask(self, x0, y0, x1, y1):
        size = int(self.brush_size_slider.value())
        self.erase_draw.line((x0, y0, x1, y1), fill=255, width=size)
        self.add_erase_to_mask(x1, y1)

    def start_left_interaction(self, canvas_x: float, canvas_y: float):
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        self.left_press_img_xy = (img_x, img_y)
        self.left_press_candidate = self.find_stroke_at_point(img_x, img_y)
        self.left_press_on_selected = (
            self.selected_stroke_index >= 0
            and self.point_near_stroke(self.selected_stroke_index, img_x, img_y, extra_tol=24.0)
        )
        self.current_brush_size = int(self.brush_size_slider.value())
        self.current_points = []
        self.last_img_xy = None
        self.is_painting = False

    def continue_left_interaction(self, canvas_x: float, canvas_y: float):
        if self.left_press_img_xy is None or not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if not self.is_painting:
            move_dist = dist(self.left_press_img_xy, (img_x, img_y))
            if move_dist < max(6, int(self.current_brush_size * 0.08)):
                return
            self.is_painting = True
            if self.selected_stroke_index >= 0:
                self.select_stroke_by_index(-1, refresh_preview=False)
            self.current_points = [self.left_press_img_xy, (img_x, img_y)]
            self.last_img_xy = (img_x, img_y)
        min_capture = max(2, int(self.current_brush_size * 0.012))
        if self.last_img_xy is None or dist(self.last_img_xy, (img_x, img_y)) >= min_capture:
            self.current_points.append((img_x, img_y))
            self.last_img_xy = (img_x, img_y)
        self.canvas.update()

    def finish_left_interaction(self, canvas_x: float, canvas_y: float):
        click = self.is_click_release(canvas_x, canvas_y)

        if click and self.left_press_on_selected:
            self.select_stroke_by_index(-1, refresh_preview=False)
            self.clear_left_interaction()
            self.schedule_preview()
            return

        if self.is_painting and self.current_points:
            cleaned = simplify_points(self.current_points, min_dist=max(2.0, self.current_brush_size * 0.010))
            cleaned = chaikin_smooth(cleaned, iterations=3)
            if len(cleaned) >= 2:
                self.strokes.append({
                    "name": f"Stroke {self.stroke_counter}",
                    "visible": True,
                    "points": cleaned,
                    "brush_size": self.current_brush_size,
                    "opacity": int(self.opacity_slider.value()),
                })
                self.stroke_counter += 1
                self.refresh_stroke_list()
                self.select_stroke_by_index(len(self.strokes) - 1, refresh_preview=False)
        elif self.left_press_candidate >= 0:
            self.select_stroke_by_index(self.left_press_candidate, refresh_preview=False)
        self.clear_left_interaction()
        self.schedule_preview()

    def start_erase_interaction(self, canvas_x: float, canvas_y: float):
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        self.add_erase_to_mask(img_x, img_y)
        self.last_img_xy = (img_x, img_y)
        self.is_erasing = True
        self.schedule_preview(20)

    def continue_erase_interaction(self, canvas_x: float, canvas_y: float):
        if not self.is_erasing or not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if self.last_img_xy is None:
            self.last_img_xy = (img_x, img_y)
        self.add_erase_line_to_mask(self.last_img_xy[0], self.last_img_xy[1], img_x, img_y)
        self.last_img_xy = (img_x, img_y)
        self.schedule_preview(20)

    def finish_erase_interaction(self, canvas_x: float, canvas_y: float):
        self.last_img_xy = None
        self.is_erasing = False
        self.schedule_preview(20)

    def delete_selected_stroke(self):
        if 0 <= self.selected_stroke_index < len(self.strokes):
            del self.strokes[self.selected_stroke_index]
            if self.strokes:
                self.selected_stroke_index = min(self.selected_stroke_index, len(self.strokes) - 1)
                self.select_stroke_by_index(self.selected_stroke_index, refresh_preview=False)
            else:
                self.select_stroke_by_index(-1, refresh_preview=False)
                self.refresh_stroke_list()
            self.schedule_preview()

    def clear_all(self):
        self.strokes = []
        self.current_points = []
        self.selected_stroke_index = -1
        self.erase_mask = Image.new("L", (self.full_w, self.full_h), 0)
        self.erase_draw = ImageDraw.Draw(self.erase_mask)
        self.refresh_stroke_list()
        self.select_stroke_by_index(-1, refresh_preview=False)
        self.schedule_preview()

    def save_and_close(self):
        save_settings(self.current_settings())
        if not self.strokes:
            answer = QMessageBox.question(self, APP_NAME, "You did not paint any stroke. Save unchanged image and close?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            final = self.make_full_composited_image()
            final.save(self.image_path, quality=95, subsampling=0, optimize=True)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        if self.reveal_in_explorer_check.isChecked():
            reveal_in_explorer(self.image_path)
        self.close()

    def exit_without_saving(self):
        save_settings(self.current_settings())
        self.close()


def select_jpg_file() -> Optional[Path]:
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select JPG image",
        "",
        "JPEG images (*.jpg *.jpeg);;All files (*.*)",
    )
    if not file_path:
        return None
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        QMessageBox.critical(None, APP_NAME, "Only JPG and JPEG files are supported.")
        return None
    return path


def resolve_image_path() -> Optional[Path]:
    if len(sys.argv) >= 2:
        return Path(sys.argv[1])
    return select_jpg_file()


def main():
    app = QApplication(sys.argv)
    image_path = resolve_image_path()
    if image_path is None:
        return 0
    try:
        window = BrushWatermarkQtPolished(image_path)
        window.show()
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None, APP_NAME, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
