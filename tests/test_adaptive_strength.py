"""Tests for pixel-based "barely visible" strength calculation."""
import random

from PIL import Image, ImageDraw

from brush_watermark.services.adaptive_strength import (
    MAX_OPACITY,
    MIN_OPACITY,
    barely_visible_opacity,
    local_luminance_std,
    opacity_for_path,
)


def _noisy_image(size=(200, 200), seed=0):
    img = Image.new("RGB", size, (128, 128, 128))
    rng = random.Random(seed)
    for y in range(0, size[1], 2):
        for x in range(0, size[0], 2):
            v = rng.randint(0, 255)
            img.putpixel((x, y), (v, v, v))
    return img


class TestLocalLuminanceStd:
    def test_flat_image_has_zero_std(self):
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        mask = Image.new("L", (100, 100), 255)
        assert local_luminance_std(img, mask) == 0.0

    def test_noisy_image_has_positive_std(self):
        img = _noisy_image()
        mask = Image.new("L", img.size, 255)
        assert local_luminance_std(img, mask) > 0.0

    def test_empty_mask_returns_zero(self):
        img = _noisy_image()
        mask = Image.new("L", img.size, 0)
        assert local_luminance_std(img, mask) == 0.0

    def test_mask_restricts_sampling_to_its_region(self):
        img = Image.new("RGB", (200, 100), (128, 128, 128))
        draw = ImageDraw.Draw(img)
        rng = random.Random(1)
        for y in range(0, 100, 2):
            for x in range(100, 200, 2):
                v = rng.randint(0, 255)
                img.putpixel((x, y), (v, v, v))
        flat_mask = Image.new("L", (200, 100), 0)
        ImageDraw.Draw(flat_mask).rectangle([0, 0, 99, 99], fill=255)
        busy_mask = Image.new("L", (200, 100), 0)
        ImageDraw.Draw(busy_mask).rectangle([100, 0, 199, 99], fill=255)
        assert local_luminance_std(img, flat_mask) < local_luminance_std(img, busy_mask)


class TestBarelyVisibleOpacity:
    def test_flat_area_gets_minimum_opacity(self):
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        mask = Image.new("L", (100, 100), 255)
        assert barely_visible_opacity(img, mask) == MIN_OPACITY

    def test_very_busy_area_saturates_to_maximum_opacity(self):
        # Extreme-contrast black/white checkerboard: well past the saturation std-dev.
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        for y in range(0, 100, 10):
            for x in range(0, 100, 20):
                offset = 10 if (y // 10) % 2 else 0
                draw.rectangle([x + offset, y, x + offset + 9, y + 9], fill=(255, 255, 255))
        mask = Image.new("L", img.size, 255)
        assert barely_visible_opacity(img, mask) == MAX_OPACITY

    def test_opacity_always_within_bounds(self):
        img = _noisy_image()
        mask = Image.new("L", img.size, 128)
        opacity = barely_visible_opacity(img, mask)
        assert MIN_OPACITY <= opacity <= MAX_OPACITY


class TestOpacityForPath:
    def test_returns_value_within_bounds(self):
        img = _noisy_image()
        opacity = opacity_for_path(img, [(20, 100), (180, 100)], brush_size=40)
        assert MIN_OPACITY <= opacity <= MAX_OPACITY

    def test_busier_path_gets_higher_opacity_than_flatter_path(self):
        img = Image.new("RGB", (200, 100), (128, 128, 128))
        rng = random.Random(2)
        for y in range(0, 100, 2):
            for x in range(100, 200, 2):
                v = rng.randint(0, 255)
                img.putpixel((x, y), (v, v, v))
        flat_opacity = opacity_for_path(img, [(10, 50), (90, 50)], brush_size=30)
        busy_opacity = opacity_for_path(img, [(110, 50), (190, 50)], brush_size=30)
        assert busy_opacity > flat_opacity
