from brush_watermark.ui.color_picker import ColorSwatchPicker

PALETTE = ["#101010", "#202020", "#ffffff"]


def test_palette_colour_is_selected_without_a_custom_swatch(qapp):
    picker = ColorSwatchPicker()
    picker.set_swatches(PALETTE, "#202020")
    assert picker.selected_color() == "#202020"
    assert picker.custom_color() is None


def test_colour_outside_the_palette_is_kept_exactly_as_a_custom_swatch(qapp):
    picker = ColorSwatchPicker()
    picker.set_swatches(PALETTE, "#ff8800")
    assert picker.selected_color() == "#ff8800"
    assert picker.custom_color() == "#ff8800"
    picker.set_selected("#123456")
    assert picker.selected_color() == "#123456" and picker.custom_color() == "#123456"


def test_select_picked_emits(qapp):
    picker = ColorSwatchPicker()
    picker.set_swatches(PALETTE, "#ffffff")
    seen = []
    picker.color_changed.connect(seen.append)
    picker.select_picked("#AB12CD")
    assert seen == ["#ab12cd"] and picker.custom_color() == "#ab12cd"


def test_pick_button_survives_rebuilds_and_emits(qapp):
    picker = ColorSwatchPicker()
    picker.set_swatches(PALETTE, "#ffffff")
    picker.set_swatches(["#000000"], "#000000")
    seen = []
    picker.pick_requested.connect(lambda: seen.append(True))
    picker.pick_button.click()
    assert seen == [True]
    # The window reports pick mode back; the click alone doesn't latch it.
    assert not picker.pick_button.isChecked()
    picker.set_picking(True)
    assert picker.pick_button.isChecked()


def test_eleven_swatches_fill_one_row_and_extras_wrap(qapp):
    picker = ColorSwatchPicker()
    colors = [f"#0000{i:02x}" for i in range(11)]
    picker.set_swatches(colors, "#ff0000")
    grid = picker._grid
    row_of = lambda widget: grid.getItemPosition(grid.indexOf(widget))[0]
    assert row_of(picker._buttons[-1]) == 0
    assert row_of(picker._custom_button) == 1
    assert row_of(picker.pick_button) == 1
