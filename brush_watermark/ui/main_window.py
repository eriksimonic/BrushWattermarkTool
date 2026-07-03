from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QListWidgetItem, QMainWindow, QMessageBox, QScrollArea, QWidget

from brush_watermark.config import APP_NAME, reveal_in_explorer, save_settings
from brush_watermark.geometry.points import clamp, dist
from brush_watermark.models import CanvasView, Settings
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.document import Document
from brush_watermark.ui.canvas import CanvasWidget
from brush_watermark.ui.sidebar import SidebarPanel
from brush_watermark.ui.styles import app_stylesheet


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    return QPixmap.fromImage(ImageQt(image))


class MainWindow(QMainWindow):
    def __init__(self, image_path: Path, settings: Settings):
        super().__init__()
        self.doc = Document(image_path, settings)
        self.last_pointer: Optional[tuple[float, float]] = None

        self.preview_pixmap: Optional[QPixmap] = None
        self.scale = 1.0
        self.display_w = 1
        self.display_h = 1
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.refresh_pending = False

        self.is_painting = False
        self.is_erasing = False
        self.last_img_xy = None
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False
        self._list_toggle_row = -1
        self._ignore_list_selection = False

        self.setWindowTitle(f"{APP_NAME} - {self.doc.image_path.name}")
        self.resize(1560, 980)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(app_stylesheet())

        self._build_ui()
        self._connect_signals()
        self.update_labels()
        self.schedule_preview(1)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.canvas = CanvasWidget(
            get_view=self.get_canvas_view,
            image_to_canvas=self.image_to_canvas_xy,
            inside_image=self.inside_image_canvas,
            on_left_press=self.start_left_interaction,
            on_left_move=self.continue_left_interaction,
            on_left_release=self.finish_left_interaction,
            on_right_press=self.start_erase_interaction,
            on_right_move=self.continue_erase_interaction,
            on_right_release=self.finish_erase_interaction,
            on_wheel=self.handle_wheel,
            on_pointer_move=self._on_pointer_move,
            on_pointer_leave=self._on_pointer_leave,
            text_span_info=self.doc.text_span_info,
        )
        root.addWidget(self.canvas, 1)

        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFixedWidth(320)
        root.addWidget(self.sidebar_scroll)

        self.sidebar = SidebarPanel(self.doc.settings)
        self.sidebar_scroll.setWidget(self.sidebar)

    def _connect_signals(self):
        self.sidebar.settings_changed.connect(self.global_controls_changed)
        self.sidebar.layer_selected.connect(self.on_layer_selected)
        self.sidebar.layer_item_pressed.connect(self.on_layer_item_pressed)
        self.sidebar.layer_item_clicked.connect(self.on_layer_item_clicked)
        self.sidebar.delete_selected.connect(self.delete_selected_stroke)
        self.sidebar.delete_all.connect(self.clear_all)
        self.sidebar.selected_stroke_changed.connect(self.selected_stroke_controls_changed)
        self.sidebar.save_and_close.connect(self.save_and_close)
        self.sidebar.exit_without_saving.connect(self.exit_without_saving)

    def _on_pointer_move(self, x: float, y: float):
        self.last_pointer = (x, y)

    def _on_pointer_leave(self):
        self.last_pointer = None

    def get_canvas_view(self) -> CanvasView:
        return CanvasView(
            strokes=self.doc.strokes,
            selected_stroke_index=self.doc.selected_stroke_index,
            current_points=self.doc.current_points,
            current_brush_size=self.doc.current_brush_size,
            scale=self.scale,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            last_pointer=self.last_pointer,
            brush_size=self.sidebar.brush_size_slider.value(),
        )

    def _sync_settings_from_sidebar(self):
        self.doc.settings = self.sidebar.read_settings()

    def update_labels(self):
        self._sync_settings_from_sidebar()
        brush = self.doc.settings.brush_size
        font = font_size_from_brush(brush)
        sb = self.sidebar
        sb.set_field_label_value(sb.opacity_value_label, f"{self.doc.settings.opacity}%")
        sb.set_field_label_value(sb.brush_value_label, f"{brush} px")
        sb.font_size_value_label.setText(f"Font {font} px (follows brush)")
        sb.set_field_label_value(sb.angle_value_label, f"{self.doc.settings.angle_offset}°")
        sb.set_field_label_value(sb.softness_value_label, f"{self.doc.settings.mask_softness} px")

        enabled = 0 <= self.doc.selected_stroke_index < len(self.doc.strokes)
        sb.sel_brush_slider.setEnabled(enabled)
        sb.sel_opacity_slider.setEnabled(enabled)
        sb.delete_selected_btn.setEnabled(enabled)

        if enabled:
            stroke = self.doc.strokes[self.doc.selected_stroke_index]
            sbrush = int(sb.sel_brush_slider.value())
            visibility_text = "visible" if stroke.visible else "hidden"
            sb.selected_info_label.setText(f"{stroke.name} · {visibility_text}")
            sb.set_field_label_value(sb.sel_brush_value_label, f"{sbrush} px")
            sb.sel_font_value_label.setText(f"Font {font_size_from_brush(sbrush)} px")
            sb.set_field_label_value(sb.sel_opacity_value_label, f"{int(sb.sel_opacity_slider.value())}%")
        else:
            sb.selected_info_label.setText("No stroke selected")
            sb.set_field_label_value(sb.sel_brush_value_label, "—")
            sb.sel_font_value_label.setText("")
            sb.set_field_label_value(sb.sel_opacity_value_label, "—")

    def global_controls_changed(self):
        self._sync_settings_from_sidebar()
        save_settings(self.doc.settings.to_dict())
        self.update_labels()
        self.canvas.update()
        self.schedule_preview()

    def selected_stroke_controls_changed(self):
        if 0 <= self.doc.selected_stroke_index < len(self.doc.strokes):
            self.doc.update_selected_stroke(
                int(self.sidebar.sel_brush_slider.value()),
                int(self.sidebar.sel_opacity_slider.value()),
            )
            self.refresh_stroke_list()
            self.update_labels()
            self.schedule_preview()

    def sync_list_selection(self):
        self._ignore_list_selection = True
        self.sidebar.stroke_list.blockSignals(True)
        if 0 <= self.doc.selected_stroke_index < len(self.doc.strokes):
            self.sidebar.stroke_list.setCurrentRow(self.doc.selected_stroke_index)
        else:
            self.sidebar.stroke_list.clearSelection()
            self.sidebar.stroke_list.setCurrentRow(-1)
        self.sidebar.stroke_list.blockSignals(False)
        self._ignore_list_selection = False

    def refresh_stroke_list(self):
        self.sidebar.stroke_list.blockSignals(True)
        self.sidebar.stroke_list.clear()
        for idx, stroke in enumerate(self.doc.strokes):
            item = QListWidgetItem(self.doc.stroke_list_text(idx, stroke))
            self.sidebar.stroke_list.addItem(item)
        self.sidebar.stroke_list.blockSignals(False)
        self.sync_list_selection()

    def on_layer_selected(self, index: int):
        if self._ignore_list_selection:
            return
        if index < 0:
            if self.doc.selected_stroke_index >= 0:
                self.select_stroke_by_index(-1)
            return
        if index == self.doc.selected_stroke_index:
            return
        self.select_stroke_by_index(index)

    def on_layer_item_pressed(self, row: int):
        if row < 0:
            return
        if row == self.doc.selected_stroke_index:
            self._list_toggle_row = row
            return
        self._list_toggle_row = -1
        self.select_stroke_by_index(row)

    def on_layer_item_clicked(self, row: int):
        if self._ignore_list_selection:
            return
        if row >= 0 and row == self._list_toggle_row and row == self.doc.selected_stroke_index:
            self._list_toggle_row = -1
            self.select_stroke_by_index(-1)
            return
        self._list_toggle_row = -1

    def clear_left_interaction(self):
        self.doc.current_points = []
        self.last_img_xy = None
        self.is_painting = False
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False

    def handle_wheel(self, step: int, alt: bool):
        if 0 <= self.doc.selected_stroke_index < len(self.doc.strokes):
            if alt:
                value = clamp(self.sidebar.sel_brush_slider.value() + step * 12, 5, 600)
                self.sidebar.sel_brush_slider.setValue(int(value))
            else:
                value = clamp(self.sidebar.sel_opacity_slider.value() + step * 2, 1, 100)
                self.sidebar.sel_opacity_slider.setValue(int(value))
        else:
            if alt:
                value = clamp(self.sidebar.brush_size_slider.value() + step * 12, 5, 600)
                self.sidebar.brush_size_slider.setValue(int(value))
            else:
                value = clamp(self.sidebar.opacity_slider.value() + step * 2, 1, 100)
                self.sidebar.opacity_slider.setValue(int(value))

    def select_stroke_by_index(self, index: int, refresh_preview: bool = True):
        self.doc.select_stroke(index)
        self.sync_list_selection()
        if 0 <= index < len(self.doc.strokes):
            stroke = self.doc.strokes[index]
            sb = self.sidebar
            sb.sel_brush_slider.blockSignals(True)
            sb.sel_opacity_slider.blockSignals(True)
            sb.sel_brush_slider.setValue(stroke.brush_size)
            sb.sel_opacity_slider.setValue(stroke.opacity)
            sb.sel_brush_slider.blockSignals(False)
            sb.sel_opacity_slider.blockSignals(False)
        self.update_labels()
        if refresh_preview:
            self.schedule_preview()

    def canvas_to_image_xy(self, canvas_x: float, canvas_y: float):
        return self.doc.canvas_to_image_xy(canvas_x, canvas_y, self.scale, self.offset_x, self.offset_y)

    def image_to_canvas_xy(self, x: float, y: float):
        return self.doc.image_to_canvas_xy(x, y, self.scale, self.offset_x, self.offset_y)

    def inside_image_canvas(self, canvas_x: float, canvas_y: float) -> bool:
        return self.doc.inside_image_canvas(
            canvas_x, canvas_y, self.display_w, self.display_h, self.offset_x, self.offset_y
        )

    def schedule_preview(self, delay_ms: int = 50):
        self.update_labels()
        save_settings(self.doc.settings.to_dict())
        if self.refresh_pending:
            return
        self.refresh_pending = True
        QTimer.singleShot(delay_ms, self.refresh_preview)

    def refresh_preview(self):
        self.refresh_pending = False
        self.update_labels()
        canvas_w = max(1, self.canvas.width())
        canvas_h = max(1, self.canvas.height())
        self.scale = max(0.0001, min(canvas_w / self.doc.full_w, canvas_h / self.doc.full_h))
        self.display_w = max(1, int(self.doc.full_w * self.scale))
        self.display_h = max(1, int(self.doc.full_h * self.scale))
        self.offset_x = (canvas_w - self.display_w) // 2
        self.offset_y = (canvas_h - self.display_h) // 2
        preview_image = self.doc.make_preview_image(self.display_w, self.display_h, self.scale)
        self.preview_pixmap = pil_to_qpixmap(preview_image)
        self.canvas.preview_pixmap = self.preview_pixmap
        self.canvas.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_preview(1)

    def start_left_interaction(self, canvas_x: float, canvas_y: float):
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        self.left_press_img_xy = (img_x, img_y)
        self.left_press_candidate = self.doc.find_stroke_at_point(img_x, img_y)
        self.left_press_on_selected = (
            self.doc.selected_stroke_index >= 0
            and self.doc.point_near_stroke(self.doc.selected_stroke_index, img_x, img_y, extra_tol=24.0)
        )
        self.doc.current_brush_size = self.doc.settings.brush_size
        self.doc.current_points = []
        self.last_img_xy = None
        self.is_painting = False

    def continue_left_interaction(self, canvas_x: float, canvas_y: float):
        if self.left_press_img_xy is None or not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if not self.is_painting:
            move_dist = dist(self.left_press_img_xy, (img_x, img_y))
            if move_dist < max(6, int(self.doc.current_brush_size * 0.08)):
                return
            self.is_painting = True
            if self.doc.selected_stroke_index >= 0:
                self.select_stroke_by_index(-1, refresh_preview=False)
            self.doc.current_points = [self.left_press_img_xy, (img_x, img_y)]
            self.last_img_xy = (img_x, img_y)
        min_capture = max(2, int(self.doc.current_brush_size * 0.012))
        if self.last_img_xy is None or dist(self.last_img_xy, (img_x, img_y)) >= min_capture:
            self.doc.current_points.append((img_x, img_y))
            self.last_img_xy = (img_x, img_y)

    def finish_left_interaction(self, canvas_x: float, canvas_y: float):
        release_xy = self.canvas_to_image_xy(canvas_x, canvas_y) if self.inside_image_canvas(canvas_x, canvas_y) else None
        click = self.doc.is_click_release(self.left_press_img_xy, release_xy, self.doc.current_brush_size) if release_xy else True

        if click and self.left_press_on_selected:
            self.select_stroke_by_index(-1, refresh_preview=False)
            self.clear_left_interaction()
            self.schedule_preview()
            return

        if self.is_painting and self.doc.current_points:
            cleaned = self.doc.finalize_stroke_points(self.doc.current_points, self.doc.current_brush_size)
            if len(cleaned) >= 2:
                self.doc.add_stroke(
                    cleaned,
                    self.doc.current_brush_size,
                    self.doc.settings.opacity,
                )
                self.refresh_stroke_list()
                self.select_stroke_by_index(len(self.doc.strokes) - 1, refresh_preview=False)
        elif self.left_press_candidate >= 0:
            self.select_stroke_by_index(self.left_press_candidate, refresh_preview=False)
        self.clear_left_interaction()
        self.schedule_preview()

    def start_erase_interaction(self, canvas_x: float, canvas_y: float):
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        self.doc.add_erase_to_mask(img_x, img_y)
        self.last_img_xy = (img_x, img_y)
        self.is_erasing = True
        self.schedule_preview(20)

    def continue_erase_interaction(self, canvas_x: float, canvas_y: float):
        if not self.is_erasing or not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if self.last_img_xy is None:
            self.last_img_xy = (img_x, img_y)
        self.doc.add_erase_line_to_mask(self.last_img_xy[0], self.last_img_xy[1], img_x, img_y)
        self.last_img_xy = (img_x, img_y)
        self.schedule_preview(20)

    def finish_erase_interaction(self, canvas_x: float, canvas_y: float):
        self.last_img_xy = None
        self.is_erasing = False
        self.schedule_preview(20)

    def delete_selected_stroke(self):
        self.doc.delete_selected_stroke()
        if self.doc.strokes:
            self.select_stroke_by_index(self.doc.selected_stroke_index, refresh_preview=False)
        else:
            self.select_stroke_by_index(-1, refresh_preview=False)
            self.refresh_stroke_list()
        self.schedule_preview()

    def clear_all(self):
        self.doc.clear_all()
        self.refresh_stroke_list()
        self.select_stroke_by_index(-1, refresh_preview=False)
        self.schedule_preview()

    def save_and_close(self):
        self._sync_settings_from_sidebar()
        save_settings(self.doc.settings.to_dict())
        if not self.doc.strokes:
            answer = QMessageBox.question(
                self, APP_NAME, "You did not paint any stroke. Save unchanged image and close?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            final = self.doc.make_full_composited_image()
            final.save(self.doc.image_path, quality=95, subsampling=0, optimize=True)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        if self.sidebar.reveal_in_explorer_check.isChecked():
            reveal_in_explorer(self.doc.image_path)
        self.close()

    def exit_without_saving(self):
        self._sync_settings_from_sidebar()
        save_settings(self.doc.settings.to_dict())
        self.close()
