import math
from bisect import bisect_left

from brush_watermark.geometry.points import Point, dist, path_length, simplify_points

MIN_TANGENT_WIDTH_CHARS = 3.0


class PathSampler:
    """Point/angle at a distance along a path, in O(log n) per lookup.

    Segment lengths are measured once up front. Walking the path from its
    start on every lookup made text rendering cost glyphs × points, which
    stalled the UI for long strokes with repeated text.
    """

    def __init__(self, points: list[Point]):
        self.points = points
        self._index: list[int] = []  # start point of each non-zero segment
        self._starts: list[float] = []  # distance where that segment starts
        self._ends: list[float] = []  # ... and ends
        total = 0.0
        for i in range(len(points) - 1):
            seg = dist(points[i], points[i + 1])
            if seg <= 0:
                continue
            self._index.append(i)
            self._starts.append(total)
            total += seg
            self._ends.append(total)
        self.length = total

    def point_at(self, target: float) -> tuple[float, float, float]:
        points = self.points
        if len(points) < 2:
            x, y = points[0]
            return x, y, 0.0
        # The first segment that ends at or after `target` (the linear walk's
        # "remaining <= seg"); a negative target extrapolates the first one.
        k = bisect_left(self._ends, target)
        if k < len(self._ends):
            i = self._index[k]
            p0, p1 = points[i], points[i + 1]
            t = (target - self._starts[k]) / (self._ends[k] - self._starts[k])
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            return x, y, math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        p0 = points[-2]
        p1 = points[-1]
        angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        return float(p1[0]), float(p1[1]), angle


def point_at_distance(points: list[Point], target: float) -> tuple[float, float, float]:
    """One-off lookup; build a PathSampler when looking up many distances."""
    return PathSampler(points).point_at(target)


def smooth_path_for_text(
    points: list[Point],
    *,
    min_dist: float = 3.0,
    iterations: int = 3,
) -> list[tuple[float, float]]:
    if len(points) < 2:
        return [(float(x), float(y)) for x, y in points]
    simplified = simplify_points(points, min_dist=min_dist)
    if len(simplified) < 2:
        return [(float(x), float(y)) for x, y in points]

    smoothed = [(float(x), float(y)) for x, y in simplified]
    for _ in range(iterations):
        new_points = [smoothed[0]]
        for i in range(len(smoothed) - 1):
            x0, y0 = smoothed[i]
            x1, y1 = smoothed[i + 1]
            q = (0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1)
            r = (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)
            new_points.extend([q, r])
        new_points.append(smoothed[-1])
        smoothed = new_points
    return smoothed


def tangent_half_window(avg_glyph_advance: float) -> float:
    """Half-width of the secant used to estimate a stable tangent direction."""
    return max(1.0, (MIN_TANGENT_WIDTH_CHARS / 2.0) * avg_glyph_advance)


def tangent_angle_at_distance(
    points: list[Point],
    center_d: float,
    half_window: float,
    *,
    total_length: float | None = None,
    sampler: PathSampler | None = None,
) -> float:
    if sampler is None:
        sampler = PathSampler(points)
    length = total_length if total_length is not None else sampler.length
    if length <= 0:
        return 0.0

    d0 = max(0.0, center_d - half_window)
    d1 = min(length, center_d + half_window)
    if d1 - d0 < 1e-6:
        _, _, angle = sampler.point_at(center_d)
        return angle

    x0, y0, _ = sampler.point_at(d0)
    x1, y1, _ = sampler.point_at(d1)
    return math.atan2(y1 - y0, x1 - x0)


def averaged_angle(points: list[Point], center_d: float, window: float) -> float:
    return tangent_angle_at_distance(points, center_d, window)


def angle_unwrap(reference: float, angle: float) -> float:
    while angle - reference > math.pi:
        angle -= 2 * math.pi
    while angle - reference < -math.pi:
        angle += 2 * math.pi
    return angle


def blend_angles(a: float, b: float, amount: float) -> float:
    b = angle_unwrap(a, b)
    return a + (b - a) * amount


def glyph_rotation_degrees(tangent_radians: float, angle_offset_degrees: float = 0) -> float:
    """Map path tangent to PIL rotation (image y-axis points down)."""
    return -math.degrees(tangent_radians) + angle_offset_degrees


def centered_baseline_offset(
    tangent_radians: float,
    ascent: float,
    descent: float,
) -> tuple[float, float]:
    """Virtual baseline path offset so baseline-aligned text centers on the stroke."""
    offset = (ascent - descent) * 0.5
    return -math.sin(tangent_radians) * offset, math.cos(tangent_radians) * offset
