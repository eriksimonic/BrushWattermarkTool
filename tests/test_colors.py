from PIL import Image

from brush_watermark.rendering.colors import (
    build_swatch_palette,
    normalize_text_color,
    parse_rgb,
    rgb_to_hex,
    sample_image_color,
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


class TestSampleImageColor:
    def test_flat_image_returns_its_colour(self):
        image = Image.new("RGB", (50, 40), (10, 200, 30))
        assert sample_image_color(image, 25, 20) == "#0ac81e"

    def test_averages_the_box_around_the_point(self):
        image = Image.new("RGB", (5, 1), (0, 0, 0))
        image.putpixel((2, 0), (250, 250, 250))
        # radius 2 on a 5x1 image averages all five pixels: 250 / 5 = 50.
        assert sample_image_color(image, 2, 0) == "#323232"

    def test_corner_and_out_of_range_points_are_clamped(self):
        image = Image.new("RGB", (10, 10), (100, 100, 100))
        image.putpixel((9, 9), (100, 100, 100))
        assert sample_image_color(image, 9, 9) == "#646464"
        assert sample_image_color(image, 500, -3) == "#646464"

    def test_rgba_input(self):
        image = Image.new("RGBA", (6, 6), (255, 0, 0, 128))
        assert sample_image_color(image, 3, 3) == "#ff0000"
