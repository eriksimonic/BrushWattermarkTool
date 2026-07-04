from brush_watermark.services.exif_metadata import (
    ImageMetadata,
    format_exposure,
    format_fnumber,
    format_focal_length,
)


class TestExifFormatting:
    def test_format_exposure_fast(self):
        assert format_exposure((1, 250)) == "1/250s"

    def test_format_exposure_slow(self):
        assert format_exposure((15, 10)) == "1.5s"

    def test_format_fnumber(self):
        assert format_fnumber((28, 10)) == "f/2.8"

    def test_format_focal_length(self):
        assert format_focal_length((500, 10)) == "50mm"


class TestImageMetadata:
    def test_caption_line_single_publication_style(self):
        metadata = ImageMetadata(
            make="Canon",
            model="EOS R5",
            lens="RF 24-70mm F2.8 L IS USM",
            serial="123456789",
            iso="400",
            aperture="f/2.8",
            shutter="1/250s",
            focal_length="50mm",
            datetime_original="2026-07-04 14:10:55",
        )
        caption = metadata.caption_line("© Erik Simonič")
        assert caption == (
            "Canon EOS R5, 24-70mm f/2.8 — "
            "ƒ/2.8, 1/250 sec., ISO 400, 50 mm — "
            "S/N 123456789 — © Erik Simonič"
        )

    def test_caption_shortens_redundant_camera_and_lens(self):
        metadata = ImageMetadata(
            make="NIKON CORPORATION",
            model="NIKON Z 8",
            lens="NIKKOR Z 800mm f/6.3 VR S Z TC-1.4x",
            serial="6022905",
            iso="160",
            aperture="f/9",
            shutter="1/40s",
            focal_length="1120mm",
        )
        caption = metadata.caption_line("Erik Simonič")
        assert caption.startswith("Nikon Z 8, 800mm f/6.3 TC-1.4x —")
        assert "CORPORATION" not in caption
        assert "NIKKOR" not in caption
        assert caption.endswith("S/N 6022905 — Erik Simonič")

    def test_from_exif(self):
        exif = {
            "Make": "Nikon",
            "Model": "Z8",
            "LensModel": "NIKKOR Z 24-70mm f/2.8 S",
            "BodySerialNumber": "987654321",
            "ISOSpeedRatings": 800,
            "FNumber": (28, 10),
            "ExposureTime": (1, 500),
            "FocalLength": (240, 10),
            "DateTimeOriginal": "2026:07:04 14:10:55",
        }
        metadata = ImageMetadata.from_exif(exif)
        assert metadata.make == "Nikon"
        assert metadata.serial == "987654321"
        assert metadata.iso == "800"
        assert metadata.aperture == "f/2.8"
        assert metadata.shutter == "1/500s"
        assert metadata.focal_length == "24mm"
