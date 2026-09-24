"""Tests for the sibling-launch path payload in launch_collector."""
from pathlib import Path

from brush_watermark.ui.launch_collector import SERVER_NAME, _decode_paths, _encode_paths


def test_paths_round_trip_including_spaces_and_unicode():
    paths = [Path(r"C:\photos\my image.jpg"), Path(r"C:\fotke\Simonič_01.jpeg")]
    assert _decode_paths(_encode_paths(paths)) == paths


def test_decode_ignores_blank_lines():
    assert _decode_paths(b"a.jpg\n\n  \nb.jpg\n") == [Path("a.jpg"), Path("b.jpg")]


def test_server_name_is_per_user():
    assert SERVER_NAME.startswith("BrushWatermarkLaunchCollector-")
