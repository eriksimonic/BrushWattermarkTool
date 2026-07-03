from PIL import Image

from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.masks import make_stroke_mask
from brush_watermark.rendering.watermark import compute_text_span, composite_watermark


class TestMakeStrokeMask:
    def test_single_point_stroke(self):
        stroke = Stroke(name="S1", points=[(50, 50)], brush_size=20, opacity=50)
        mask = make_stroke_mask(100, 100, [stroke], mask_softness=0, default_brush_size=20)
        assert mask.getpixel((50, 50)) > 0
        assert mask.getpixel((0, 0)) == 0

    def test_line_stroke(self):
        stroke = Stroke(name="S1", points=[(10, 50), (90, 50)], brush_size=10, opacity=50)
        mask = make_stroke_mask(100, 100, [stroke], mask_softness=0, default_brush_size=20)
        assert mask.getpixel((50, 50)) > 0
        assert mask.getpixel((50, 10)) == 0

    def test_invisible_stroke_ignored(self):
        stroke = Stroke(name="S1", points=[(50, 50)], brush_size=20, opacity=50, visible=False)
        mask = make_stroke_mask(100, 100, [stroke], mask_softness=0, default_brush_size=20)
        assert mask.getbbox() is None


class TestComputeTextSpan:
    def test_returns_none_for_short_path(self):
        points = [(0, 0), (2, 0)]
        result = compute_text_span(points, 120, "Test", "Arial", auto_fit=True)
        assert result is None

    def test_returns_none_for_empty_text(self):
        points = [(0, 0), (100, 0), (200, 0)]
        result = compute_text_span(points, 120, "  ", "Arial", auto_fit=True)
        assert result is None

    def test_valid_span(self):
        points = [(0, 0), (500, 0)]
        result = compute_text_span(points, 120, "Hello", "Arial", auto_fit=True)
        assert result is not None
        assert result.font_size > 0
        assert result.used_span > 0
        assert result.start_d >= 0
        assert result.end_d > result.start_d


class TestCompositeWatermark:
    def test_produces_rgb_image(self):
        base = Image.new("RGB", (200, 200), (128, 128, 128))
        stroke = Stroke(
            name="S1",
            points=[(20, 100), (180, 100)],
            brush_size=40,
            opacity=50,
        )
        settings = Settings(watermark_text="Hi", opacity=50, brush_size=40)
        erase_mask = Image.new("L", (200, 200), 0)
        result = composite_watermark(base, [stroke], settings, erase_mask)
        assert result.mode == "RGB"
        assert result.size == (200, 200)

    def test_watermark_changes_pixels(self):
        base = Image.new("RGB", (200, 200), (128, 128, 128))
        stroke = Stroke(
            name="S1",
            points=[(20, 100), (180, 100)],
            brush_size=40,
            opacity=100,
        )
        settings = Settings(
            watermark_text="TEST",
            opacity=100,
            brush_size=40,
            text_color="#ffffff",
        )
        erase_mask = Image.new("L", (200, 200), 0)
        result = composite_watermark(base, [stroke], settings, erase_mask)
        changed = [
            result.getpixel((x, 100))
            for x in range(20, 180, 5)
            if result.getpixel((x, 100)) != (128, 128, 128)
        ]
        assert len(changed) > 0
