"""Tests for auto-watermark placement orchestration."""
import random
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from brush_watermark.models import Settings
from brush_watermark.services.adaptive_strength import MAX_OPACITY, MIN_OPACITY
from brush_watermark.services.auto_watermark import (
    MAX_DENSITY,
    MIN_DENSITY,
    clamp_density,
    place_auto_watermarks,
)
from brush_watermark.services.document import Document


def _make_doc(tmp_path: Path, size=(600, 600)) -> Document:
    """A Document backed by a noisy JPEG, so busy tiles exist everywhere."""
    img_path = tmp_path / "test.jpg"
    img = Image.new("RGB", size, (60, 60, 60))
    draw = ImageDraw.Draw(img)
    rng = random.Random(0)
    for y in range(0, size[1], 3):
        for x in range(0, size[0], 3):
            v = rng.randint(0, 255)
            draw.point((x, y), fill=(v, v, v))
    img.save(img_path)
    return Document(img_path, Settings(watermark_text="Test Mark"))


class TestClampDensity:
    def test_clamps_below_minimum(self):
        assert clamp_density(0) == MIN_DENSITY

    def test_clamps_above_maximum(self):
        assert clamp_density(999) == MAX_DENSITY

    def test_passes_through_in_range(self):
        assert clamp_density(4) == 4


class TestPlaceAutoWatermarks:
    def test_adds_strokes_to_document(self, tmp_path):
        doc = _make_doc(tmp_path)
        added = place_auto_watermarks(doc, density=4)
        assert added
        assert doc.strokes == added

    def test_added_strokes_use_adaptive_barely_visible_opacity(self, tmp_path):
        doc = _make_doc(tmp_path)
        added = place_auto_watermarks(doc, density=3)
        assert added
        for stroke in added:
            assert MIN_OPACITY <= stroke.opacity <= MAX_OPACITY

    def test_added_strokes_reuse_document_settings(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.settings.blend_mode = "screen"
        doc.settings.text_color = "#00ff00"
        added = place_auto_watermarks(doc, density=2)
        assert added
        for stroke in added:
            assert stroke.blend_mode == "screen"
            assert stroke.text_color == "#00ff00"

    def test_respects_density_upper_bound(self, tmp_path):
        doc = _make_doc(tmp_path)
        added = place_auto_watermarks(doc, density=999)
        assert len(added) <= MAX_DENSITY

    def test_no_strokes_when_no_safe_regions_found(self, tmp_path):
        doc = _make_doc(tmp_path)
        with patch(
            "brush_watermark.services.auto_watermark.find_busy_paths", return_value=[]
        ):
            added = place_auto_watermarks(doc, density=5)
        assert added == []
        assert doc.strokes == []
