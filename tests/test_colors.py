from PIL import Image

from brush_watermark.rendering.colors import (
    build_swatch_palette,
    normalize_text_color,
    parse_rgb,
    rgb_to_hex,
)


class TestColors:
    def test_legacy_white_maps_to_hex(self):
        assert normalize_text_color("white") == "#ffffff"
        assert normalize_text_color("black") == "#000000"

    def test_parse_rgb(self):
        assert parse_rgb("#808080") == (128, 128, 128)

    def test_build_swatch_palette_includes_fixed_colors(self):
        image = Image.new("RGB", (200, 200), (40, 90, 160))
        swatches = build_swatch_palette(image)
        assert len(swatches) == 11
        assert rgb_to_hex((255, 255, 255)) in swatches
        assert rgb_to_hex((128, 128, 128)) in swatches
        assert rgb_to_hex((0, 0, 0)) in swatches
