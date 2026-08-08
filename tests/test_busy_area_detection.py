"""Tests for busy-area tile scoring, path growing, and candidate selection."""
import random

import numpy as np
from PIL import Image, ImageDraw, ImageStat

from brush_watermark.services.busy_area_detection import (
    BusyPath,
    TileScore,
    edge_energy_image,
    find_busy_paths,
    grow_organic_path,
    score_tiles,
    select_spaced_candidates,
    tile_overlaps_protect_mask,
    tile_within_border,
)


def _checkerboard(size=(200, 200), cell=8):
    img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(img)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell * 2):
            offset = cell if (y // cell) % 2 else 0
            draw.rectangle([x + offset, y, x + offset + cell - 1, y + cell - 1], fill=255)
    return img.convert("RGB")


# ---------------------------------------------------------------------------
# Pure logic: no Pillow images involved
# ---------------------------------------------------------------------------


class TestTileScoreCenter:
    def test_center_is_midpoint(self):
        t = TileScore(x=10, y=20, size=40, score=1.0)
        assert t.center == (30, 40)


class TestTileWithinBorder:
    def test_tile_inside_border_passes(self):
        t = TileScore(x=50, y=50, size=20, score=1.0)
        assert tile_within_border(t, (200, 200), border_margin=10) is True

    def test_tile_touching_left_edge_fails(self):
        t = TileScore(x=0, y=50, size=20, score=1.0)
        assert tile_within_border(t, (200, 200), border_margin=10) is False

    def test_tile_touching_right_edge_fails(self):
        t = TileScore(x=185, y=50, size=20, score=1.0)
        assert tile_within_border(t, (200, 200), border_margin=10) is False


class TestSelectSpacedCandidates:
    def test_picks_highest_scores_first(self):
        tiles = [
            TileScore(x=0, y=0, size=10, score=1.0),
            TileScore(x=200, y=200, size=10, score=9.0),
            TileScore(x=400, y=400, size=10, score=5.0),
        ]
        selected = select_spaced_candidates(tiles, count=2, min_spacing=1.0)
        assert [t.score for t in selected] == [9.0, 5.0]

    def test_respects_count_limit(self):
        tiles = [TileScore(x=i * 100, y=0, size=10, score=float(i)) for i in range(10)]
        selected = select_spaced_candidates(tiles, count=3, min_spacing=1.0)
        assert len(selected) == 3

    def test_enforces_minimum_spacing(self):
        tiles = [
            TileScore(x=0, y=0, size=10, score=10.0),
            TileScore(x=5, y=0, size=10, score=9.0),  # too close to the first
            TileScore(x=200, y=0, size=10, score=8.0),  # far enough
        ]
        selected = select_spaced_candidates(tiles, count=3, min_spacing=100.0)
        assert len(selected) == 2
        assert selected[0].score == 10.0
        assert selected[1].score == 8.0

    def test_empty_input_returns_empty(self):
        assert select_spaced_candidates([], count=5, min_spacing=10.0) == []


# ---------------------------------------------------------------------------
# Pillow-backed pieces
# ---------------------------------------------------------------------------


class TestEdgeEnergyImage:
    def test_busy_region_scores_higher_than_flat_region(self):
        img = Image.new("RGB", (200, 200), (128, 128, 128))
        # Paint noisy detail into the left half only.
        rng = random.Random(0)
        for y in range(200):
            for x in range(0, 100, 2):
                v = rng.randint(0, 255)
                img.putpixel((x, y), (v, v, v))
        energy = edge_energy_image(img)
        busy_tile = energy.crop((0, 0, 50, 50))
        flat_tile = energy.crop((150, 150, 200, 200))
        assert ImageStat.Stat(busy_tile).mean[0] > ImageStat.Stat(flat_tile).mean[0]


class TestScoreTiles:
    def test_grid_covers_full_tiles_only(self):
        energy = Image.new("L", (50, 30), 0)
        tiles = score_tiles(energy, tile_size=20)
        # floor(50/20)=2 columns, floor(30/20)=1 row -> 2 tiles
        assert len(tiles) == 2
        assert all(t.size == 20 for t in tiles)

    def test_oversized_tile_returns_empty(self):
        energy = Image.new("L", (10, 10), 0)
        assert score_tiles(energy, tile_size=20) == []


class TestTileOverlapsProtectMask:
    def test_detects_overlap(self):
        mask = Image.new("L", (100, 100), 0)
        ImageDraw.Draw(mask).rectangle([40, 40, 60, 60], fill=255)
        overlapping = TileScore(x=30, y=30, size=20, score=1.0)
        clear = TileScore(x=0, y=0, size=20, score=1.0)
        assert tile_overlaps_protect_mask(overlapping, mask) is True
        assert tile_overlaps_protect_mask(clear, mask) is False


class TestGrowOrganicPath:
    def _open_field(self, size=(200, 200), energy_value=100.0):
        energy = np.full((size[1], size[0]), energy_value, dtype=np.float32)
        protect = np.zeros((size[1], size[0]), dtype=np.uint8)
        return energy, protect

    def test_path_starts_at_seed(self):
        energy, protect = self._open_field()
        path = grow_organic_path(
            (100, 100), energy, protect, (200, 200),
            step=10.0, max_steps=5, min_energy=1.0, border_margin=5,
            rng=random.Random(1),
        )
        assert path[0] == (100, 100)

    def test_reaches_full_length_in_an_open_field(self):
        energy, protect = self._open_field()
        path = grow_organic_path(
            (100, 100), energy, protect, (200, 200),
            step=10.0, max_steps=8, min_energy=1.0, border_margin=5,
            rng=random.Random(2),
        )
        assert len(path) == 9  # start + 8 steps, nothing to block it

    def test_stops_when_surrounded_by_protect_mask(self):
        energy, protect = self._open_field()
        protect[:, :] = 255
        protect[100, 100] = 0  # only the seed pixel itself is unprotected
        path = grow_organic_path(
            (100, 100), energy, protect, (200, 200),
            step=10.0, max_steps=8, min_energy=1.0, border_margin=5,
            rng=random.Random(3),
        )
        assert path == [(100, 100)]

    def test_stops_when_surrounded_by_flat_area(self):
        energy = np.zeros((200, 200), dtype=np.float32)
        protect = np.zeros((200, 200), dtype=np.uint8)
        path = grow_organic_path(
            (100, 100), energy, protect, (200, 200),
            step=10.0, max_steps=8, min_energy=1.0, border_margin=5,
            rng=random.Random(4),
        )
        assert path == [(100, 100)]

    def test_never_steps_outside_the_border_margin(self):
        energy, protect = self._open_field()
        path = grow_organic_path(
            (15, 15), energy, protect, (200, 200),
            step=10.0, max_steps=20, min_energy=1.0, border_margin=10,
            rng=random.Random(5),
        )
        for x, y in path:
            assert 10 <= x <= 190
            assert 10 <= y <= 190


class TestFindBusyPaths:
    def test_avoids_protect_mask_and_prefers_busy_checkerboard(self):
        img = _checkerboard((240, 240), cell=6)
        protect_mask = Image.new("L", (240, 240), 0)
        # Protect the entire right half of the image.
        ImageDraw.Draw(protect_mask).rectangle([120, 0, 240, 240], fill=255)

        paths = find_busy_paths(img, protect_mask, count=5, rng=random.Random(0))
        assert paths
        protect_arr = np.asarray(protect_mask)
        for path in paths:
            assert isinstance(path, BusyPath)
            for x, y in path.points:
                assert protect_arr[y, x] == 0

    def test_no_candidates_when_everything_protected(self):
        img = _checkerboard()
        protect_mask = Image.new("L", img.size, 255)
        paths = find_busy_paths(img, protect_mask, count=5, rng=random.Random(0))
        assert paths == []

    def test_paths_are_longer_than_a_single_tile_step(self):
        img = _checkerboard((400, 400), cell=6)
        protect_mask = Image.new("L", (400, 400), 0)
        paths = find_busy_paths(img, protect_mask, count=4, rng=random.Random(0))
        assert paths
        assert any(len(path.points) > 2 for path in paths)
