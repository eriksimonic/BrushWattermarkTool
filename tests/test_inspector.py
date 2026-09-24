from brush_watermark.models import Settings, Stroke
from brush_watermark.ui.inspector import INSPECTOR_WIDTH, InspectorPanel
from brush_watermark.ui.layer_list import LayerItem

SWATCHES = ["#FFFFFF", "#808080", "#000000"]


def make_panel() -> InspectorPanel:
    return InspectorPanel(Settings(), SWATCHES)


def test_load_tool_defaults_round_trips_without_emitting(qapp):
    panel = make_panel()
    seen = []
    panel.stroke_controls_changed.connect(lambda: seen.append(1))
    panel.load_tool_defaults(
        Settings(brush_size=77, opacity=33, mask_softness=4, repeat_text=True, repeat_spacing=9)
    )
    c = panel.read_stroke_controls()
    assert (c["brush_size"], c["opacity"], c["mask_softness"], c["repeat_text"], c["repeat_spacing"]) == (
        77, 33, 4, True, 9,
    )
    assert seen == []


def test_load_stroke_controls_titles_the_brush_section(qapp):
    panel = make_panel()
    stroke = Stroke(name="Stroke 2", points=[(0, 0), (9, 9)], brush_size=40, opacity=20, visible=False)
    panel.load_stroke_controls(stroke)
    assert panel.brush_section._title_label.text() == "Layer · Stroke 2 · hidden"


def test_auto_strength_disables_only_the_slider(qapp):
    panel = make_panel()
    panel.auto_strength_check.setChecked(True)
    assert not panel.opacity_row.slider.isEnabled()
    assert panel.auto_strength_check.isEnabled()


def test_repeat_switch_enables_gap_stepper(qapp):
    panel = make_panel()
    panel.repeat_text_check.setChecked(True)
    assert panel.repeat_spacing_spin.isEnabled()
    panel.repeat_text_check.setChecked(False)
    assert not panel.repeat_spacing_spin.isEnabled()


def test_set_layers_updates_badge_and_rows(qapp):
    panel = make_panel()
    panel.set_layers([LayerItem("S1", "10 px", True), LayerItem("S2", "20 px", False)], selected=1)
    assert panel.layer_count_badge.text() == "2"
    rows = panel.layer_list.rows()
    assert len(rows) == 2 and rows[1].property("selected") is True


def test_layer_signals_are_forwarded(qapp):
    panel = make_panel()
    panel.set_layers([LayerItem("S1", "10 px", True)])
    seen = []
    panel.layer_visibility_toggled.connect(seen.append)
    panel.layer_list.rows()[0].eye.click()
    assert seen == [0]


def test_auto_place_button_emits_density(qapp):
    panel = make_panel()
    panel.auto_density_row.slider.setValue(9)
    seen = []
    panel.auto_place_requested.connect(seen.append)
    panel.auto_place_btn.click()
    assert seen == [9] and panel.density() == 9


def test_read_document_settings_reads_switches(qapp):
    panel = make_panel()
    panel.watermark_text_edit.setText("© Me")
    panel.add_metadata_check.setChecked(True)
    settings = panel.read_document_settings(Settings())
    assert settings.watermark_text == "© Me" and settings.add_visible_metadata is True


def test_font_px_chip_and_delete_enabled(qapp):
    panel = make_panel()
    panel.set_font_px(21)
    panel.set_delete_enabled(False)
    assert panel.font_px_chip.text() == "21 px" and not panel.delete_selected_btn.isEnabled()


def test_width_leaves_room_for_the_scrollbar(qapp):
    assert make_panel().width() == INSPECTOR_WIDTH - 10


def test_reveal_in_explorer_defaults_on(qapp):
    assert make_panel().reveal_in_explorer_check.isChecked() is True


def _section_title(widget) -> str:
    from brush_watermark.ui.controls import CollapsibleSection

    parent = widget.parentWidget()
    while parent is not None and not isinstance(parent, CollapsibleSection):
        parent = parent.parentWidget()
    return parent._title_label.text() if parent is not None else ""


def test_metadata_strip_switch_lives_in_the_always_open_watermark_section(qapp):
    panel = make_panel()
    assert _section_title(panel.add_metadata_check) == "Watermark"
    assert _section_title(panel.metadata_copy_edit) == "Watermark"


def test_copy_info_field_only_shows_while_strip_is_on(qapp):
    panel = make_panel()
    panel.add_metadata_check.setChecked(False)
    assert panel.metadata_copy_edit.isHidden()
    panel.add_metadata_check.setChecked(True)
    assert not panel.metadata_copy_edit.isHidden()
