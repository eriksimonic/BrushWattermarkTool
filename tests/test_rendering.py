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
        assert result.start_d == 0.0
        assert result.end_d == result.used_span
        assert result.end_d > result.start_d

    def test_span_uses_full_path_length(self):
        points = [(0, 0), (500, 0)]
        stretch = compute_text_span(points, 120, "Hi", "Arial", auto_fit=True, repeat_text=False)
        repeat = compute_text_span(points, 120, "Hi", "Arial", auto_fit=True, repeat_text=True)
        assert stretch is not None and repeat is not None
        assert stretch.start_d == 0.0
        assert repeat.start_d == 0.0
        assert stretch.used_span == repeat.used_span
        assert stretch.end_d == stretch.used_span


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

    def test_repeat_text_changes_more_pixels_than_stretch(self):
        base = Image.new("RGB", (400, 200), (128, 128, 128))
        points = [(20, 100), (380, 100)]
        stretch_stroke = Stroke(
            name="Stretch",
            points=points,
            brush_size=40,
            opacity=100,
            repeat_text=False,
        )
        repeat_stroke = Stroke(
            name="Repeat",
            points=points,
            brush_size=40,
            opacity=100,
            repeat_text=True,
            repeat_spacing=5,
        )
        settings = Settings(
            watermark_text="COPY",
            opacity=100,
            brush_size=40,
            text_color="#ffffff",
            auto_fit_text=False,
        )
        erase_mask = Image.new("L", (400, 200), 0)
        stretch = composite_watermark(base, [stretch_stroke], settings, erase_mask)
        repeat = composite_watermark(base, [repeat_stroke], settings, erase_mask)
        stretch_changed = sum(
            1 for x in range(20, 380, 3) if stretch.getpixel((x, 100)) != (128, 128, 128)
        )
        repeat_changed = sum(
            1 for x in range(20, 380, 3) if repeat.getpixel((x, 100)) != (128, 128, 128)
        )
        assert repeat_changed > stretch_changed

    def test_repeat_spacing_reduces_tile_count(self):
        base = Image.new("RGB", (400, 200), (128, 128, 128))
        points = [(20, 100), (380, 100)]
        tight = Stroke(
            name="Tight",
            points=points,
            brush_size=40,
            opacity=100,
            repeat_text=True,
            repeat_spacing=0,
        )
        spaced = Stroke(
            name="Spaced",
            points=points,
            brush_size=40,
            opacity=100,
            repeat_text=True,
            repeat_spacing=20,
        )
        settings = Settings(
            watermark_text="COPY",
            opacity=100,
            brush_size=40,
            text_color="#ffffff",
            auto_fit_text=False,
        )
        erase_mask = Image.new("L", (400, 200), 0)
        tight_result = composite_watermark(base, [tight], settings, erase_mask)
        spaced_result = composite_watermark(base, [spaced], settings, erase_mask)
        tight_changed = sum(
            1 for x in range(20, 380, 3) if tight_result.getpixel((x, 100)) != (128, 128, 128)
        )
        spaced_changed = sum(
            1 for x in range(20, 380, 3) if spaced_result.getpixel((x, 100)) != (128, 128, 128)
        )
        assert tight_changed > spaced_changed
