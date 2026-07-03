from PIL import Image

from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.blend import composite_watermark_layer, normalize_blend_mode
from brush_watermark.rendering.watermark import composite_watermark, make_stroke_watermark_layer


class TestNormalizeBlendMode:
    def test_unknown_mode_falls_back(self):
        assert normalize_blend_mode("not-a-mode") == "soft_light"

    def test_case_insensitive(self):
        assert normalize_blend_mode("Difference") == "difference"


class TestBlendModes:
    def _sample_stroke(self) -> Stroke:
        return Stroke(
            name="S1",
            points=[(20, 100), (180, 100)],
            brush_size=40,
            opacity=100,
            blend_mode="difference",
        )

    def test_difference_changes_pixels(self):
        base = Image.new("RGB", (200, 200), (128, 128, 128))
        stroke = self._sample_stroke()
        settings = Settings(watermark_text="TEST", opacity=100, brush_size=40, text_color="white")
        erase_mask = Image.new("L", (200, 200), 0)
        result = composite_watermark(base, [stroke], settings, erase_mask)
        changed = [
            result.getpixel((x, 100))
            for x in range(20, 180, 5)
            if result.getpixel((x, 100)) != (128, 128, 128)
        ]
        assert len(changed) > 0

    def test_soft_light_differs_from_normal(self):
        base = Image.new("RGB", (200, 200), (96, 120, 144))
        stroke = Stroke(
            name="S1",
            points=[(20, 100), (180, 100)],
            brush_size=40,
            opacity=60,
            blend_mode="soft_light",
        )
        settings = Settings(
            watermark_text="TEST",
            opacity=60,
            brush_size=40,
            text_color="white",
        )
        erase_mask = Image.new("L", (200, 200), 0)
        layer = make_stroke_watermark_layer(200, 200, stroke, settings, erase_mask)

        normal = composite_watermark_layer(
            base.convert("RGBA"),
            layer,
            settings.text_color,
            "normal",
            0.6,
        ).convert("RGB")
        soft = composite_watermark_layer(
            base.convert("RGBA"),
            layer,
            settings.text_color,
            "soft_light",
            0.6,
        ).convert("RGB")

        differences = [
            x
            for x in range(20, 180, 2)
            if normal.getpixel((x, 100)) != soft.getpixel((x, 100))
        ]
        assert differences
