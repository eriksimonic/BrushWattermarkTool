import math

import pytest

from brush_watermark.geometry.path_text import (
    angle_unwrap,
    averaged_angle,
    blend_angles,
    point_at_distance,
)
from brush_watermark.geometry.points import (
    chaikin_smooth,
    clamp,
    dist,
    normalize_text_direction,
    path_length,
    point_segment_distance,
    simplify_points,
)


class TestClamp:
    def test_within_range(self):
        assert clamp(5, 0, 10) == 5

    def test_below_low(self):
        assert clamp(-1, 0, 10) == 0

    def test_above_high(self):
        assert clamp(15, 0, 10) == 10


class TestDist:
    def test_horizontal(self):
        assert dist((0, 0), (3, 0)) == pytest.approx(3.0)

    def test_diagonal(self):
        assert dist((0, 0), (3, 4)) == pytest.approx(5.0)


class TestPointSegmentDistance:
    def test_on_segment(self):
        d = point_segment_distance(5, 0, 0, 0, 10, 0)
        assert d == pytest.approx(0.0)

    def test_perpendicular(self):
        d = point_segment_distance(5, 3, 0, 0, 10, 0)
        assert d == pytest.approx(3.0)

    def test_degenerate_segment(self):
        d = point_segment_distance(3, 4, 1, 1, 1, 1)
        assert d == pytest.approx(math.hypot(2, 3))


class TestPathLength:
    def test_empty(self):
        assert path_length([]) == 0.0

    def test_single_point(self):
        assert path_length([(0, 0)]) == 0.0

    def test_polyline(self):
        points = [(0, 0), (10, 0), (10, 10)]
        assert path_length(points) == pytest.approx(20.0)


class TestSimplifyPoints:
    def test_empty(self):
        assert simplify_points([]) == []

    def test_removes_close_points(self):
        points = [(0, 0), (1, 0), (2, 0), (100, 0)]
        result = simplify_points(points, min_dist=5.0)
        assert result[0] == (0, 0)
        assert result[-1] == (100, 0)
        assert len(result) == 2

    def test_preserves_end_point(self):
        points = [(0, 0), (1, 1), (50, 50)]
        result = simplify_points(points, min_dist=100.0)
        assert result == [(0, 0), (50, 50)]


class TestChaikinSmooth:
    def test_short_path_unchanged(self):
        points = [(0, 0), (10, 0)]
        assert chaikin_smooth(points) == points

    def test_produces_more_points(self):
        points = [(0, 0), (50, 0), (100, 0)]
        result = chaikin_smooth(points, iterations=1)
        assert len(result) > len(points)


class TestNormalizeTextDirection:
    def test_left_to_right(self):
        points = [(0, 0), (100, 0)]
        assert normalize_text_direction(points) == points

    def test_right_to_left_reversed(self):
        points = [(100, 0), (0, 0)]
        assert normalize_text_direction(points) == [(0, 0), (100, 0)]

    def test_bottom_to_top_unchanged(self):
        # Vertical strokes going upward (dy <= 0) are kept as-is
        points = [(0, 100), (0, 0)]
        assert normalize_text_direction(points) == points


class TestPointAtDistance:
    def test_start(self):
        points = [(0, 0), (100, 0)]
        x, y, angle = point_at_distance(points, 0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)
        assert angle == pytest.approx(0.0)

    def test_midpoint(self):
        points = [(0, 0), (100, 0)]
        x, y, angle = point_at_distance(points, 50)
        assert x == pytest.approx(50.0)
        assert y == pytest.approx(0.0)

    def test_beyond_end(self):
        points = [(0, 0), (100, 0)]
        x, y, _ = point_at_distance(points, 200)
        assert x == pytest.approx(100.0)
        assert y == pytest.approx(0.0)


class TestAngles:
    def test_angle_unwrap(self):
        ref = 0.0
        angle = math.pi * 1.5
        unwrapped = angle_unwrap(ref, angle)
        assert abs(unwrapped - ref) <= math.pi

    def test_blend_angles_midpoint(self):
        a = 0.0
        b = math.pi / 2
        result = blend_angles(a, b, 0.5)
        assert result == pytest.approx(math.pi / 4)

    def test_averaged_angle_horizontal(self):
        points = [(0, 0), (100, 0)]
        angle = averaged_angle(points, 50, 20)
        assert angle == pytest.approx(0.0, abs=0.1)
