from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from brush_watermark.ui.controls import (
    AccentSlider,
    Chip,
    CollapsibleSection,
    KeyCombo,
    SegmentedControl,
    SliderRow,
    SplitButton,
    Stepper,
    SwitchRow,
    ToggleSwitch,
)


def test_toggle_switch_click_toggles(qapp):
    switch = ToggleSwitch()
    switch.show()
    seen = []
    switch.toggled.connect(seen.append)
    QTest.mouseClick(switch, Qt.MouseButton.LeftButton)
    assert switch.isChecked() and seen == [True]


def test_switch_row_label_click_toggles_and_forwards(qapp):
    row = SwitchRow("Auto-fit text to stroke")
    row.show()
    seen = []
    row.toggled.connect(seen.append)
    QTest.mouseClick(row.label, Qt.MouseButton.LeftButton)
    assert row.isChecked() is True and seen == [True]


def test_switch_row_blocked_signals_do_not_forward(qapp):
    row = SwitchRow("Repeat along stroke")
    seen = []
    row.toggled.connect(seen.append)
    row.blockSignals(True)
    row.setChecked(True)
    row.blockSignals(False)
    assert row.isChecked() and seen == []


def test_stepper_clamps_and_emits_only_changes(qapp):
    stepper = Stepper(0, 2, 1, prefix="gap")
    seen = []
    stepper.valueChanged.connect(seen.append)
    stepper.setValue(5)
    stepper.setValue(2)
    stepper.setValue(-3)
    assert seen == [2, 0] and stepper.value() == 0
    assert stepper._label.text() == "gap 0"
    assert not stepper._minus.isEnabled() and stepper._plus.isEnabled()


def test_segmented_control_emits_index(qapp):
    control = SegmentedControl(["Original", "Watermarked"])
    seen = []
    control.currentChanged.connect(seen.append)
    control.setCurrentIndex(1)
    assert control.currentIndex() == 1 and seen == [1]


def test_accent_slider_maps_positions_to_values(qapp):
    slider = AccentSlider()
    slider.setRange(0, 100)
    slider.resize(216, 20)
    for value in (0, 25, 50, 100):
        assert slider.x_to_value(slider.value_to_x(value)) == value
    assert slider.x_to_value(-50) == 0
    assert slider.x_to_value(10_000) == 100


def test_slider_row_header_widget_sits_before_value(qapp):
    row = SliderRow("Strength", 1, 100, 50)
    chip = Chip("Auto")
    row.add_header_widget(chip)
    assert row._header.indexOf(chip) == row._header.indexOf(row.value_label) - 1


def test_collapsible_section_toggles_body(qapp):
    section = CollapsibleSection("Brush", icon_name="paintbrush")
    seen = []
    section.toggled.connect(seen.append)
    section._toggle()
    assert section._body.isHidden() and seen == [False] and not section.is_expanded()
    section._toggle()
    assert not section._body.isHidden() and seen == [False, True]


def test_collapsible_section_can_start_collapsed(qapp):
    section = CollapsibleSection("Export", icon_name="image", expanded=False)
    assert section._body.isHidden()


def test_split_button_main_click_emits(qapp):
    button = SplitButton("Save && close", "save")
    seen = []
    button.clicked.connect(lambda: seen.append(True))
    button.main.click()
    assert seen == [True]


def test_key_combo_splits_on_plus(qapp):
    combo = KeyCombo("Alt+Wheel")
    assert [label.text() for label in combo.findChildren(QLabel)] == ["Alt", "+", "Wheel"]
