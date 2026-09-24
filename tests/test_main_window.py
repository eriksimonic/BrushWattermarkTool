"""Offscreen smoke tests for the redesigned MainWindow wiring."""
import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenuBar

from brush_watermark.models import Settings, Stroke, ToolMode
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.document import load_documents
import brush_watermark.ui.main_window as main_window
from brush_watermark.ui.main_window import MainWindow


@pytest.fixture
def make_window(qapp, tmp_path, monkeypatch):
    # Never touch the real settings file or the network from tests.
    monkeypatch.setattr("brush_watermark.ui.main_window.save_settings", lambda *_a, **_k: None)
    monkeypatch.setattr(MainWindow, "_start_update_check", lambda self: None)
    windows = []

    def _make(count: int = 1) -> MainWindow:
        paths = []
        for i in range(count):
            path = tmp_path / f"img{i}.jpg"
            Image.new("RGB", (320, 200), (90 + i * 20, 120, 150)).save(path)
            paths.append(path)
        docs, errors = load_documents(paths, Settings())
        assert errors == []
        window = MainWindow(docs)
        window.resize(1440, 960)
        window.show()
        qapp.processEvents()
        windows.append(window)
        return window

    yield _make
    for window in windows:
        window.close()


def add_stroke(window: MainWindow) -> None:
    points = [(20.0, 20.0), (250.0, 150.0)]
    window.doc.strokes.append(
        Stroke(name="Stroke 1", points=list(points), anchors=list(points), brush_size=40, opacity=50)
    )
    window.refresh_stroke_list()


def test_single_image_layout(make_window):
    window = make_window()
    assert window.findChild(QMenuBar) is None
    assert window.filmstrip.isHidden()
    assert window.top_bar.index_badge.isHidden()
    assert not window.top_bar.save_all_action.isVisible()
    assert window.top_bar.file_name_label.text() == "img0.jpg"


def test_multi_image_layout(make_window):
    window = make_window(3)
    assert not window.filmstrip.isHidden()
    assert len(window.filmstrip.items()) == 3
    assert window.top_bar.index_badge.text() == "1 / 3"
    assert window.top_bar.save_all_action.isVisible()


def test_tool_rail_and_keys_switch_tools(make_window):
    window = make_window()
    window.tool_rail.buttons[ToolMode.PATH].click()
    assert window.active_tool == ToolMode.PATH
    assert window.canvas_area.hint_pill.tool_label.text() == "Path"
    QTest.keyClick(window, Qt.Key.Key_V)
    assert window.active_tool == ToolMode.POINTER
    assert window.tool_rail.buttons[ToolMode.POINTER].isChecked()


def test_auto_place_button_disabled_while_running(make_window, monkeypatch):
    window = make_window()

    class _FakeWorker:
        completed = type("Signal", (), {"connect": lambda self, _cb: None})()
        failed = type("Signal", (), {"connect": lambda self, _cb: None})()

        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

        def isRunning(self):
            return False

    monkeypatch.setattr("brush_watermark.ui.main_window.AutoWatermarkWorker", _FakeWorker)
    assert window.tool_rail.auto_place_btn.isEnabled()
    window.start_auto_watermark(50)
    assert not window.tool_rail.auto_place_btn.isEnabled()
    window._set_auto_watermark_running(False)
    window._auto_watermark_worker = None
    assert window.tool_rail.auto_place_btn.isEnabled()


def test_preview_toggle_shows_original(make_window):
    window = make_window()
    window.top_bar.preview_toggle.setCurrentIndex(0)
    assert window.get_canvas_view().show_original is True


def test_zoom_pill_switches_to_actual_size(make_window):
    window = make_window()
    window.canvas_area.zoom_pill.one_to_one_btn.click()
    assert window.zoom_is_fit is False


def test_eye_toggle_hides_layer(make_window):
    window = make_window()
    add_stroke(window)
    window.doc.dirty = False
    window.inspector.layer_list.rows()[0].eye.click()
    assert window.doc.strokes[0].visible is False
    assert window.doc.dirty is True
    assert window.inspector.layer_list.rows()[0].eye.toolTip() == "Show layer"


def test_layer_click_selects_and_badge_counts(make_window):
    window = make_window()
    add_stroke(window)
    assert window.inspector.layer_count_badge.text() == "1"
    window.inspector.layer_item_clicked.emit(0)
    assert window.doc.selected_stroke_index == 0
    assert window.inspector.layer_list.rows()[0].property("selected") is True


def test_labels_follow_brush_size(make_window):
    window = make_window()
    window.inspector.brush_row.slider.setValue(80)
    assert window.canvas_area.brush_readout.size_label.text() == "80 px"
    assert window.inspector.font_px_chip.text() == f"{font_size_from_brush(80)} px"


def test_unsaved_indicator_follows_dirty(make_window):
    window = make_window()
    add_stroke(window)
    window.doc.dirty = True
    window.schedule_preview(1)
    assert not window.top_bar.unsaved_indicator.isHidden()


def test_switching_images_shows_each_images_own_document_settings(make_window):
    window = make_window(2)
    window.inspector.add_metadata_check.setChecked(True)
    window.inspector.watermark_text_edit.setText("Only on image 1")
    assert window.docs[0].settings.add_visible_metadata is True

    window.switch_active_document(1)
    assert window.inspector.add_metadata_check.isChecked() is False
    assert window.inspector.watermark_text_edit.text() == window.docs[1].settings.watermark_text
    assert window.docs[1].settings.add_visible_metadata is False

    window.switch_active_document(0)
    assert window.inspector.add_metadata_check.isChecked() is True
    assert window.inspector.watermark_text_edit.text() == "Only on image 1"


def test_ctrl_s_is_the_save_action_shortcut(make_window, monkeypatch):
    window = make_window()
    assert window.save_action.shortcut().toString() == "Ctrl+S"
    assert window.save_action in window.actions()
    seen = []
    monkeypatch.setattr(window, "save_and_close", lambda: seen.append("save"))
    window.save_action.trigger()
    assert seen == ["save"]


def test_prev_next_image_wraps_around(make_window):
    window = make_window(3)
    assert window.next_image_action.shortcut().toString() == "Ctrl+Right"
    assert window.prev_image_action.shortcut().toString() == "Ctrl+Left"
    window.prev_image_action.trigger()
    assert window.active_index == 2
    window.next_image_action.trigger()
    assert window.active_index == 0
    window.filmstrip.next_button.click()
    assert window.active_index == 1
    assert window.top_bar.index_badge.text() == "2 / 3"


def test_prev_next_is_a_no_op_with_one_image(make_window):
    window = make_window()
    window.next_image_action.trigger()
    assert window.active_index == 0


def test_footer_image_nav_hint_only_with_multiple_images(make_window):
    from brush_watermark.ui.status_footer import IMAGE_NAV_HINT

    assert make_window().footer.hints[IMAGE_NAV_HINT].isHidden()
    assert not make_window(2).footer.hints[IMAGE_NAV_HINT].isHidden()


def test_delete_key_removes_selected_layer(make_window):
    window = make_window()
    add_stroke(window)
    window.select_stroke_by_index(0)
    QTest.keyClick(window, Qt.Key.Key_Delete)
    assert window.doc.strokes == []


def test_delete_key_prefers_selected_path_anchor(make_window):
    window = make_window()
    points = [(20.0, 20.0), (120.0, 80.0), (250.0, 150.0)]
    window.doc.strokes.append(
        Stroke(name="Stroke 1", points=list(points), anchors=list(points), brush_size=40, opacity=50)
    )
    window.refresh_stroke_list()
    window.select_stroke_by_index(0)
    window.set_active_tool(ToolMode.PATH)
    window.selected_anchor_index = 1
    QTest.keyClick(window, Qt.Key.Key_Delete)
    assert len(window.doc.strokes) == 1
    assert len(window.doc.strokes[0].anchors) == 2


def test_delete_key_without_selection_does_nothing(make_window):
    window = make_window()
    add_stroke(window)
    window.select_stroke_by_index(-1)
    QTest.keyClick(window, Qt.Key.Key_Delete)
    assert len(window.doc.strokes) == 1


def test_h_and_z_keys_pick_pan_and_zoom(make_window):
    window = make_window()
    QTest.keyClick(window, Qt.Key.Key_H)
    assert window.active_tool == ToolMode.PAN
    assert window.canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
    QTest.keyClick(window, Qt.Key.Key_Z)
    assert window.active_tool == ToolMode.ZOOM
    assert window.canvas_area.hint_pill.tool_label.text() == "Zoom"


def test_zoom_above_100_renders_at_1_to_1_and_scales_up(make_window):
    window = make_window()
    window.set_zoom(2.0)
    assert window.scale == 2.0 and window.zoom_is_fit is False
    assert (window.preview_pixmap.width(), window.preview_pixmap.height()) == (320, 200)
    assert window.canvas.preview_draw_size == (640, 400)
    assert window.canvas_area.zoom_pill.percent_edit.text() == "200%"


def test_zoom_keeps_the_anchor_point_under_the_cursor(make_window):
    window = make_window()
    window.set_zoom(1.0)
    viewport = window.canvas_scroll.viewport()
    anchor = (viewport.width() / 2 + 40, viewport.height() / 2 + 30)
    before = window.canvas_to_image_xy(anchor[0] - window.canvas.x(), anchor[1] - window.canvas.y())
    window.set_zoom(4.0, anchor)
    assert window.canvas_scroll.horizontalScrollBar().maximum() > 0
    after = window.canvas_to_image_xy(anchor[0] - window.canvas.x(), anchor[1] - window.canvas.y())
    # Only x: at 400 % the 200 px tall test image still fits vertically, so y can not scroll.
    assert abs(after[0] - before[0]) <= 1


def test_zoom_tool_click_zooms_in_and_alt_click_zooms_out(make_window, monkeypatch):
    window = make_window()
    window.set_active_tool(ToolMode.ZOOM)
    window.set_zoom(1.0)
    window.start_left_interaction(100, 100)
    assert window.scale == 1.5
    monkeypatch.setattr(
        main_window.QApplication, "keyboardModifiers", staticmethod(lambda: Qt.KeyboardModifier.AltModifier)
    )
    window.start_left_interaction(100, 100)
    assert window.scale == 1.0
    assert window.doc.strokes == []


def test_fit_button_returns_to_fit(make_window):
    window = make_window()
    window.set_zoom(3.0)
    window.canvas_area.zoom_pill.fit_btn.click()
    assert window.zoom_is_fit is True and window.scale <= 1.0
    assert window.canvas_area.zoom_pill.fit_btn.isChecked()


def test_pan_moves_the_scrollbars(make_window):
    window = make_window()
    window.set_zoom(4.0)
    h_bar = window.canvas_scroll.horizontalScrollBar()
    h_bar.setValue(100)
    window._pan_by(30, 0)
    assert h_bar.value() == 70


def test_pan_tool_drag_pans_instead_of_drawing(make_window):
    window = make_window()
    window.set_zoom(4.0)
    window.set_active_tool(ToolMode.PAN)
    start = window.canvas.rect().center()
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    assert window.canvas.is_panning
    assert window.canvas.cursor().shape() == Qt.CursorShape.ClosedHandCursor
    end = start + QPoint(-50, 0)
    QTest.mouseMove(window.canvas, end)
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
    assert not window.canvas.is_panning
    assert window.doc.strokes == []


def _space(etype, auto_repeat=False):
    return QKeyEvent(etype, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier, "", auto_repeat)


def test_space_hold_pans_in_brush_tool(make_window, monkeypatch):
    window = make_window()
    monkeypatch.setattr(main_window.QApplication, "activeWindow", staticmethod(lambda: window))
    monkeypatch.setattr(main_window.QApplication, "focusWidget", staticmethod(lambda: None))
    assert window.eventFilter(window, _space(QEvent.Type.KeyPress)) is True
    assert window._should_pan() and window.active_tool == ToolMode.BRUSH
    # An auto-repeat release (Windows sends these while a key is held) keeps the hold.
    assert window.eventFilter(window, _space(QEvent.Type.KeyRelease, auto_repeat=True)) is True
    assert window._should_pan()
    assert window.eventFilter(window, _space(QEvent.Type.KeyRelease)) is True
    assert not window._should_pan()


def test_space_is_left_alone_in_text_fields(make_window, monkeypatch):
    window = make_window()
    monkeypatch.setattr(main_window.QApplication, "activeWindow", staticmethod(lambda: window))
    monkeypatch.setattr(
        main_window.QApplication, "focusWidget", staticmethod(lambda: window.inspector.watermark_text_edit)
    )
    assert window.eventFilter(window, _space(QEvent.Type.KeyPress)) is False
    assert not window._space_held


def test_space_released_mid_pan_still_ends_as_a_pan(make_window):
    window = make_window()
    window.set_zoom(4.0)
    window.set_space_held(True)
    start = window.canvas.rect().center()
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    window.set_space_held(False)
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    assert not window.canvas.is_panning
    assert window.line_start_xy is None and window.doc.strokes == []


def _expected_pick(window):
    # JPEG shifts the flat fixture colour slightly, so compare against the decoded pixels.
    from brush_watermark.rendering.colors import sample_image_color

    return sample_image_color(window.doc.original, 160, 100)


def _image_center(window):
    return window.image_to_canvas_xy(160, 100)


def test_i_key_toggles_pick_mode(make_window):
    window = make_window()
    QTest.keyClick(window, Qt.Key.Key_I)
    assert window.color_pick_active
    assert window.inspector.color_picker.pick_button.isChecked()
    assert window.canvas_area.hint_pill.tool_label.text() == "Pick colour"
    assert window.canvas.cursor().shape() == Qt.CursorShape.CrossCursor
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not window.color_pick_active
    assert window.canvas_area.hint_pill.tool_label.text() == "Brush"


def test_picking_sets_tool_default_colour_without_drawing(make_window):
    window = make_window()
    window.inspector.color_picker.pick_button.click()
    assert window.color_pick_active
    x, y = _image_center(window)
    window.start_left_interaction(x, y)
    window.finish_left_interaction(x, y)
    assert not window.color_pick_active
    assert window.inspector.color_picker.selected_color() == _expected_pick(window)
    assert window.doc.settings.text_color == _expected_pick(window)
    # The release belonged to the pick, not to the Brush tool.
    assert window.line_start_xy is None and window.doc.strokes == []


def test_picking_recolours_the_selected_layer(make_window):
    window = make_window()
    add_stroke(window)
    window.select_stroke_by_index(0)
    window.start_color_pick()
    x, y = _image_center(window)
    window.start_left_interaction(x, y)
    window.finish_left_interaction(x, y)
    assert window.doc.strokes[0].text_color == _expected_pick(window)


def test_switching_tool_or_image_cancels_pick_mode(make_window):
    window = make_window(2)
    window.start_color_pick()
    window.set_active_tool(ToolMode.PATH)
    assert not window.color_pick_active
    window.start_color_pick()
    window.show_next_image()
    assert not window.color_pick_active
    assert not window.inspector.color_picker.pick_button.isChecked()


def test_pick_wins_over_pan_tool(make_window):
    window = make_window()
    window.set_active_tool(ToolMode.PAN)
    window.start_color_pick()
    assert not window._should_pan()


def test_add_images_appends_documents(make_window, tmp_path, monkeypatch):
    from PIL import Image

    window = make_window()
    extra = tmp_path / "extra.jpg"
    Image.new("RGB", (100, 80), (200, 10, 10)).save(extra)
    monkeypatch.setattr(main_window, "select_jpg_files", lambda parent=None: [extra])
    assert window.add_images_action.shortcut().toString() == "Ctrl+O"
    window.add_images_action.trigger()
    assert [doc.image_path.name for doc in window.docs] == ["img0.jpg", "extra.jpg"]
    assert not window.filmstrip.isHidden()
    window.filmstrip.add_tile.click()  # the same file again is ignored
    assert len(window.docs) == 2


def test_add_images_cancelled_changes_nothing(make_window, monkeypatch):
    window = make_window()
    monkeypatch.setattr(main_window, "select_jpg_files", lambda parent=None: [])
    window.add_images()
    assert len(window.docs) == 1
