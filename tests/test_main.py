"""Tests for CLI argument resolution in main.py."""
from pathlib import Path
from unittest.mock import patch

from brush_watermark.main import resolve_image_paths


class TestResolveImagePaths:
    def test_single_arg_returns_single_path(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["brush_watermark", "a.jpg"])
        assert resolve_image_paths() == [Path("a.jpg")]

    def test_multiple_args_returns_all_paths(self, monkeypatch):
        # Lightroom's "Edit In" passes every selected photo as a separate argv entry.
        monkeypatch.setattr("sys.argv", ["brush_watermark", "a.jpg", "b.jpeg", "c.JPG"])
        assert resolve_image_paths() == [Path("a.jpg"), Path("b.jpeg"), Path("c.JPG")]

    def test_filters_unsupported_extensions(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["brush_watermark", "a.jpg", "notes.txt", "b.jpeg"])
        assert resolve_image_paths() == [Path("a.jpg"), Path("b.jpeg")]

    def test_no_args_falls_back_to_file_picker(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["brush_watermark"])
        with patch(
            "brush_watermark.main.select_jpg_files", return_value=[Path("picked.jpg")]
        ) as picker:
            assert resolve_image_paths() == [Path("picked.jpg")]
            picker.assert_called_once()

    def test_no_args_and_picker_allows_multiple_files(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["brush_watermark"])
        with patch(
            "brush_watermark.main.select_jpg_files",
            return_value=[Path("a.jpg"), Path("b.jpeg")],
        ):
            assert resolve_image_paths() == [Path("a.jpg"), Path("b.jpeg")]

    def test_no_args_and_picker_cancelled_returns_empty(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["brush_watermark"])
        with patch("brush_watermark.main.select_jpg_files", return_value=[]):
            assert resolve_image_paths() == []
