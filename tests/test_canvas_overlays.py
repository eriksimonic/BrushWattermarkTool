from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QScrollArea

from brush_watermark.models import ToolMode
from brush_watermark.ui.canvas import make_dot_tile
from brush_watermark.ui.canvas_overlays import CanvasArea, tool_hint
from brush_watermark.ui.design_tokens import CANVAS_BG, CANVAS_DOT


def test_every_tool_has_a_hint():
    for tool in ToolMode:
        name, hints = tool_hint(tool)
        assert name and hints


def test_hint_pill_follows_tool(qapp):
    area = CanvasArea(QScrollArea())
    area.hint_pill.set_tool(ToolMode.PATH)
    assert area.hint_pill.tool_label.text() == "Path"


def test_hint_pill_resizes_immediately_on_tool_switch(qapp):
    area = CanvasArea(QScrollArea())
    area.resize(1000, 700)
    area.show()
    qapp.processEvents()
    area.hint_pill.set_tool(ToolMode.PATH)
    qapp.processEvents()
    assert area.hint_pill.width() >= area.hint_pill.sizeHint().width()


def test_zoom_pill_emits_mode(qapp):
    area = CanvasArea(QScrollArea())
    seen = []
    area.zoom_pill.zoom_mode_changed.connect(seen.append)
    area.zoom_pill.one_to_one_btn.click()
    area.zoom_pill.fit_btn.click()
    assert seen == [True, False]
    area.zoom_pill.set_zoom_percent(62)
    assert area.zoom_pill.percent_edit.text() == "62%"


def test_zoom_pill_step_buttons_and_typed_percent(qapp):
    area = CanvasArea(QScrollArea())
    pill = area.zoom_pill
    steps, typed = [], []
    pill.zoom_step_requested.connect(steps.append)
    pill.zoom_percent_entered.connect(typed.append)
    pill.zoom_in_btn.click()
    pill.zoom_out_btn.click()
    assert steps == [1, -1]
    pill.percent_edit.setText("150")
    pill.percent_edit.editingFinished.emit()
    assert typed == [1.5]


def test_zoom_pill_rejects_garbage_and_restores_text(qapp):
    area = CanvasArea(QScrollArea())
    pill = area.zoom_pill
    typed = []
    pill.zoom_percent_entered.connect(typed.append)
    pill.set_zoom_percent(62)
    pill.percent_edit.setText("abc")
    pill.percent_edit.editingFinished.emit()
    assert typed == [] and pill.percent_edit.text() == "62%"


def test_zoom_pill_state_can_check_neither_mode(qapp):
    area = CanvasArea(QScrollArea())
    pill = area.zoom_pill
    pill.set_zoom_state(150, fit=False)
    assert not pill.fit_btn.isChecked() and not pill.one_to_one_btn.isChecked()
    pill.set_zoom_state(100, fit=False)
    assert pill.one_to_one_btn.isChecked() and not pill.fit_btn.isChecked()
    pill.set_zoom_state(62, fit=True)
    assert pill.fit_btn.isChecked() and not pill.one_to_one_btn.isChecked()


def test_clicking_checked_fit_keeps_it_checked(qapp):
    area = CanvasArea(QScrollArea())
    pill = area.zoom_pill
    pill.fit_btn.click()
    assert pill.fit_btn.isChecked()


def test_brush_readout_values(qapp):
    area = CanvasArea(QScrollArea())
    area.brush_readout.set_values("#FFFFFF", 41, "19%", "Hard light")
    texts = (area.brush_readout.size_label.text(), area.brush_readout.strength_label.text(), area.brush_readout.blend_label.text())
    assert texts == ("41 px", "19%", "Hard light")


def test_overlays_are_positioned_on_resize(qapp):
    area = CanvasArea(QScrollArea())
    area.resize(800, 600)
    area.show()
    qapp.processEvents()
    m = CanvasArea.MARGIN
    assert area.scroll_area.geometry() == area.rect()
    assert area.hint_pill.y() == m
    assert abs(area.hint_pill.x() + area.hint_pill.width() / 2 - 400) <= 1
    assert area.zoom_pill.x() == m and area.zoom_pill.geometry().bottom() == 600 - m - 1
    assert area.brush_readout.geometry().right() == 800 - m - 1


def test_dot_tile(qapp):
    image = make_dot_tile().toImage()
    assert (image.width(), image.height()) == (20, 20)
    assert image.pixelColor(0, 0) == QColor(CANVAS_DOT)
    assert image.pixelColor(10, 10) == QColor(CANVAS_BG)


def test_overlays_transparent_to_mouse_events(qapp):
    area = CanvasArea(QScrollArea())
    assert area.hint_pill.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert area.brush_readout.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert not area.zoom_pill.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
