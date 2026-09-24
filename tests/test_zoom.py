import pytest

from brush_watermark.ui.zoom import ZOOM_MAX, ZOOM_MIN, clamp_zoom, parse_zoom_percent, step_zoom


def test_step_zoom_walks_presets():
    assert step_zoom(1.0, 1) == 1.5
    assert step_zoom(1.0, -1) == 0.75
    # A fit scale between presets goes to the next one either way.
    assert step_zoom(0.62, 1) == 0.67
    assert step_zoom(0.62, -1) == 0.5


def test_step_zoom_stops_at_the_limits():
    assert step_zoom(ZOOM_MAX, 1) == ZOOM_MAX
    assert step_zoom(ZOOM_MIN, -1) == ZOOM_MIN


def test_step_zoom_treats_near_preset_as_that_preset():
    assert step_zoom(0.3301, 1) == 0.5


@pytest.mark.parametrize(
    "text, expected",
    [("150", 1.5), ("150%", 1.5), (" 62 % ", 0.62), ("12,5", 0.125), ("9000", ZOOM_MAX), ("1", ZOOM_MIN)],
)
def test_parse_zoom_percent(text, expected):
    assert parse_zoom_percent(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "abc", "0", "-50"])
def test_parse_zoom_percent_rejects_garbage(text):
    assert parse_zoom_percent(text) is None


def test_clamp_zoom():
    assert clamp_zoom(100) == ZOOM_MAX
    assert clamp_zoom(0) == ZOOM_MIN
    assert clamp_zoom(0.8) == 0.8
