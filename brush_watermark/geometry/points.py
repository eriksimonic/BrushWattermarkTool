import math
from typing import TypeVar

Point = tuple[int, int]
T = TypeVar("T", int, float)


def clamp(value: T, low: T, high: T) -> T:
    return max(low, min(high, value))


def dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx = ax + t * dx
    qy = ay + t * dy
    return math.hypot(px - qx, py - qy)


def path_length(points: list[Point]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def simplify_points(points: list[Point], min_dist: float = 3.0) -> list[Point]:
    if not points:
        return []
    out = [points[0]]
    for pt in points[1:]:
        if dist(out[-1], pt) >= min_dist:
            out.append(pt)
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def find_anchor_index(points: list[Point], x: float, y: float, tol: float = 12.0) -> int:
    """Return the index of the nearest point within tol, or -1."""
    best_idx = -1
    best_dist = None
    for i, (px, py) in enumerate(points):
        d = math.hypot(x - px, y - py)
        if d <= tol and (best_dist is None or d < best_dist):
            best_dist = d
            best_idx = i
    return best_idx


def normalize_text_direction(points: list[Point]) -> list[Point]:
    if len(points) < 2:
        return points
    start = points[0]
    end = points[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if abs(dx) >= abs(dy):
        return points if dx >= 0 else list(reversed(points))
    return points if dy <= 0 else list(reversed(points))
