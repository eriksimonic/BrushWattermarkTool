"""Tests for anchor-based curve geometry."""
import pytest

from brush_watermark.geometry.curve import (
    anchors_from_points,
    catmull_rom_curve,
    find_curve_segment_for_insert,
)


class TestAnchorsFromPoints:
    def test_keeps_endpoints(self):
        pts = [(i * 5, 0) for i in range(40)]
        anchors = anchors_from_points(pts, epsilon=4.0)
        assert anchors[0] == (0, 0)
        assert anchors[-1] == (195, 0)

    def test_collapses_straight_line_to_two_anchors(self):
        pts = [(i, 0) for i in range(100)]
        anchors = anchors_from_points(pts, epsilon=2.0)
        assert anchors == [(0, 0), (99, 0)]

    def test_reduces_dense_curve_to_few_anchors(self):
        # A big arc drawn as many dense samples should reduce dramatically.
        import math

        pts = [
            (int(200 + 200 * math.cos(t / 100 * math.pi)),
             int(200 + 200 * math.sin(t / 100 * math.pi)))
            for t in range(101)
        ]
        anchors = anchors_from_points(pts, epsilon=8.0)
        assert 2 < len(anchors) < len(pts) / 2

    def test_short_input_preserved(self):
        assert anchors_from_points([(0, 0), (10, 10)], epsilon=5.0) == [(0, 0), (10, 10)]


class TestCatmullRomCurve:
    def test_two_anchors_stay_a_line(self):
        assert catmull_rom_curve([(0, 0), (100, 0)]) == [(0, 0), (100, 0)]

    def test_passes_through_endpoints(self):
        curve = catmull_rom_curve([(0, 0), (50, 40), (100, 0)])
        assert curve[0] == (0, 0)
        assert curve[-1] == (100, 0)

    def test_produces_dense_smooth_curve(self):
        anchors = [(0, 0), (50, 40), (100, 0)]
        curve = catmull_rom_curve(anchors)
        assert len(curve) > len(anchors)
        # Curve bulges toward the middle anchor.
        assert max(y for _, y in curve) > 0


class TestFindCurveSegmentForInsert:
    def test_none_when_far(self):
        anchors = [(0, 0), (100, 0), (200, 0)]
        assert find_curve_segment_for_insert(anchors, 100, 500, tol=5.0) == -1

    def test_finds_first_segment(self):
        anchors = [(0, 0), (100, 0), (200, 0)]
        assert find_curve_segment_for_insert(anchors, 50, 0, tol=5.0) == 0

    def test_finds_second_segment(self):
        anchors = [(0, 0), (100, 0), (200, 0)]
        assert find_curve_segment_for_insert(anchors, 150, 0, tol=5.0) == 1

    def test_two_anchor_line(self):
        anchors = [(0, 0), (100, 0)]
        assert find_curve_segment_for_insert(anchors, 50, 0, tol=5.0) == 0
        assert find_curve_segment_for_insert(anchors, 50, 50, tol=5.0) == -1
