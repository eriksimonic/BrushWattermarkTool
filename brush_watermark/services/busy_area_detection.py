"""Finds visually busy/detailed regions of a photo, for hiding a subtle watermark in.

Scores a grid of tiles by local edge energy to pick a handful of well-spaced,
subject-safe "seed" points, then grows each seed into a longer, gently
curved path: a short random walk that keeps following busy texture and
steers away from the subject protect mask (from subject_detection.py),
stopping at the image border, a too-flat area, or the protect zone.
"""

import math
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter, ImageStat

from brush_watermark.geometry.points import Point, dist

DEFAULT_MIN_SCORE_RATIO = 0.15
DEFAULT_BORDER_RATIO = 0.03
DEFAULT_PATH_SPACING_RATIO = 3.0
DEFAULT_PATH_STEPS_RANGE = (6, 14)
DEFAULT_MAX_TURN_DEGREES = 25.0
_STEP_RETRY_ATTEMPTS = 8


@dataclass(frozen=True)
class TileScore:
    x: int
    y: int
    size: int
    score: float

    @property
    def center(self) -> Point:
        return (self.x + self.size // 2, self.y + self.size // 2)


@dataclass(frozen=True)
class BusyPath:
    points: list[Point]
    brush_size: int


def edge_energy_image(image: Image.Image) -> Image.Image:
    """Grayscale 'L' image where brighter pixels mean more local detail/edges."""
    return image.convert("L").filter(ImageFilter.FIND_EDGES)


def score_tiles(energy_image: Image.Image, tile_size: int) -> list[TileScore]:
    """Score a grid of non-overlapping tile_size x tile_size tiles by mean edge energy.

    Only full tiles are scored; a partial remainder at the right/bottom edge
    is dropped rather than scored on a smaller area.
    """
    width, height = energy_image.size
    tiles: list[TileScore] = []
    if tile_size <= 0 or tile_size > width or tile_size > height:
        return tiles
    for y in range(0, height - tile_size + 1, tile_size):
        for x in range(0, width - tile_size + 1, tile_size):
            region = energy_image.crop((x, y, x + tile_size, y + tile_size))
            mean = ImageStat.Stat(region).mean[0]
            tiles.append(TileScore(x=x, y=y, size=tile_size, score=mean))
    return tiles


def tile_within_border(tile: TileScore, image_size: tuple[int, int], border_margin: int) -> bool:
    width, height = image_size
    return (
        tile.x >= border_margin
        and tile.y >= border_margin
        and tile.x + tile.size <= width - border_margin
        and tile.y + tile.size <= height - border_margin
    )


def tile_overlaps_protect_mask(
    tile: TileScore, protect_mask: Image.Image, tolerance: float = 0.0
) -> bool:
    """True if the tile's coverage of protected (255) pixels exceeds tolerance (0-1)."""
    region = protect_mask.crop((tile.x, tile.y, tile.x + tile.size, tile.y + tile.size))
    coverage = ImageStat.Stat(region).mean[0] / 255.0
    return coverage > tolerance


def select_spaced_candidates(
    tiles: list[TileScore], count: int, min_spacing: float
) -> list[TileScore]:
    """Greedily pick up to `count` tiles, highest score first, keeping centers apart."""
    ranked = sorted(tiles, key=lambda t: t.score, reverse=True)
    selected: list[TileScore] = []
    for tile in ranked:
        if len(selected) >= count:
            break
        if all(dist(tile.center, chosen.center) >= min_spacing for chosen in selected):
            selected.append(tile)
    return selected


def grow_organic_path(
    start: Point,
    energy: np.ndarray,
    protect: np.ndarray,
    image_size: tuple[int, int],
    *,
    step: float,
    max_steps: int,
    min_energy: float,
    border_margin: int,
    max_turn_degrees: float = DEFAULT_MAX_TURN_DEGREES,
    rng: random.Random | None = None,
) -> list[Point]:
    """Random-walk a path from `start`, favoring busy/safe pixels.

    Each step turns by at most `max_turn_degrees` from the current heading
    (for a gently curved, non-straight line) and must land on a pixel that
    is inside the border margin, not in the protect mask, and at least as
    busy as `min_energy`. When a step can't find a valid heading it tries a
    few fresh random headings before giving up, so the path can curve
    around an obstacle instead of always stopping dead at its edge. The
    walk ends early (a shorter path) once no valid step remains.
    """
    rng = rng or random.Random()
    width, height = image_size
    x, y = float(start[0]), float(start[1])
    angle = rng.uniform(0.0, 2 * math.pi)
    path: list[Point] = [(int(round(x)), int(round(y)))]

    def _valid(px: float, py: float) -> bool:
        if px < border_margin or py < border_margin:
            return False
        if px > width - border_margin or py > height - border_margin:
            return False
        ix, iy = int(px), int(py)
        if protect[iy, ix]:
            return False
        return energy[iy, ix] >= min_energy

    for _ in range(max_steps):
        moved = False
        for attempt in range(_STEP_RETRY_ATTEMPTS):
            if attempt < _STEP_RETRY_ATTEMPTS // 2:
                candidate_angle = angle + math.radians(
                    rng.uniform(-max_turn_degrees, max_turn_degrees)
                )
            else:
                candidate_angle = rng.uniform(0.0, 2 * math.pi)
            nx = x + step * math.cos(candidate_angle)
            ny = y + step * math.sin(candidate_angle)
            if _valid(nx, ny):
                x, y, angle = nx, ny, candidate_angle
                path.append((int(round(x)), int(round(y))))
                moved = True
                break
        if not moved:
            break
    return path


def find_busy_paths(
    image: Image.Image,
    protect_mask: Image.Image,
    count: int,
    tile_size: int | None = None,
    min_score_ratio: float = DEFAULT_MIN_SCORE_RATIO,
    border_ratio: float = DEFAULT_BORDER_RATIO,
    min_spacing_ratio: float = DEFAULT_PATH_SPACING_RATIO,
    path_steps_range: tuple[int, int] = DEFAULT_PATH_STEPS_RANGE,
    max_turn_degrees: float = DEFAULT_MAX_TURN_DEGREES,
    rng: random.Random | None = None,
) -> list[BusyPath]:
    """Return up to `count` long, gently curved, subject-safe paths through busy texture."""
    rng = rng or random.Random()
    width, height = image.size
    short_edge = min(width, height)
    if tile_size is None:
        tile_size = max(24, short_edge // 14)
    border_margin = max(4, int(short_edge * border_ratio))
    min_spacing = tile_size * min_spacing_ratio

    energy_image = edge_energy_image(image)
    tiles = score_tiles(energy_image, tile_size)
    if not tiles:
        return []

    min_score = max(t.score for t in tiles) * min_score_ratio
    seed_candidates = [
        tile
        for tile in tiles
        if tile.score >= min_score
        and tile_within_border(tile, (width, height), border_margin)
        and not tile_overlaps_protect_mask(tile, protect_mask)
    ]
    seeds = select_spaced_candidates(seed_candidates, count, min_spacing)
    if not seeds:
        return []

    energy_arr = np.asarray(energy_image, dtype=np.float32)
    protect_arr = np.asarray(protect_mask)
    step = tile_size * 0.6
    brush_size = max(18, int(tile_size * 0.6))

    paths: list[BusyPath] = []
    for seed in seeds:
        n_steps = rng.randint(*path_steps_range)
        points = grow_organic_path(
            seed.center,
            energy_arr,
            protect_arr,
            (width, height),
            step=step,
            max_steps=n_steps,
            min_energy=min_score,
            border_margin=border_margin,
            max_turn_degrees=max_turn_degrees,
            rng=rng,
        )
        if len(points) >= 2:
            paths.append(BusyPath(points=points, brush_size=brush_size))
    return paths
