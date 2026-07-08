import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QListWidgetItem, QMainWindow, QMessageBox, QScrollArea, QSizePolicy, QWidget

from brush_watermark import __version__
from brush_watermark.config import APP_NAME, reveal_in_explorer, save_settings
from brush_watermark.geometry.curve import find_curve_segment_for_insert
from brush_watermark.geometry.points import clamp, dist, find_anchor_index
from brush_watermark.models import CanvasView, Settings, ToolMode
from brush_watermark.rendering.colors import build_swatch_palette
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.auto_update import can_auto_update
from brush_watermark.services.document import Document
from brush_watermark.services.explorer_context import MENU_TEXT, install_context_menu, uninstall_context_menu
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

        self.active_tool = ToolMode.BRUSH
        self.is_painting = False
        self.is_erasing = False
        self.last_img_xy = None
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False
        self.line_start_xy: Optional[tuple] = None
        self.snap_endpoint: Optional[tuple] = None   # (stroke_idx, img_pt)
        self._snap_activated: bool = False
        self._line_stopped: bool = False
        self.selected_anchor_index: int = -1
        self.anchor_drag_active: bool = False
        self._ignore_list_selection = False
        self._update_checker: UpdateChecker | None = None
        self._auto_updater: AutoUpdater | None = None
        self._update_result: UpdateCheckResult | None = None

        self.setWindowTitle(f"{APP_NAME} - {self.doc.image_path.name}")
        self.resize(1560, 980)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(app_stylesheet())

        self._build_menu_bar()
        self._build_ui()
        self._connect_signals()
        self.update_labels()
        self.schedule_preview(1)
        QTimer.singleShot(0, self._start_update_check)

    def _build_menu_bar(self):
        file_menu = self.menuBar().addMenu("&File")

        save_action = QAction("Save && Close", self)
        save_action.triggered.connect(lambda _checked=False: self.save_and_close())
        file_menu.addAction(save_action)

        save_copy_action = QAction("Save Copy && Close", self)
        save_copy_action.triggered.connect(lambda _checked=False: self.save_copy_and_close())
        file_menu.addAction(save_copy_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit Without Saving", self)
        exit_action.triggered.connect(lambda _checked=False: self.exit_without_saving())
        file_menu.addAction(exit_action)

        tools_menu = self.menuBar().addMenu("&Tools")

        install_explorer_action = QAction(f'Install Explorer "{MENU_TEXT}"', self)
        install_explorer_action.setEnabled(sys.platform == "win32")
        install_explorer_action.triggered.connect(lambda _checked=False: self.install_explorer_context_menu())
        tools_menu.addAction(install_explorer_action)

        uninstall_explorer_action = QAction(f'Remove Explorer "{MENU_TEXT}"', self)
        uninstall_explorer_action.setEnabled(sys.platform == "win32")
        uninstall_explorer_action.triggered.connect(lambda _checked=False: self.uninstall_explorer_context_menu())
        tools_menu.addAction(uninstall_explorer_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda _checked=False: self.show_about())
        help_menu.addAction(about_action)

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
            on_right_press=self.start_right_interaction,
            on_right_move=self.continue_right_interaction,
            on_right_release=self.finish_right_interaction,
            on_wheel=self.handle_wheel,
            on_pointer_move=self._on_pointer_move,
            on_pointer_leave=self._on_pointer_leave,
            text_span_info=self.doc.text_span_info,
            on_double_click=self.handle_double_click,
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
        self.sidebar.tool_changed.connect(self.set_active_tool)

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

    def install_explorer_context_menu(self):
        try:
            install_context_menu()
        except (OSError, RuntimeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not install Explorer menu.\n\n{exc}")
            return
        QMessageBox.information(
            self,
            APP_NAME,
            f'Explorer will now show "{MENU_TEXT}" when you right-click JPG and JPEG files.',
        )

    def uninstall_explorer_context_menu(self):
        try:
            uninstall_context_menu()
        except (OSError, RuntimeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not remove Explorer menu.\n\n{exc}")
            return
        QMessageBox.information(self, APP_NAME, f'Removed the Explorer "{MENU_TEXT}" menu.')

    def show_about(self):
        QMessageBox.about(
            self,
            APP_NAME,
            f"{APP_NAME}\nVersion {__version__}\n\n"
            f'Use Tools > Install Explorer "{MENU_TEXT}" to add a JPG right-click shortcut.',
        )

    def _on_pointer_move(self, x: float, y: float):
        self.last_pointer = (x, y)
        self.snap_endpoint = self._find_snap_endpoint(x, y)

    def _on_pointer_leave(self):
        self.last_pointer = None
        self.snap_endpoint = None

    def _find_snap_endpoint(self, canvas_x: float, canvas_y: float) -> Optional[tuple]:
        """Return (stroke_idx, img_pt) if the cursor is near any stroke endpoint in Brush mode."""
        if self.active_tool != ToolMode.BRUSH:
            return None
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return None
        tol_img = 16.0 / max(self.scale, 0.0001)
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        best = None
        best_d = None
        for i, stroke in enumerate(self.doc.strokes):
            if not stroke.points:
                continue
            for pt in (stroke.points[0], stroke.points[-1]):
                d = dist((img_x, img_y), pt)
                if d <= tol_img and (best_d is None or d < best_d):
                    best_d = d
                    best = (i, pt)
        return best

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
            active_tool=self.active_tool,
            line_start_xy=self.line_start_xy,
            selected_anchor_index=self.selected_anchor_index,
            snap_endpoint_xy=self.snap_endpoint[1] if self.snap_endpoint else None,
            is_drawing=self.is_painting,
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
        # Fit the image to the canvas, but never upscale past 1:1 (100%). A small
        # image (e.g. 100px) stays at its native pixel size instead of being blown
        # up to the monitor resolution, which avoids a blurry/pixelated preview.
        fit_scale = min(canvas_w / content_w, canvas_h / content_h)
        self.scale = max(0.0001, min(fit_scale, 1.0))
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

    # --- Tool switching ---

    def set_active_tool(self, tool) -> None:
        self.active_tool = ToolMode(tool) if not isinstance(tool, ToolMode) else tool
        self.snap_endpoint = None
        self._line_stopped = False
        self.is_erasing = False
        if self.active_tool != ToolMode.BRUSH:
            self.line_start_xy = None
        if self.active_tool != ToolMode.PATH:
            self.selected_anchor_index = -1
            self.anchor_drag_active = False
        self.sidebar.set_active_tool(self.active_tool)
        self.canvas.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_V:
            self.set_active_tool(ToolMode.POINTER)
        elif key == Qt.Key.Key_B:
            self.set_active_tool(ToolMode.BRUSH)
        elif key == Qt.Key.Key_A:
            self.set_active_tool(ToolMode.PATH)
        elif key == Qt.Key.Key_E:
            self.set_active_tool(ToolMode.ERASER)
        elif key == Qt.Key.Key_Escape:
            if self.active_tool == ToolMode.BRUSH and self.line_start_xy is not None:
                self.line_start_xy = None
                self.canvas.update()
            elif self.active_tool == ToolMode.PATH and self.selected_anchor_index >= 0:
                self.selected_anchor_index = -1
                self.canvas.update()
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.active_tool == ToolMode.PATH and self.selected_anchor_index >= 0:
                self.doc.delete_anchor(self.doc.selected_stroke_index, self.selected_anchor_index)
                self.selected_anchor_index = -1
                self.refresh_stroke_list()
                self.schedule_preview()
        else:
            super().keyPressEvent(event)

    # --- Left-button dispatch ---

    def start_left_interaction(self, canvas_x: float, canvas_y: float):
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if self.active_tool == ToolMode.POINTER:
            self._pointer_press(img_x, img_y)
        elif self.active_tool == ToolMode.BRUSH:
            self._brush_press(img_x, img_y)
        elif self.active_tool == ToolMode.ERASER:
            self._erase_press(img_x, img_y)
        else:
            self._path_press(img_x, img_y)

    def continue_left_interaction(self, canvas_x: float, canvas_y: float):
        if self.active_tool == ToolMode.POINTER:
            return
        if not self.inside_image_canvas(canvas_x, canvas_y):
            return
        if self.active_tool == ToolMode.BRUSH:
            self._brush_move(canvas_x, canvas_y)
        elif self.active_tool == ToolMode.ERASER:
            self._erase_move(canvas_x, canvas_y)
        else:
            self._path_move(canvas_x, canvas_y)

    def finish_left_interaction(self, canvas_x: float, canvas_y: float):
        if self.active_tool == ToolMode.POINTER:
            self._pointer_release(canvas_x, canvas_y)
        elif self.active_tool == ToolMode.BRUSH:
            self._brush_release(canvas_x, canvas_y)
        elif self.active_tool == ToolMode.ERASER:
            self._erase_release(canvas_x, canvas_y)
        else:
            self._path_release(canvas_x, canvas_y)

    # --- Right-button dispatch (stop drawing in Brush mode) ---

    def start_right_interaction(self, canvas_x: float, canvas_y: float):
        if self.active_tool == ToolMode.BRUSH:
            self._brush_stop()

    def continue_right_interaction(self, canvas_x: float, canvas_y: float):
        return

    def finish_right_interaction(self, canvas_x: float, canvas_y: float):
        return

    def handle_double_click(self, canvas_x: float, canvas_y: float):
        """Insert an anchor at the clicked segment (Path tool only)."""
        if self.active_tool != ToolMode.PATH:
            return
        if not self._layer_selected() or not self.inside_image_canvas(canvas_x, canvas_y):
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        stroke = self.doc.strokes[self.doc.selected_stroke_index]
        tol_img = max(8.0, 15.0 / max(self.scale, 0.0001))
        seg_idx = find_curve_segment_for_insert(stroke.anchors, img_x, img_y, tol=tol_img)
        if seg_idx >= 0:
            self.doc.insert_anchor(self.doc.selected_stroke_index, seg_idx, (img_x, img_y))
            self.selected_anchor_index = seg_idx + 1
            self.refresh_stroke_list()
            self.schedule_preview()

    # --- Pointer tool ---

    def _pointer_press(self, img_x: int, img_y: int) -> None:
        self.left_press_img_xy = (img_x, img_y)
        self.left_press_candidate = self.doc.find_stroke_at_point(img_x, img_y)
        self.left_press_on_selected = (
            self.doc.selected_stroke_index >= 0
            and self.doc.point_near_stroke(self.doc.selected_stroke_index, img_x, img_y, extra_tol=24.0)
        )

    def _pointer_release(self, canvas_x: float, canvas_y: float) -> None:
        if self.left_press_on_selected:
            self.select_stroke_by_index(-1)
        elif self.left_press_candidate >= 0:
            self.select_stroke_by_index(self.left_press_candidate)
        else:
            self.select_stroke_by_index(-1)
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False

    # --- Brush tool ---

    def _brush_press(self, img_x: int, img_y: int) -> None:
        self.left_press_img_xy = (img_x, img_y)
        self.doc.current_brush_size = self.sidebar.brush_row.slider.value()
        self.doc.current_points = []
        self.last_img_xy = None
        self.is_painting = False
        self._snap_activated = False

        if self.snap_endpoint is not None:
            # Hovering over a stroke endpoint — resume drawing from there.
            stroke_idx, snap_pt = self.snap_endpoint
            if stroke_idx != self.doc.selected_stroke_index:
                self.select_stroke_by_index(stroke_idx, refresh_preview=False)
            self.line_start_xy = snap_pt
            self._snap_activated = True
            self._line_stopped = False
        elif self._line_stopped:
            # Line was stopped and user clicked outside any endpoint → new stroke.
            self.select_stroke_by_index(-1, refresh_preview=False)
            self._line_stopped = False

    def _brush_move(self, canvas_x: float, canvas_y: float) -> None:
        if self.left_press_img_xy is None:
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if not self.is_painting:
            move_dist = dist(self.left_press_img_xy, (img_x, img_y))
            if move_dist < max(6, int(self.doc.current_brush_size * 0.08)):
                return
            self.line_start_xy = None  # cancel pending line mode on drag
            self._snap_activated = False
            self._line_stopped = False
            self.is_painting = True
            self.doc.current_points = [self.left_press_img_xy, (img_x, img_y)]
            self.last_img_xy = (img_x, img_y)
        min_capture = max(2, int(self.doc.current_brush_size * 0.012))
        if self.last_img_xy is None or dist(self.last_img_xy, (img_x, img_y)) >= min_capture:
            self.doc.current_points.append((img_x, img_y))
            self.last_img_xy = (img_x, img_y)

    def _brush_release(self, canvas_x: float, canvas_y: float) -> None:
        release_xy = (
            self.canvas_to_image_xy(canvas_x, canvas_y)
            if self.inside_image_canvas(canvas_x, canvas_y)
            else None
        )
        is_click = (
            self.doc.is_click_release(self.left_press_img_xy, release_xy, self.doc.current_brush_size)
            if release_xy
            else True
        )

        snap_click = self._snap_activated and not self.is_painting
        self._snap_activated = False

        if self.is_painting and self.doc.current_points:
            cleaned = self.doc.finalize_stroke_points(self.doc.current_points, self.doc.current_brush_size)
            if len(cleaned) >= 2:
                self._commit_brush_points(cleaned)
                # Keep the chain active from the freehand end, so continuing and
                # right-click-to-stop behave the same as with click-placed lines.
                self.line_start_xy = cleaned[-1]
                self._line_stopped = False
        elif snap_click:
            # User clicked an endpoint to arm continuation — line_start_xy is already set.
            # Nothing to commit yet; the next click will draw from here.
            pass
        elif is_click and release_xy:
            if self.line_start_xy is None:
                self.line_start_xy = release_xy
            else:
                segment = [self.line_start_xy, release_xy]
                cleaned = self.doc.finalize_stroke_points(segment, self.doc.current_brush_size)
                if len(cleaned) >= 2:
                    self._commit_brush_points(cleaned)
                self.line_start_xy = release_xy  # chain next segment from here

        self.doc.current_points = []
        self.last_img_xy = None
        self.is_painting = False
        self.left_press_img_xy = None
        self.schedule_preview()

    def _commit_brush_points(self, points: list) -> None:
        if self._layer_selected():
            self.doc.append_to_stroke(self.doc.selected_stroke_index, points)
            self.refresh_stroke_list()
        else:
            controls = self.sidebar.read_stroke_controls()
            self.doc.add_stroke(
                points,
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

    # --- Path tool ---

    def _path_press(self, img_x: int, img_y: int) -> None:
        self.left_press_img_xy = (img_x, img_y)
        self.anchor_drag_active = False

        if not self._layer_selected():
            candidate = self.doc.find_stroke_at_point(img_x, img_y)
            if candidate >= 0:
                self.select_stroke_by_index(candidate, refresh_preview=False)
                self.canvas.update()
            return

        stroke = self.doc.strokes[self.doc.selected_stroke_index]
        tol_img = max(8.0, 10.0 / max(self.scale, 0.0001))
        anchor_idx = find_anchor_index(stroke.anchors, img_x, img_y, tol=tol_img)
        if anchor_idx >= 0:
            self.selected_anchor_index = anchor_idx
            self.anchor_drag_active = True
            self.last_img_xy = (img_x, img_y)
        else:
            self.selected_anchor_index = -1

    def _path_move(self, canvas_x: float, canvas_y: float) -> None:
        if not self.anchor_drag_active:
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        self.doc.move_anchor(self.doc.selected_stroke_index, self.selected_anchor_index, (img_x, img_y))
        self.last_img_xy = (img_x, img_y)
        self.canvas.update()

    def _path_release(self, canvas_x: float, canvas_y: float) -> None:
        if self.anchor_drag_active:
            self.anchor_drag_active = False
            self.refresh_stroke_list()
            self.schedule_preview()
        elif self.left_press_img_xy is not None and not self._layer_selected():
            if self.inside_image_canvas(canvas_x, canvas_y):
                img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
                candidate = self.doc.find_stroke_at_point(img_x, img_y)
                if candidate >= 0:
                    self.select_stroke_by_index(candidate)
        self.left_press_img_xy = None
        self.anchor_drag_active = False

    def _brush_stop(self) -> None:
        """Left-click in Brush mode ends the current line chain (without deselecting)."""
        self.line_start_xy = None
        self._snap_activated = False
        self._line_stopped = True   # next non-snap draw will start a new stroke
        self.canvas.update()

    # --- Eraser tool ---

    def _erase_press(self, img_x: int, img_y: int) -> None:
        self.doc.add_erase_to_mask(img_x, img_y)
        self.last_img_xy = (img_x, img_y)
        self.is_erasing = True
        self.schedule_preview(20)

    def _erase_move(self, canvas_x: float, canvas_y: float) -> None:
        if not self.is_erasing:
            return
        img_x, img_y = self.canvas_to_image_xy(canvas_x, canvas_y)
        if self.last_img_xy is None:
            self.last_img_xy = (img_x, img_y)
        self.doc.add_erase_line_to_mask(self.last_img_xy[0], self.last_img_xy[1], img_x, img_y)
        self.last_img_xy = (img_x, img_y)
        self.schedule_preview(20)

    def _erase_release(self, canvas_x: float, canvas_y: float) -> None:
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
            save_kwargs = {"quality": 95, "subsampling": 0, "optimize": True}
            if self.doc.exif_bytes:
                save_kwargs["exif"] = self.doc.exif_bytes
            final.save(export_path, **save_kwargs)
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
