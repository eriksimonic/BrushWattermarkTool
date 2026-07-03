import math

from brush_watermark.geometry.points import Point, dist


def point_at_distance(points: list[Point], target: float) -> tuple[float, float, float]:
    if len(points) < 2:
        x, y = points[0]
        return x, y, 0.0
    remaining = target
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        seg = dist(p0, p1)
        if seg <= 0:
            continue
        if remaining <= seg:
            t = remaining / seg
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            return x, y, angle
        remaining -= seg
    p0 = points[-2]
    p1 = points[-1]
    angle = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return float(p1[0]), float(p1[1]), angle


def averaged_angle(points: list[Point], center_d: float, window: float) -> float:
    d0 = max(0.0, center_d - window)
    d1 = center_d + window
    x0, y0, _ = point_at_distance(points, d0)
    x1, y1, _ = point_at_distance(points, d1)
    return math.atan2(y1 - y0, x1 - x0)


def angle_unwrap(reference: float, angle: float) -> float:
    while angle - reference > math.pi:
        angle -= 2 * math.pi
    while angle - reference < -math.pi:
        angle += 2 * math.pi
    return angle


def blend_angles(a: float, b: float, amount: float) -> float:
    b = angle_unwrap(a, b)
    return a + (b - a) * amount
