import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QListWidgetItem, QMainWindow, QMessageBox, QScrollArea, QSizePolicy, QWidget

from brush_watermark import __version__
from brush_watermark.config import APP_NAME, reveal_in_explorer, save_settings
from brush_watermark.geometry.points import clamp, dist
from brush_watermark.models import CanvasView, Settings
from brush_watermark.rendering.colors import build_swatch_palette
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.auto_update import can_auto_update
from brush_watermark.services.document import Document
from brush_watermark.services.export import build_watermarked_copy_path
from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.auto_updater import AutoUpdater
from brush_watermark.ui.canvas import CanvasWidget
from brush_watermark.ui.sidebar import SidebarPanel
from brush_watermark.ui.styles import app_stylesheet
from brush_watermark.ui.update_checker import UpdateChecker


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    return QPixmap.fromImage(ImageQt(image))


class MainWindow(QMainWindow):
    def __init__(self, image_path: Path, settings: Settings):
        super().__init__()
        self.doc = Document(image_path, settings)
        self.swatch_colors = build_swatch_palette(self.doc.original)
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
        self._ignore_list_selection = False
        self._update_checker: UpdateChecker | None = None
        self._auto_updater: AutoUpdater | None = None
        self._update_result: UpdateCheckResult | None = None

        self.setWindowTitle(f"{APP_NAME} - {self.doc.image_path.name}")
        self.resize(1560, 980)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(app_stylesheet())

        self._build_ui()
        self._connect_signals()
        self.update_labels()
        self.schedule_preview(1)
        QTimer.singleShot(0, self._start_update_check)

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
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sidebar_scroll.setFixedWidth(340)
        root.addWidget(self.sidebar_scroll)

        self.sidebar = SidebarPanel(self.doc.settings, self.swatch_colors, self.doc.metadata)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        self.sidebar_scroll.setWidget(self.sidebar)

    def _connect_signals(self):
        self.sidebar.document_settings_changed.connect(self.document_settings_changed)
        self.sidebar.stroke_controls_changed.connect(self.stroke_controls_changed)
        self.sidebar.layer_item_clicked.connect(self.on_layer_item_clicked)
        self.sidebar.delete_selected.connect(self.delete_selected_stroke)
        self.sidebar.delete_all.connect(self.clear_all)
        self.sidebar.save_and_close.connect(self.save_and_close)
        self.sidebar.save_copy_and_close.connect(self.save_copy_and_close)
        self.sidebar.exit_without_saving.connect(self.exit_without_saving)
        self.sidebar.preview_mode_changed.connect(self.on_preview_mode_changed)
        self.sidebar.update_now.connect(self.start_auto_update)

    def _start_update_check(self):
        self.sidebar.set_version_info(__version__)
        checker = UpdateChecker(self)
        checker.completed.connect(self._on_update_check_finished)
        self._update_checker = checker
        checker.start()

    def _on_update_check_finished(self, result):
        self._update_result = result
        self.sidebar.set_version_info(__version__, result)
        self._update_checker = None

    def start_auto_update(self):
        result = self._update_result
        if result is None or not result.update_available:
            return
        if not can_auto_update():
            QDesktopServices.openUrl(QUrl(result.release_url))
            return
        if not result.download_url:
            QDesktopServices.openUrl(QUrl(result.release_url))
            return

        answer = QMessageBox.question(
            self,
            APP_NAME,
            f"Download and install version {result.latest_version}?\n\n"
            "The app will close and restart automatically. "
            "Unsaved image changes will be lost.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._sync_document_settings_from_sidebar()
        if not self._layer_selected():
            self._sync_tool_defaults_from_sidebar()
        save_settings(self.doc.settings.to_dict())

        self.sidebar.set_update_progress(0, "Preparing update…")
        updater = AutoUpdater(result.download_url, os.getpid(), sys.argv[1:])
        updater.progress.connect(self.sidebar.set_update_progress)
        updater.failed.connect(self._on_auto_update_failed)
        self._auto_updater = updater
        updater.start()

    def _on_auto_update_failed(self, message: str):
        self._auto_updater = None
        self.sidebar.clear_update_progress()
        QMessageBox.critical(
            self,
            APP_NAME,
            f"Could not install the update.\n\n{message}",
        )

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
            brush_size=self.sidebar.brush_row.slider.value(),
            show_original=self.sidebar.show_original_preview(),
        )

    def _sync_document_settings_from_sidebar(self):
        self.doc.settings = self.sidebar.read_document_settings(self.doc.settings)

    def _sync_tool_defaults_from_sidebar(self):
        tool = self.sidebar.read_tool_defaults()
        self.doc.settings.opacity = tool["opacity"]
        self.doc.settings.brush_size = tool["brush_size"]
        self.doc.settings.angle_offset = tool["angle_offset"]
        self.doc.settings.text_color = tool["text_color"]
        self.doc.settings.blend_mode = tool["blend_mode"]
        self.doc.settings.mask_softness = tool["mask_softness"]
        self.doc.settings.repeat_text = tool["repeat_text"]
        self.doc.settings.repeat_spacing = tool["repeat_spacing"]

    def _layer_selected(self) -> bool:
        return 0 <= self.doc.selected_stroke_index < len(self.doc.strokes)

    def update_labels(self):
        sb = self.sidebar
        controls = sb.read_stroke_controls()
        brush = controls["brush_size"]
        sb.set_slider_value(sb.opacity_row, f"{controls['opacity']}%")
        sb.set_slider_value(sb.brush_row, f"{brush} px")
        sb.font_size_value_label.setText(f"Font {font_size_from_brush(brush)} px (follows brush)")
        sb.set_slider_value(sb.softness_row, f"{controls['mask_softness']} px")
        sb.delete_selected_btn.setEnabled(self._layer_selected())

    def document_settings_changed(self):
        self._sync_document_settings_from_sidebar()
        if not self._layer_selected():
            self._sync_tool_defaults_from_sidebar()
        save_settings(self.doc.settings.to_dict())
        self.update_labels()
        self.canvas.update()
        self.schedule_preview()

    def stroke_controls_changed(self):
        if self._layer_selected():
            self.doc.update_selected_stroke(**self.sidebar.read_stroke_controls())
            self.refresh_stroke_list()
        else:
            self._sync_tool_defaults_from_sidebar()
            save_settings(self.doc.settings.to_dict())
        self.update_labels()
        self.schedule_preview()

    def sync_list_selection(self):
        self._ignore_list_selection = True
        self.sidebar.stroke_list.blockSignals(True)
        if self._layer_selected():
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

    def on_layer_item_clicked(self, row: int):
        if self._ignore_list_selection or row < 0:
            return
        if row == self.doc.selected_stroke_index:
            self.select_stroke_by_index(-1)
        else:
            self.select_stroke_by_index(row)

    def clear_left_interaction(self):
        self.doc.current_points = []
        self.last_img_xy = None
        self.is_painting = False
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False

    def handle_wheel(self, step: int, alt: bool):
        sb = self.sidebar
        if alt:
            value = clamp(sb.brush_row.slider.value() + step * 12, 5, 600)
            sb.brush_row.slider.setValue(int(value))
        else:
            value = clamp(sb.opacity_row.slider.value() + step * 2, 1, 100)
            sb.opacity_row.slider.setValue(int(value))

    def select_stroke_by_index(self, index: int, refresh_preview: bool = True):
        self.doc.select_stroke(index)
        self.sync_list_selection()
        if self._layer_selected():
            self.sidebar.load_stroke_controls(self.doc.strokes[index])
        else:
            self.sidebar.load_tool_defaults(self.doc.settings)
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

    def on_preview_mode_changed(self):
        self.canvas.update()
        self.schedule_preview(1)

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
        include_metadata = (
            not self.sidebar.show_original_preview()
            and self.doc.settings.add_visible_metadata
        )
        content_w, content_h = self.doc.preview_content_size(include_metadata=include_metadata)
        self.scale = max(0.0001, min(canvas_w / content_w, canvas_h / content_h))
        self.display_w = max(1, int(self.doc.full_w * self.scale))
        self.display_h = max(1, int(self.doc.full_h * self.scale))
        if self.sidebar.show_original_preview():
            preview_image = self.doc.make_original_preview_image(self.display_w, self.display_h)
        else:
            preview_image = self.doc.make_preview_image(self.display_w, self.display_h, self.scale)
        pixmap_w, pixmap_h = preview_image.size
        self.offset_x = (canvas_w - pixmap_w) // 2
        self.offset_y = (canvas_h - pixmap_h) // 2
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
        self.doc.current_brush_size = self.sidebar.brush_row.slider.value()
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
                controls = self.sidebar.read_stroke_controls()
                self.doc.add_stroke(
                    cleaned,
                    self.doc.current_brush_size,
                    controls["opacity"],
                    controls["blend_mode"],
                    controls["text_color"],
                    controls["angle_offset"],
                    controls["mask_softness"],
                    controls["repeat_text"],
                    controls["repeat_spacing"],
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
        self.refresh_stroke_list()
        if self.doc.strokes:
            self.select_stroke_by_index(self.doc.selected_stroke_index, refresh_preview=False)
        else:
            self.select_stroke_by_index(-1, refresh_preview=False)
        self.schedule_preview()

    def clear_all(self):
        self.doc.clear_all()
        self.refresh_stroke_list()
        self.select_stroke_by_index(-1, refresh_preview=False)
        self.schedule_preview()

    def _sync_before_save(self):
        self._sync_document_settings_from_sidebar()
        if not self._layer_selected():
            self._sync_tool_defaults_from_sidebar()
        save_settings(self.doc.settings.to_dict())

    def _confirm_save_without_strokes(self) -> bool:
        if self.doc.strokes:
            return True
        answer = QMessageBox.question(
            self,
            APP_NAME,
            "You did not paint any stroke. Save unchanged image and close?",
        )
        return answer == QMessageBox.StandardButton.Yes

    def _write_final_image(self, export_path: Path) -> bool:
        try:
            final = self.doc.make_full_composited_image()
            final.save(export_path, quality=95, subsampling=0, optimize=True)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        if self.sidebar.reveal_in_explorer_check.isChecked():
            reveal_in_explorer(export_path)
        return True

    def save_and_close(self):
        self._sync_before_save()
        if not self._confirm_save_without_strokes():
            return
        if self._write_final_image(self.doc.image_path):
            self.close()

    def save_copy_and_close(self):
        self._sync_before_save()
        if not self._confirm_save_without_strokes():
            return
        export_path = build_watermarked_copy_path(self.doc.image_path)
        if self._write_final_image(export_path):
            self.close()

    def exit_without_saving(self):
        self._sync_document_settings_from_sidebar()
        if not self._layer_selected():
            self._sync_tool_defaults_from_sidebar()
        save_settings(self.doc.settings.to_dict())
        self.close()
