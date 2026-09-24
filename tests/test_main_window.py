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
