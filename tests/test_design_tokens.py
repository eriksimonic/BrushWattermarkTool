import re

import brush_watermark.ui.design_tokens as tokens
from brush_watermark.ui.design_tokens import rgba


def _token_values():
    return {
        name: value
        for name, value in vars(tokens).items()
        if name.isupper() and isinstance(value, str)
    }


def test_every_token_is_a_six_digit_hex():
    for name, value in _token_values().items():
        assert re.fullmatch(r"#[0-9A-F]{6}", value), name


def test_rgba_formats_qss_color():
    assert rgba("#5B8CFF", 0.16) == "rgba(91, 140, 255, 0.16)"
    assert rgba("#FFFFFF", 1) == "rgba(255, 255, 255, 1)"
