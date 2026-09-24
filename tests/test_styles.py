import re

import brush_watermark.ui.design_tokens as tokens
from brush_watermark.ui.app_fonts import mono_family, ui_family
from brush_watermark.ui.styles import app_stylesheet


def test_stylesheet_only_uses_token_colors(qapp):
    token_hexes = {
        value.upper()
        for name, value in vars(tokens).items()
        if name.isupper() and isinstance(value, str)
    }
    used = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", app_stylesheet())}
    assert used <= token_hexes


def test_stylesheet_uses_bundled_fonts(qapp):
    css = app_stylesheet()
    assert f"font-family: '{ui_family()}'" in css
    assert f"font-family: '{mono_family()}'" in css


def test_stylesheet_styles_new_areas(qapp):
    css = app_stylesheet()
    for name in ("TopBar", "ToolRail", "InspectorPanel", "StatusFooter", "FloatingPanel", "RailButton", "LayerRow"):
        assert f"#{name}" in css, name
