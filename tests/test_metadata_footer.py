from PIL import Image

from brush_watermark.rendering.metadata_footer import append_metadata_footer, estimate_footer_height, footer_layout
from brush_watermark.services.exif_metadata import ImageMetadata


class TestMetadataFooter:
    def test_append_footer_expands_image(self):
        base = Image.new("RGB", (400, 300), (120, 120, 120))
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
        result = append_metadata_footer(base, metadata, "© Example")
        assert result.size[0] == 400
        assert result.size[1] > 300
        assert result.size[1] >= 300 + estimate_footer_height(400, 300, metadata, "© Example") - 8

    def test_footer_scales_with_image_size(self):
        metadata = ImageMetadata(
            make="Nikon",
            model="Z 8",
            lens="800mm f/6.3",
            serial="6022905",
        )
        small = append_metadata_footer(Image.new("RGB", (800, 600), "white"), metadata, "© Example")
        large = append_metadata_footer(Image.new("RGB", (8000, 6000), "white"), metadata, "© Example")
        small_strip = small.size[1] - 600
        large_strip = large.size[1] - 6000
        assert large_strip > small_strip * 4

        _, small_font, _ = footer_layout(800, 600)
        _, large_font, _ = footer_layout(8000, 6000)
        assert large_font > small_font * 4

    def test_estimate_footer_height_single_line(self):
        metadata = ImageMetadata()
        height = estimate_footer_height(800, 600, metadata, "")
        assert height > 0
        assert height == estimate_footer_height(800, 600, metadata, "© Long copy text")
