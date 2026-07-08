"""Anchor-based path geometry.

A path is defined by a small set of *anchors* (editable control points). The
smooth curve that the watermark text follows is a Catmull-Rom spline through
those anchors, so moving one anchor re-flows the whole curve smoothly, the way
an Illustrator path responds to dragging a point.
"""
import math

from brush_watermark.geometry.points import Point, point_segment_distance

CURVE_SAMPLES_PER_SEGMENT = 18


def _perpendicular_distance(pt, line_start, line_end) -> float:
    x, y = pt
    x1, y1 = line_start
    x2, y2 = line_end
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    px = x1 + t * dx
    py = y1 + t * dy
    return math.hypot(x - px, y - py)


def _rdp(points: list, epsilon: float) -> list:
    """Ramer-Douglas-Peucker simplification that always keeps the endpoints."""
    if len(points) < 3:
        return list(points)
    start, end = points[0], points[-1]
    index = -1
    max_dist = 0.0
    for i in range(1, len(points) - 1):
        d = _perpendicular_distance(points[i], start, end)
        if d > max_dist:
            max_dist = d
            index = i
    if max_dist > epsilon and index != -1:
        left = _rdp(points[: index + 1], epsilon)
        right = _rdp(points[index:], epsilon)
        return left[:-1] + right
    return [start, end]


def _dedupe(points: list) -> list:
    out = []
    for pt in points:
        if not out or out[-1] != pt:
            out.append(pt)
    return out


def anchors_from_points(points: list, epsilon: float) -> list[Point]:
    """Reduce a dense drawn polyline to a sparse set of anchor points."""
    pts = _dedupe([(float(x), float(y)) for x, y in points])
    if len(pts) <= 2:
        return [(int(round(x)), int(round(y))) for x, y in pts]
    simplified = _rdp(pts, epsilon)
    return _dedupe([(int(round(x)), int(round(y))) for x, y in simplified])


def _catmull_rom_point(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * (
        (2 * p1[0])
        + (-p0[0] + p2[0]) * t
        + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
        + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
    )
    y = 0.5 * (
        (2 * p1[1])
        + (-p0[1] + p2[1]) * t
        + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
        + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
    )
    return x, y


def catmull_rom_curve(
    anchors: list, samples_per_segment: int = CURVE_SAMPLES_PER_SEGMENT
) -> list[Point]:
    """Dense polyline of a Catmull-Rom spline passing through every anchor."""
    pts = [(float(x), float(y)) for x, y in anchors]
    if len(pts) <= 2:
        return [(int(round(x)), int(round(y))) for x, y in pts]
    padded = [pts[0]] + pts + [pts[-1]]
    curve: list[tuple[float, float]] = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for s in range(samples_per_segment):
            curve.append(_catmull_rom_point(p0, p1, p2, p3, s / samples_per_segment))
    curve.append(pts[-1])
    return _dedupe([(int(round(x)), int(round(y))) for x, y in curve])


def find_curve_segment_for_insert(
    anchors: list,
    x: float,
    y: float,
    tol: float = 12.0,
    samples_per_segment: int = CURVE_SAMPLES_PER_SEGMENT,
) -> int:
    """Return the anchor index after which to insert a new anchor.

    Distance is measured against the *rendered* smooth curve, so clicking on the
    visible curve inserts an anchor into the correct span even when the anchors
    themselves are far apart. Returns -1 if nothing is close enough.
    """
    pts = [(float(ax), float(ay)) for ax, ay in anchors]
    if len(pts) < 2:
        return -1
    if len(pts) == 2:
        d = point_segment_distance(x, y, pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        return 0 if d <= tol else -1

    padded = [pts[0]] + pts + [pts[-1]]
    best_idx = -1
    best_dist: float | None = None
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        prev = p1
        for s in range(1, samples_per_segment + 1):
            cur = _catmull_rom_point(p0, p1, p2, p3, s / samples_per_segment)
            d = point_segment_distance(x, y, prev[0], prev[1], cur[0], cur[1])
            if best_dist is None or d < best_dist:
                best_dist = d
                best_idx = i - 1
            prev = cur
    if best_dist is not None and best_dist <= tol:
        return best_idx
    return -1
