from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from brush_watermark.ui.layer_list import LayerItem, LayerList

ITEMS = [LayerItem("Stroke 1", "120 px · Normal · 30%", True), LayerItem("Stroke 2", "80 px · Overlay · 20%", False)]


def test_set_layers_builds_rows_and_selection(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS, selected=1)
    rows = layers.rows()
    assert [r.name_label.text() for r in rows] == ["Stroke 1", "Stroke 2"]
    assert rows[0].property("selected") is False and rows[1].property("selected") is True
    assert layers._empty.isHidden()


def test_hidden_layer_row_is_marked(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS)
    row = layers.rows()[1]
    assert row.name_label.property("layerHidden") is True
    assert row.eye.toolTip() == "Show layer"


def test_eye_click_emits_visibility_toggle(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS)
    seen = []
    layers.visibility_toggled.connect(seen.append)
    layers.rows()[1].eye.click()
    assert seen == [1]


def test_row_click_emits_layer_clicked(qapp):
    layers = LayerList()
    layers.set_layers(ITEMS)
    layers.show()
    seen = []
    layers.layer_clicked.connect(seen.append)
    QTest.mouseClick(layers.rows()[0], Qt.MouseButton.LeftButton)
    assert seen == [0]


def test_empty_list_shows_hint(qapp):
    layers = LayerList()
    layers.set_layers([])
    assert not layers._empty.isHidden() and layers.rows() == []
