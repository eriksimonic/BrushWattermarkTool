from brush_watermark.models import ToolMode
from brush_watermark.ui.tool_rail import SHORTCUTS, ToolRail


def test_clicking_a_tool_emits_it(qapp):
    rail = ToolRail()
    seen = []
    rail.tool_changed.connect(seen.append)
    rail.buttons[ToolMode.PATH].click()
    assert seen == [ToolMode.PATH]


def test_set_active_tool_checks_exclusively_without_emitting(qapp):
    rail = ToolRail()
    seen = []
    rail.tool_changed.connect(seen.append)
    rail.set_active_tool(ToolMode.ERASER)
    assert [t for t, b in rail.buttons.items() if b.isChecked()] == [ToolMode.ERASER]
    assert seen == []


def test_brush_is_active_by_default(qapp):
    assert ToolRail().buttons[ToolMode.BRUSH].isChecked()


def test_auto_place_button_emits(qapp):
    rail = ToolRail()
    seen = []
    rail.auto_place_requested.connect(lambda: seen.append(True))
    rail.auto_place_btn.click()
    assert seen == [True]


def test_shortcuts_list_existing_keys_only():
    keys = [k for k, _ in SHORTCUTS]
    assert keys[:4] == ["V", "B", "A", "E"]
    assert "Ctrl+S" not in keys and "H" not in keys and "Z" not in keys
