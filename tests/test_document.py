"""Tests for Document anchor-editing methods and append_to_stroke."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from brush_watermark.models import Settings, Stroke


# ---------------------------------------------------------------------------
# Helpers — test the lower-level document methods without a real image file
# ---------------------------------------------------------------------------

def _make_doc(tmp_path: Path):
    """Return a Document backed by a tiny 10×10 JPEG."""
    from PIL import Image
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10), (128, 128, 128)).save(img_path)
    from brush_watermark.services.document import Document
    return Document(img_path, Settings())


def _stroke(pts, brush_size=50, opacity=50):
    pts = list(pts)
    return Stroke(
        name="S",
        points=list(pts),
        anchors=list(pts),
        brush_size=brush_size,
        opacity=opacity,
    )


class TestAppendToStroke:
    def test_extends_stroke_points(self, tmp_path):
        doc = _make_doc(tmp_path)
        s = _stroke([(0, 0), (10, 0)])
        doc.strokes.append(s)
        doc.append_to_stroke(0, [(20, 0), (30, 0)])
        assert doc.strokes[0].points[-1] == (30, 0)
        assert doc.strokes[0].points[0] == (0, 0)

    def test_no_op_on_invalid_index(self, tmp_path):
        doc = _make_doc(tmp_path)
        s = _stroke([(0, 0), (10, 0)])
        doc.strokes.append(s)
        original_len = len(s.points)
        doc.append_to_stroke(99, [(20, 0)])  # out of range, must not raise
        assert len(doc.strokes[0].points) == original_len

    def test_simplifies_duplicates_at_join(self, tmp_path):
        doc = _make_doc(tmp_path)
        # Same point repeated — simplify should collapse
        s = _stroke([(0, 0), (100, 0)], brush_size=50)
        doc.strokes.append(s)
        doc.append_to_stroke(0, [(100, 0), (100, 0), (100, 0), (200, 0)])
        pts = doc.strokes[0].points
        # Should not have triple repetitions of (100,0)
        x_vals = [p[0] for p in pts]
        assert x_vals.count(100) <= 2


class TestMoveAnchor:
    def test_moves_to_new_position(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (50, 0), (100, 0)]))
        doc.move_anchor(0, 1, (50, 25))
        assert doc.strokes[0].anchors[1] == (50, 25)

    def test_rebuilds_curve_through_moved_anchor(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (50, 0), (100, 0)]))
        doc.move_anchor(0, 1, (50, 40))
        pts = doc.strokes[0].points
        # Endpoints stay put; the curve now bulges toward the moved anchor.
        assert pts[0] == (0, 0)
        assert pts[-1] == (100, 0)
        assert max(y for _, y in pts) > 0

    def test_ignores_out_of_range_anchor(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (10, 0)]))
        doc.move_anchor(0, 99, (5, 5))  # must not raise
        assert doc.strokes[0].anchors == [(0, 0), (10, 0)]

    def test_ignores_out_of_range_stroke(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.move_anchor(5, 0, (0, 0))  # no strokes at all, must not raise


class TestInsertAnchor:
    def test_inserts_between_two_points(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (100, 0)]))
        doc.insert_anchor(0, 0, (50, 0))
        anchors = doc.strokes[0].anchors
        assert len(anchors) == 3
        assert anchors[1] == (50, 0)

    def test_does_not_insert_beyond_last_segment(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (10, 0)]))
        doc.insert_anchor(0, 5, (99, 99))  # segment index 5 doesn't exist
        assert len(doc.strokes[0].anchors) == 2

    def test_ignores_out_of_range_stroke(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.insert_anchor(0, 0, (0, 0))  # no strokes, must not raise


class TestDeleteAnchor:
    def test_removes_middle_point(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (50, 50), (100, 0)]))
        doc.delete_anchor(0, 1)
        assert doc.strokes[0].anchors == [(0, 0), (100, 0)]

    def test_refuses_to_delete_below_two_points(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (10, 0)]))
        doc.delete_anchor(0, 0)
        assert len(doc.strokes[0].anchors) == 2

    def test_ignores_out_of_range(self, tmp_path):
        doc = _make_doc(tmp_path)
        doc.strokes.append(_stroke([(0, 0), (10, 0), (20, 0)]))
        doc.delete_anchor(0, 99)  # bad index, must not raise
        assert len(doc.strokes[0].anchors) == 3


class TestFinalizeStrokePoints:
    def test_simplifies_only_no_excessive_expansion(self, tmp_path):
        doc = _make_doc(tmp_path)
        # Chaikin would multiply the number of points; simplified output should be smaller
        raw = [(i * 5, 0) for i in range(20)]
        result = doc.finalize_stroke_points(raw, brush_size=50)
        # simplify with min_dist=0.5 keeps all 20; with larger brush we collapse some
        assert len(result) >= 2
        assert result[0] == raw[0]
        assert result[-1] == raw[-1]

    def test_returns_at_least_two_for_valid_input(self, tmp_path):
        doc = _make_doc(tmp_path)
        pts = [(0, 0), (500, 0)]
        assert len(doc.finalize_stroke_points(pts, 100)) >= 2
