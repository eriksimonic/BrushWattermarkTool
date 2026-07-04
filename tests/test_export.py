from pathlib import Path

from PIL import Image

from brush_watermark.services.export import (
    build_copy_basename,
    build_watermarked_copy_path,
)


class TestBuildCopyBasename:
    def test_without_exif(self):
        assert build_copy_basename("DSC_1042", {}) == "DSC_1042_watermarked"

    def test_with_serial_and_datetime(self):
        exif = {
            "BodySerialNumber": "123456789",
            "DateTimeOriginal": "2026:07:04 14:10:55",
        }
        assert (
            build_copy_basename("DSC_1042", exif)
            == "DSC_1042_123456789_20260704_141055_watermarked"
        )

    def test_sanitizes_unsafe_characters(self):
        exif = {"BodySerialNumber": "ABC:123/456"}
        assert build_copy_basename("my photo", exif) == "my_photo_ABC_123_456_watermarked"


class TestBuildWatermarkedCopyPath:
    def test_builds_path_next_to_source(self, tmp_path: Path):
        src = tmp_path / "DSC_1042.jpg"
        Image.new("RGB", (8, 8), "white").save(src, format="JPEG")
        result = build_watermarked_copy_path(src)
        assert result.parent == tmp_path
        assert result.name == "DSC_1042_watermarked.jpg"
        assert not result.exists()

    def test_avoids_existing_file_collision(self, tmp_path: Path):
        src = tmp_path / "DSC_1042.jpg"
        Image.new("RGB", (8, 8), "white").save(src, format="JPEG")
        existing = tmp_path / "DSC_1042_watermarked.jpg"
        Image.new("RGB", (8, 8), "black").save(existing, format="JPEG")
        result = build_watermarked_copy_path(src)
        assert result.name == "DSC_1042_watermarked_2.jpg"
