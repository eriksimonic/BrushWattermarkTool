"""PathSampler: distance lookups along a path without re-walking it every call."""
import math
import random

import pytest

import brush_watermark.geometry.points as points_module
from brush_watermark.geometry.path_text import PathSampler, point_at_distance, tangent_angle_at_distance
from brush_watermark.geometry.points import dist, path_length


def _reference_point_at_distance(points, target):
    """The original linear walk, kept here as the behaviour to match."""
    if len(points) < 2:
        x, y = points[0]
        return x, y, 0.0
    remaining = target
    for i in range(len(points) - 1):
        p0, p1 = points[i], points[i + 1]
        seg = dist(p0, p1)
        if seg <= 0:
            continue
        if remaining <= seg:
            t = remaining / seg
            return p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        remaining -= seg
    p0, p1 = points[-2], points[-1]
    return float(p1[0]), float(p1[1]), math.atan2(p1[1] - p0[1], p1[0] - p0[0])


def _wiggly_path(n, seed=1):
    rng = random.Random(seed)
    pts, x, y = [], 0.0, 0.0
    for i in range(n):
        if i % 17 == 5:
            pts.append((x, y))  # zero-length segment
        x += rng.uniform(-4, 9)
        y += rng.uniform(-6, 6)
        pts.append((x, y))
    return pts


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_the_linear_walk_everywhere(seed):
    pts = _wiggly_path(300, seed)
    sampler = PathSampler(pts)
    length = path_length(pts)
    assert sampler.length == pytest.approx(length)
    targets = [-5.0, 0.0, length, length + 50] + [random.Random(seed).uniform(0, length) for _ in range(200)]
    for target in targets:
        assert sampler.point_at(target) == pytest.approx(_reference_point_at_distance(pts, target), abs=1e-6)


def test_degenerate_paths():
    assert PathSampler([(3, 4)]).point_at(10) == (3, 4, 0.0)
    assert PathSampler([(1, 1), (1, 1)]).point_at(5) == pytest.approx(_reference_point_at_distance([(1, 1), (1, 1)], 5))


def test_point_at_distance_still_works_on_plain_lists():
    pts = [(0, 0), (100, 0), (100, 50)]
    assert point_at_distance(pts, 120) == pytest.approx((100.0, 20.0, math.pi / 2))


def test_tangent_with_sampler_matches_without():
    pts = _wiggly_path(200)
    sampler = PathSampler(pts)
    for center in (10.0, 250.0, 600.0):
        assert tangent_angle_at_distance(pts, center, 12.0, sampler=sampler) == pytest.approx(
            tangent_angle_at_distance(pts, center, 12.0)
        )


def test_lookups_do_not_rewalk_the_path(monkeypatch):
    """Many lookups on a long path cost one pass to build, then no more distance maths."""
    pts = _wiggly_path(4000)
    calls = {"n": 0}
    real_dist = points_module.dist

    def counting_dist(a, b):
        calls["n"] += 1
        return real_dist(a, b)

    import brush_watermark.geometry.path_text as path_text

    monkeypatch.setattr(path_text, "dist", counting_dist)
    sampler = PathSampler(pts)
    for i in range(600):
        sampler.point_at(i * 20.0)
        tangent_angle_at_distance(pts, i * 20.0, 15.0, sampler=sampler, total_length=sampler.length)
    assert calls["n"] <= len(pts)


def test_rendering_a_long_repeat_stroke_is_not_quadratic(monkeypatch):
    """Drawing repeated text along a long stroke must not walk the path per glyph."""
    from PIL import Image

    import brush_watermark.geometry.path_text as path_text
    from brush_watermark.models import Settings, Stroke
    from brush_watermark.rendering.watermark import draw_text_on_path

    loop = [(600 + 300 * math.cos(t / 40), 600 + 250 * math.sin(t / 40)) for t in range(1500)]
    stroke = Stroke(name="s", points=loop, anchors=loop[::30], brush_size=60, opacity=30, repeat_text=True)
    calls = {"n": 0}
    real_dist = points_module.dist

    def counting_dist(a, b):
        calls["n"] += 1
        return real_dist(a, b)

    monkeypatch.setattr(path_text, "dist", counting_dist)
    layer = Image.new("RGBA", (1300, 1300), (0, 0, 0, 0))
    draw_text_on_path(layer, stroke, Settings())
    # The smoothed text path has ~8x the stroke's points; a handful of passes over
    # it is fine, one pass per glyph (hundreds of glyphs) is not.
    assert calls["n"] < 20 * 8 * len(loop)
    assert layer.getbbox() is not None
