"""Offscreen smoke tests for the redesigned MainWindow wiring."""
import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenuBar

from brush_watermark.models import Settings, Stroke, ToolMode
from brush_watermark.rendering.fonts import font_size_from_brush
from brush_watermark.services.document import load_documents
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
