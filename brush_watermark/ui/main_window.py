import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from brush_watermark import __version__
from brush_watermark.config import APP_NAME, reveal_in_explorer, save_settings
from brush_watermark.geometry.curve import find_curve_segment_for_insert
from brush_watermark.geometry.points import clamp, dist, find_anchor_index
from brush_watermark.models import CanvasView, ToolMode
from brush_watermark.rendering.blend import blend_mode_label
from brush_watermark.rendering.colors import build_swatch_palette
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.adaptive_strength import opacity_for_path
from brush_watermark.services.auto_update import can_auto_update
from brush_watermark.services.auto_watermark import add_paths_as_strokes
from brush_watermark.services.document import Document, format_load_errors, load_documents
from brush_watermark.services.explorer_context import MENU_TEXT, install_context_menu, uninstall_context_menu
from brush_watermark.services.export import build_watermarked_copy_path
from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.auto_updater import AutoUpdater
from brush_watermark.ui.auto_watermark_worker import AutoWatermarkWorker
from brush_watermark.ui.canvas import CanvasWidget
from brush_watermark.ui.canvas_overlays import CanvasArea
from brush_watermark.ui.design_tokens import TEXT
from brush_watermark.ui.filmstrip import THUMB_H, THUMB_W, FilmstripWidget
from brush_watermark.ui.icons import get_pixmap
from brush_watermark.ui.inspector import INSPECTOR_WIDTH, InspectorPanel
from brush_watermark.ui.layer_list import LayerItem
from brush_watermark.ui.status_footer import StatusFooter
from brush_watermark.ui.styles import app_stylesheet
from brush_watermark.ui.tool_rail import ToolRail
from brush_watermark.ui.top_bar import TopBar
from brush_watermark.ui.update_checker import UpdateChecker
from brush_watermark.ui.zoom import clamp_zoom, step_zoom

# Widgets where Space is typed text, not "hold to pan".
_TEXT_INPUT_TYPES = (QLineEdit, QAbstractSpinBox, QTextEdit, QPlainTextEdit)


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    return QPixmap.fromImage(ImageQt(image))


class MainWindow(QMainWindow):
    def __init__(self, docs: list[Document]):
        super().__init__()
        # Load with services.document.load_documents so each doc has its own Settings.
        self.docs: list[Document] = list(docs)
        self.active_index = 0
        self.swatch_colors = build_swatch_palette(self.doc.original)
        self.last_pointer: Optional[tuple[float, float]] = None

        self.preview_pixmap: Optional[QPixmap] = None
        self.scale = 1.0
        self.display_w = 1
        self.display_h = 1
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.refresh_pending = False
        self.zoom_is_fit = True
        self.manual_scale = 1.0  # used while zoom_is_fit is False
        # (img_x, img_y, viewport_x, viewport_y): keep that image point under
        # that viewport point after the next zoom change.
        self._pending_zoom_anchor: Optional[tuple[float, float, float, float]] = None
        self._space_held = False
        self.suppress_guides = False
        self._wheel_guide_timer = QTimer(self)
        self._wheel_guide_timer.setSingleShot(True)
        self._wheel_guide_timer.timeout.connect(self._clear_wheel_guide_suppress)

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
        self._update_checker: UpdateChecker | None = None
        self._auto_updater: AutoUpdater | None = None
        self._update_result: UpdateCheckResult | None = None
        self._auto_watermark_worker: AutoWatermarkWorker | None = None

        self.setWindowTitle(f"{APP_NAME} - {self.doc.image_path.name}")
        self.resize(1560, 980)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(app_stylesheet())

        self._build_ui()
        self._build_menu_bar()
        self._connect_signals()
        # App-wide so Space-to-pan works whatever widget has focus (and a
        # focused button isn't clicked by it).
        QApplication.instance().installEventFilter(self)
        self._refresh_document_list_ui()
        self.update_labels()
        self.schedule_preview(1)
        QTimer.singleShot(0, self._start_update_check)

    @property
    def doc(self) -> Document:
        return self.docs[self.active_index]

    def closeEvent(self, event):
        # Give in-flight workers a bounded chance to finish so Qt doesn't destroy
        # a running QThread. None of them are cancellable, so just wait.
        for worker in (self._auto_watermark_worker, self._update_checker, self._auto_updater):
            if worker is not None and worker.isRunning():
                worker.wait(3000)
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    def _build_filmstrip_thumbnails(self) -> list[QPixmap]:
        pixmaps = []
        for doc in self.docs:
            pixmap = pil_to_qpixmap(doc.original).scaled(
                THUMB_W,
                THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmaps.append(pixmap)
        return pixmaps

    def _update_dirty_indicators(self) -> None:
        flags = [doc.dirty for doc in self.docs]
        self.filmstrip.set_dirty_flags(flags)
        self.top_bar.set_unsaved(self.doc.dirty)
        self.top_bar.set_multi_document_mode(len(self.docs) > 1, sum(flags))

    def _build_menu_bar(self):
        file_menu = self.top_bar.add_menu("&File")

        # Actions with shortcuts are also added to the window so the keys work
        # while their menu is closed. Each key belongs to exactly one action.
        self.save_action = QAction("Save && Close", self)
        self.save_action.setShortcut(QKeySequence("Ctrl+S"))
        self.save_action.triggered.connect(lambda _checked=False: self.save_and_close())
        file_menu.addAction(self.save_action)
        self.addAction(self.save_action)

        save_copy_action = QAction("Save Copy && Close", self)
        save_copy_action.triggered.connect(lambda _checked=False: self.save_copy_and_close())
        file_menu.addAction(save_copy_action)

        self.save_all_action = QAction("Save All && Close", self)
        self.save_all_action.triggered.connect(lambda _checked=False: self.save_all_and_close())
        file_menu.addAction(self.save_all_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit Without Saving", self)
        exit_action.triggered.connect(lambda _checked=False: self.exit_without_saving())
        file_menu.addAction(exit_action)

        self.prev_image_action = QAction("Previous image", self)
        self.prev_image_action.setShortcut(QKeySequence("Ctrl+Left"))
        self.prev_image_action.triggered.connect(lambda _checked=False: self.show_previous_image())
        self.next_image_action = QAction("Next image", self)
        self.next_image_action.setShortcut(QKeySequence("Ctrl+Right"))
        self.next_image_action.triggered.connect(lambda _checked=False: self.show_next_image())
        self.addAction(self.prev_image_action)
        self.addAction(self.next_image_action)

        tools_menu = self.top_bar.add_menu("&Tools")

        install_explorer_action = QAction(f'Install Explorer "{MENU_TEXT}"', self)
        install_explorer_action.setEnabled(sys.platform == "win32")
        install_explorer_action.triggered.connect(lambda _checked=False: self.install_explorer_context_menu())
        tools_menu.addAction(install_explorer_action)

        uninstall_explorer_action = QAction(f'Remove Explorer "{MENU_TEXT}"', self)
        uninstall_explorer_action.setEnabled(sys.platform == "win32")
        uninstall_explorer_action.triggered.connect(lambda _checked=False: self.uninstall_explorer_context_menu())
        tools_menu.addAction(uninstall_explorer_action)

        help_menu = self.top_bar.add_menu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda _checked=False: self.show_about())
        help_menu.addAction(about_action)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("AppRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        self.tool_rail = ToolRail()
        body.addWidget(self.tool_rail)

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
            should_pan=self._should_pan,
            on_pan=self._pan_by,
            on_pan_state=lambda _panning: self._update_canvas_cursor(),
        )
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setObjectName("CanvasScrollArea")
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_area = CanvasArea(self.canvas_scroll)
        self.canvas_area.hint_pill.set_tool(self.active_tool)

        self.filmstrip = FilmstripWidget()
        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(0)
        center.addWidget(self.canvas_area, 1)
        center.addWidget(self.filmstrip)
        body.addLayout(center, 1)

        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setObjectName("InspectorScroll")
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inspector_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.inspector_scroll.setFixedWidth(INSPECTOR_WIDTH)
        self.inspector = InspectorPanel(self.doc.settings, self.swatch_colors)
        self.inspector_scroll.setWidget(self.inspector)
        body.addWidget(self.inspector_scroll)

        self.footer = StatusFooter()
        root.addWidget(self.footer)

    def _connect_signals(self):
        ins = self.inspector
        ins.document_settings_changed.connect(self.document_settings_changed)
        ins.stroke_controls_changed.connect(self.stroke_controls_changed)
        ins.layer_item_clicked.connect(self.on_layer_item_clicked)
        ins.layer_visibility_toggled.connect(self.on_layer_visibility_toggled)
        ins.delete_selected.connect(self.delete_selected_stroke)
        ins.delete_all.connect(self.clear_all)
        ins.guide_suppress_changed.connect(self.set_guide_suppressed)
        ins.auto_place_requested.connect(self.start_auto_watermark)
        self.top_bar.save_and_close.connect(self.save_and_close)
        self.top_bar.save_copy_and_close.connect(self.save_copy_and_close)
        self.top_bar.save_all_and_close.connect(self.save_all_and_close)
        self.top_bar.exit_without_saving.connect(self.exit_without_saving)
        self.top_bar.preview_changed.connect(lambda _original: self.on_preview_mode_changed())
        self.tool_rail.tool_changed.connect(self.set_active_tool)
        self.tool_rail.auto_place_requested.connect(lambda: self.start_auto_watermark(ins.density()))
        zoom_pill = self.canvas_area.zoom_pill
        zoom_pill.zoom_mode_changed.connect(self.on_zoom_mode_changed)
        zoom_pill.zoom_step_requested.connect(lambda direction: self.zoom_step(direction))
        zoom_pill.zoom_percent_entered.connect(lambda scale: self.set_zoom(scale))
        self.footer.update_now.connect(self.start_auto_update)
        self.filmstrip.imageSelected.connect(self.switch_active_document)
        self.filmstrip.previousRequested.connect(self.show_previous_image)
        self.filmstrip.nextRequested.connect(self.show_next_image)

    def _start_update_check(self):
        self.footer.set_version_info(__version__)
        checker = UpdateChecker(self)
        checker.completed.connect(self._on_update_check_finished)
        self._update_checker = checker
        checker.start()

    def _on_update_check_finished(self, result):
        self._update_result = result
        self.footer.set_version_info(__version__, result)
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

        self._commit_inspector_settings()

        self.footer.set_update_progress(0, "Preparing update…")
        updater = AutoUpdater(result.download_url, os.getpid(), sys.argv[1:])
        updater.progress.connect(self.footer.set_update_progress)
        updater.failed.connect(self._on_auto_update_failed)
        self._auto_updater = updater
        updater.start()

    def _on_auto_update_failed(self, message: str):
        self._auto_updater = None
        self.footer.clear_update_progress()
        QMessageBox.critical(
            self,
            APP_NAME,
            f"Could not install the update.\n\n{message}",
        )

    def start_auto_watermark(self, density: int):
        if self._auto_watermark_worker is not None:
            return
        self._set_auto_watermark_running(True)
        worker = AutoWatermarkWorker(self.doc.original, density, self)
        worker.completed.connect(self._on_auto_watermark_completed)
        worker.failed.connect(self._on_auto_watermark_failed)
        self._auto_watermark_worker = worker
        worker.start()

    def _set_auto_watermark_running(self, running: bool) -> None:
        self.inspector.set_auto_watermark_running(running)
        self.tool_rail.auto_place_btn.setEnabled(not running)

    def _on_auto_watermark_completed(self, paths: list):
        self._auto_watermark_worker = None
        self._set_auto_watermark_running(False)
        added = add_paths_as_strokes(self.doc, paths)
        if added:
            self.inspector.set_auto_watermark_status(f"Placed {len(added)} watermark(s).")
            self.refresh_stroke_list()
            self.schedule_preview()
        else:
            self.inspector.set_auto_watermark_status(
                "No suitable busy areas found away from the subject."
            )

    def _on_auto_watermark_failed(self, message: str):
        self._auto_watermark_worker = None
        self._set_auto_watermark_running(False)
        self.inspector.set_auto_watermark_status(f"Auto-placement failed: {message}")

    def install_explorer_context_menu(self):
        try:
            install_context_menu()
        except (OSError, RuntimeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not install Explorer menu.\n\n{exc}")
            return
        QMessageBox.information(
            self,
            APP_NAME,
            f'Explorer will now show "{MENU_TEXT}" when you right-click JPG and JPEG files. '
            "Selecting multiple files opens them together for editing.",
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
            brush_size=self.inspector.brush_row.slider.value(),
            show_original=self.top_bar.show_original(),
            active_tool=self.active_tool,
            line_start_xy=self.line_start_xy,
            selected_anchor_index=self.selected_anchor_index,
            snap_endpoint_xy=self.snap_endpoint[1] if self.snap_endpoint else None,
            is_drawing=self.is_painting,
            suppress_guides=self.suppress_guides,
        )

    def _sync_document_settings_from_inspector(self):
        self.doc.settings = self.inspector.read_document_settings(self.doc.settings)

    def _sync_tool_defaults_from_inspector(self):
        tool = self.inspector.read_tool_defaults()
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
        ins = self.inspector
        controls = ins.read_stroke_controls()
        brush = controls["brush_size"]
        strength = f"{controls['opacity']}%"
        ins.opacity_row.set_value_text(strength)
        ins.brush_row.set_value_text(f"{brush} px")
        ins.softness_row.set_value_text(f"{controls['mask_softness']} px")
        ins.set_font_px(font_size_from_brush(brush))
        ins.set_delete_enabled(self._layer_selected())
        self.canvas_area.brush_readout.set_values(
            controls["text_color"], brush, strength, blend_mode_label(controls["blend_mode"])
        )
        self.canvas_area.refresh_overlays()

    def document_settings_changed(self):
        self._commit_inspector_settings()
        self.update_labels()
        self.canvas.update()
        self.schedule_preview()

    def stroke_controls_changed(self):
        if self._layer_selected():
            self.doc.update_selected_stroke(**self.inspector.read_stroke_controls())
            self.refresh_stroke_list()
        else:
            self._sync_tool_defaults_from_inspector()
            save_settings(self.doc.settings.to_dict())
        self.update_labels()
        self.schedule_preview()

    def sync_list_selection(self):
        self.inspector.set_selected_layer(self.doc.selected_stroke_index if self._layer_selected() else -1)

    def refresh_stroke_list(self):
        items = [
            LayerItem(stroke.name, self.doc.stroke_meta_text(stroke), stroke.visible)
            for stroke in self.doc.strokes
        ]
        selected = self.doc.selected_stroke_index if self._layer_selected() else -1
        self.inspector.set_layers(items, selected)

    def on_layer_visibility_toggled(self, index: int) -> None:
        if not 0 <= index < len(self.doc.strokes):
            return
        stroke = self.doc.strokes[index]
        self.doc.set_stroke_visible(index, not stroke.visible)
        self.refresh_stroke_list()
        if index == self.doc.selected_stroke_index:
            self.inspector.set_brush_context(layer_name=stroke.name, visible=stroke.visible)
        self.schedule_preview()

    def on_layer_item_clicked(self, row: int):
        if row < 0:
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
        sb = self.inspector
        self.suppress_guides = True
        self.canvas.update()
        self._wheel_guide_timer.start(400)
        if alt:
            value = clamp(sb.brush_row.slider.value() + step * 12, 5, 600)
            sb.brush_row.slider.setValue(int(value))
        else:
            value = clamp(sb.opacity_row.slider.value() + step * 2, 1, 100)
            sb.opacity_row.slider.setValue(int(value))

    def _clear_wheel_guide_suppress(self):
        self.suppress_guides = False
        self.canvas.update()

    def on_zoom_mode_changed(self, is_100: bool):
        if is_100:
            self.set_zoom(1.0)
            return
        self.zoom_is_fit = True
        self._pending_zoom_anchor = None
        self.refresh_preview()

    def set_zoom(self, scale: float, anchor: Optional[tuple[float, float]] = None) -> None:
        """Zoom to `scale`, keeping the image point under `anchor` (viewport
        coordinates; default: the viewport centre) where it is."""
        viewport = self.canvas_scroll.viewport()
        if anchor is None:
            anchor = (viewport.width() / 2, viewport.height() / 2)
        ax, ay = anchor
        # The canvas sits at -scroll inside the viewport.
        img_x = (ax - self.canvas.x() - self.offset_x) / max(self.scale, 0.0001)
        img_y = (ay - self.canvas.y() - self.offset_y) / max(self.scale, 0.0001)
        self.zoom_is_fit = False
        self.manual_scale = clamp_zoom(scale)
        self._pending_zoom_anchor = (img_x, img_y, ax, ay)
        self.refresh_preview()

    def zoom_step(self, direction: int, anchor: Optional[tuple[float, float]] = None) -> None:
        self.set_zoom(step_zoom(self.scale, direction), anchor)

    def _zoom_click(self, canvas_x: float, canvas_y: float) -> None:
        alt = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        anchor = (canvas_x + self.canvas.x(), canvas_y + self.canvas.y())
        self.zoom_step(-1 if alt else 1, anchor)

    # --- Panning (Pan tool, or Space held in any tool) ---

    def _should_pan(self) -> bool:
        return self._space_held or self.active_tool == ToolMode.PAN

    def _pan_by(self, dx: float, dy: float) -> None:
        h_bar = self.canvas_scroll.horizontalScrollBar()
        v_bar = self.canvas_scroll.verticalScrollBar()
        h_bar.setValue(h_bar.value() - round(dx))
        v_bar.setValue(v_bar.value() - round(dy))

    def set_space_held(self, held: bool) -> None:
        if held != self._space_held:
            self._space_held = held
            self._update_canvas_cursor()

    def _update_canvas_cursor(self) -> None:
        if self.canvas.is_panning:
            self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self._should_pan():
            self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.active_tool == ToolMode.ZOOM:
            self.canvas.setCursor(QCursor(get_pixmap("zoom-in", 20, TEXT), 9, 9))
        else:
            self.canvas.unsetCursor()

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype == QEvent.Type.WindowDeactivate and obj is self:
            # The Space release would go to another window; don't stay stuck panning.
            self.set_space_held(False)
        elif etype in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) and event.key() == Qt.Key.Key_Space:
            if QApplication.activeWindow() is not self or isinstance(
                QApplication.focusWidget(), _TEXT_INPUT_TYPES
            ):
                return False
            if not event.isAutoRepeat():
                self.set_space_held(etype == QEvent.Type.KeyPress)
            return True
        return super().eventFilter(obj, event)

    def set_guide_suppressed(self, suppressed: bool):
        self.suppress_guides = suppressed
        self.canvas.update()

    def select_stroke_by_index(self, index: int, refresh_preview: bool = True):
        self.doc.select_stroke(index)
        self.sync_list_selection()
        if self._layer_selected():
            self.inspector.load_stroke_controls(self.doc.strokes[index])
        else:
            self.inspector.load_tool_defaults(self.doc.settings)
        self.update_labels()
        if refresh_preview:
            self.schedule_preview()

    def switch_active_document(self, index: int) -> None:
        """Switch the displayed image (filmstrip click). Keeps every doc's edits in memory."""
        if index == self.active_index or not (0 <= index < len(self.docs)):
            return
        self._commit_inspector_settings()

        self.active_index = index
        self.snap_endpoint = None
        self.line_start_xy = None
        self._line_stopped = False
        self.suppress_guides = False
        self.left_press_img_xy = None
        self.left_press_candidate = -1
        self.left_press_on_selected = False
        self.is_painting = False
        self.is_erasing = False
        self.last_img_xy = None
        self.last_pointer = None

        self.filmstrip.set_active_index(index)
        self._load_active_document_into_ui()
        self.canvas.update()

    def show_previous_image(self) -> None:
        if len(self.docs) > 1:
            self.switch_active_document((self.active_index - 1) % len(self.docs))

    def show_next_image(self) -> None:
        if len(self.docs) > 1:
            self.switch_active_document((self.active_index + 1) % len(self.docs))

    def _refresh_file_info(self) -> None:
        doc = self.doc
        self.top_bar.set_file_info(doc.image_path.name, doc.metadata.serial, self.active_index, len(self.docs))

    def _load_active_document_into_ui(self) -> None:
        """Point the title, swatches, stroke list and controls at the active doc."""
        doc = self.doc
        self.setWindowTitle(f"{APP_NAME} - {doc.image_path.name}")
        self.swatch_colors = build_swatch_palette(doc.original)
        self.inspector.set_swatches(self.swatch_colors, doc.settings.text_color)
        self.inspector.load_document_settings(doc.settings)
        self._refresh_file_info()
        self.selected_anchor_index = -1
        self.anchor_drag_active = False
        self.refresh_stroke_list()
        if self._layer_selected():
            self.inspector.load_stroke_controls(doc.strokes[doc.selected_stroke_index])
        else:
            self.inspector.load_tool_defaults(doc.settings)
        self.update_labels()
        self.schedule_preview(1)

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
        self._update_dirty_indicators()
        if self.refresh_pending:
            return
        self.refresh_pending = True
        QTimer.singleShot(delay_ms, self.refresh_preview)

    def refresh_preview(self):
        self.refresh_pending = False
        self.update_labels()
        viewport = self.canvas_scroll.viewport()
        canvas_w = max(1, viewport.width())
        canvas_h = max(1, viewport.height())
        include_metadata = (
            not self.top_bar.show_original()
            and self.doc.settings.add_visible_metadata
        )
        content_w, content_h = self.doc.preview_content_size(include_metadata=include_metadata)
        if self.zoom_is_fit:
            # Fit the image to the canvas, but never upscale past 1:1 (100%). A small
            # image (e.g. 100px) stays at its native pixel size instead of being blown
            # up to the monitor resolution, which avoids a blurry/pixelated preview.
            fit_scale = min(canvas_w / content_w, canvas_h / content_h)
            self.scale = max(0.0001, min(fit_scale, 1.0))
        else:
            self.scale = self.manual_scale
        self.canvas_area.zoom_pill.set_zoom_state(round(self.scale * 100), self.zoom_is_fit)
        self.display_w = max(1, int(self.doc.full_w * self.scale))
        self.display_h = max(1, int(self.doc.full_h * self.scale))
        # Above 100 % the preview is rendered at 1:1 and the canvas scales it up
        # when drawing; rendering it at 400 % would cost far too much memory.
        render_scale = min(self.scale, 1.0)
        render_w = max(1, int(self.doc.full_w * render_scale))
        render_h = max(1, int(self.doc.full_h * render_scale))
        if self.top_bar.show_original():
            preview_image = self.doc.make_original_preview_image(render_w, render_h)
        else:
            preview_image = self.doc.make_preview_image(render_w, render_h, render_scale)
        pixmap_w, pixmap_h = preview_image.size
        if self.scale > render_scale:
            ratio = self.scale / render_scale
            pixmap_w, pixmap_h = round(pixmap_w * ratio), round(pixmap_h * ratio)

        if self.zoom_is_fit:
            self.canvas_scroll.setWidgetResizable(True)
            self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.canvas.setMinimumSize(400, 300)
            self.canvas.setMaximumSize(16777215, 16777215)
        else:
            self.canvas_scroll.setWidgetResizable(False)
            self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            canvas_w = max(pixmap_w, canvas_w)
            canvas_h = max(pixmap_h, canvas_h)
            self.canvas.setFixedSize(canvas_w, canvas_h)

        self.offset_x = (canvas_w - pixmap_w) // 2
        self.offset_y = (canvas_h - pixmap_h) // 2
        self.preview_pixmap = pil_to_qpixmap(preview_image)
        self.canvas.preview_pixmap = self.preview_pixmap
        self.canvas.preview_draw_size = (pixmap_w, pixmap_h)
        if self._pending_zoom_anchor is not None:
            img_x, img_y, ax, ay = self._pending_zoom_anchor
            self._pending_zoom_anchor = None
            if not self.zoom_is_fit:
                self.canvas_scroll.horizontalScrollBar().setValue(round(self.offset_x + img_x * self.scale - ax))
                self.canvas_scroll.verticalScrollBar().setValue(round(self.offset_y + img_y * self.scale - ay))
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
            self.suppress_guides = False
        self.tool_rail.set_active_tool(self.active_tool)
        self._update_canvas_cursor()
        self.canvas_area.hint_pill.set_tool(self.active_tool)
        self.canvas_area.refresh_overlays()
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
        elif key == Qt.Key.Key_H:
            self.set_active_tool(ToolMode.PAN)
        elif key == Qt.Key.Key_Z:
            self.set_active_tool(ToolMode.ZOOM)
        elif key == Qt.Key.Key_Escape:
            if self.active_tool == ToolMode.BRUSH and self.line_start_xy is not None:
                self.line_start_xy = None
                self.canvas.update()
            elif self.active_tool == ToolMode.PATH and self.selected_anchor_index >= 0:
                self.selected_anchor_index = -1
                self.canvas.update()
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            # A selected Path anchor goes first; otherwise the selected layer.
            if self.active_tool == ToolMode.PATH and self.selected_anchor_index >= 0:
                self.doc.delete_anchor(self.doc.selected_stroke_index, self.selected_anchor_index)
                self.selected_anchor_index = -1
                self.refresh_stroke_list()
                self.schedule_preview()
            elif self._layer_selected():
                self.delete_selected_stroke()
        else:
            super().keyPressEvent(event)

    # --- Left-button dispatch ---

    def start_left_interaction(self, canvas_x: float, canvas_y: float):
        # Pan presses never get here (CanvasWidget handles them via should_pan).
        if self.active_tool == ToolMode.ZOOM:
            self._zoom_click(canvas_x, canvas_y)
            return
        if self.active_tool == ToolMode.PAN:
            return
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
        if self.active_tool in (ToolMode.POINTER, ToolMode.PAN, ToolMode.ZOOM):
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
        if self.active_tool in (ToolMode.PAN, ToolMode.ZOOM):
            return
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
        if self.active_tool == ToolMode.ZOOM:
            # The second click of a quick double-click is still a zoom click.
            self._zoom_click(canvas_x, canvas_y)
            return
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
        self.doc.current_brush_size = self.inspector.brush_row.slider.value()
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
            controls = self.inspector.read_stroke_controls()
            opacity = controls["opacity"]
            if self.doc.settings.auto_strength:
                opacity = opacity_for_path(
                    self.doc.original, points, self.doc.current_brush_size, controls["mask_softness"]
                )
            self.doc.add_stroke(
                points,
                self.doc.current_brush_size,
                opacity,
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
            self.suppress_guides = True
            self.last_img_xy = (img_x, img_y)
            self.canvas.update()
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
            self.suppress_guides = False
            self.canvas.update()
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

    def _commit_inspector_settings(self):
        """Pull pending inspector edits into the active doc/tool defaults and persist them."""
        self._sync_document_settings_from_inspector()
        if not self._layer_selected():
            self._sync_tool_defaults_from_inspector()
        save_settings(self.doc.settings.to_dict())

    def _confirm_save_without_strokes(self, doc: Document) -> bool:
        if doc.strokes:
            return True
        answer = QMessageBox.question(
            self,
            APP_NAME,
            f"{doc.image_path.name}: you did not paint any stroke. Save unchanged image and close?",
        )
        return answer == QMessageBox.StandardButton.Yes

    def _write_final_image(self, doc: Document, export_path: Path) -> bool:
        try:
            final = doc.make_full_composited_image()
            save_kwargs = {"quality": 95, "subsampling": 0, "optimize": True}
            if doc.exif_bytes:
                save_kwargs["exif"] = doc.exif_bytes
            final.save(export_path, **save_kwargs)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        doc.dirty = False
        if self.inspector.reveal_in_explorer_check.isChecked():
            reveal_in_explorer(export_path)
        return True

    def add_documents(self, paths: list[Path]) -> None:
        """Append images handed over by a sibling launch (see launch_collector).

        Runs on the Qt event loop, same thread as everything else here, so
        no locking is needed.
        """
        existing = {doc.image_path.resolve() for doc in self.docs}
        new_paths = sorted(
            (path for path in paths if path.resolve() not in existing),
            key=lambda path: path.name,
        )
        if not new_paths:
            return

        new_docs, errors = load_documents(new_paths, self.doc.settings)
        if errors:
            QMessageBox.warning(self, APP_NAME, format_load_errors(errors))
        if not new_docs:
            return
        self.docs.extend(new_docs)
        self._refresh_document_list_ui()

    def _remove_document(self, index: int) -> None:
        """Drop a saved image from the session; close the window once none remain."""
        del self.docs[index]
        if not self.docs:
            self.close()
            return

        self.active_index = min(index, len(self.docs) - 1)
        self._refresh_document_list_ui()
        self._load_active_document_into_ui()

    def _refresh_document_list_ui(self) -> None:
        """Rebuild the filmstrip and toggle the multi-image-only UI after docs change."""
        multi = len(self.docs) > 1
        self.filmstrip.set_thumbnails(self._build_filmstrip_thumbnails())
        self.filmstrip.setVisible(multi)
        self.filmstrip.set_active_index(self.active_index)
        self.save_all_action.setVisible(multi)
        self.footer.set_multi_image(multi)
        self._refresh_file_info()
        self._update_dirty_indicators()

    def save_and_close(self):
        doc = self.doc
        self._commit_inspector_settings()
        if not self._confirm_save_without_strokes(doc):
            return
        if self._write_final_image(doc, doc.image_path):
            self._remove_document(self.active_index)

    def save_copy_and_close(self):
        doc = self.doc
        self._commit_inspector_settings()
        if not self._confirm_save_without_strokes(doc):
            return
        export_path = build_watermarked_copy_path(doc.image_path)
        if self._write_final_image(doc, export_path):
            self._remove_document(self.active_index)

    def save_all_and_close(self):
        self._commit_inspector_settings()
        if any(not doc.strokes for doc in self.docs):
            answer = QMessageBox.question(
                self,
                APP_NAME,
                "One or more images have no painted strokes. Save all unchanged and close?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        for doc in self.docs:
            if not self._write_final_image(doc, doc.image_path):
                return
        self.close()

    def exit_without_saving(self):
        self._commit_inspector_settings()
        self.close()
